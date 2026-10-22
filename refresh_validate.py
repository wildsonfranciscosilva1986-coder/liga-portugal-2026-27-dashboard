#!/usr/bin/env python3
"""Fail-closed refresh and independent validation for Liga Portugal Betclic 2026/27."""
import json, urllib.request, datetime, re, unicodedata
from pathlib import Path
from collections import Counter, defaultdict
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parent
SNAP=ROOT/'source_snapshots'; SNAP.mkdir(exist_ok=True)
COMP='ligaportugalbetclic'; SEASON='20262027'
BASE='https://www.ligaportugal.pt/api'
ROUNDS_URL=f'{BASE}/v1/competition/season/rounds?competition={COMP}&season={SEASON}'
MATCH_URL=f'{BASE}/v1/competition/matches?competition={COMP}&season={SEASON}&round={{round}}'
TABLE_URL=f'{BASE}/v2/competition/standings?competition={COMP}&season={SEASON}'
ESPN_URL='https://site.api.espn.com/apis/site/v2/sports/soccer/por.1/scoreboard?dates={date}'
ALIASES={
 'fc porto':'fc porto','sl benfica':'benfica','sporting cp':'sporting cp','santa clara':'santa clara',
 'fc arouca':'arouca','gil vicente fc':'gil vicente','academico':'academico de viseu','sc braga':'braga',
 'fc alverca':'alverca','estrela amadora':'estrela','moreirense fc':'moreirense','maritimo m':'maritimo',
 'fc famalicao':'fc famalicao','rio ave fc':'rio ave','vitoria sc':'vitoria de guimaraes','cd nacional':'c d nacional',
 'casa pia ac':'casa pia','estoril praia':'estoril'
}

def get_json(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; dashboard-refresh/1.0)','Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=45) as r:
        if r.status!=200: raise RuntimeError(f'HTTP {r.status}: {url}')
        return json.load(r)
def save(name,obj): (SNAP/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def norm(s):
    s=unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower()
    s=re.sub(r'[^a-z0-9]+',' ',s).strip()
    return s

def teams_lookup(matches):
    return {norm(m['home']):m['home'] for m in matches}|{norm(m['away']):m['away'] for m in matches}
def alias(s):
    n=norm(s)
    return ALIASES.get(n,n)
def compact_match(m):
    state=m.get('fixtureStateTypeId')
    final=state==5 and m.get('homeTeamGoals') is not None and m.get('awayTeamGoals') is not None
    date_defined=bool(m.get('fixtureDateIsDefined'))
    return {'fixture_code':str(m.get('fixtureCode')),'fixture_number':m.get('fixtureNumber'),'round':int(m['round']),
      'match_date_utc':m.get('matchDate'),'fixture_date_utc':m.get('fixtureDate'),'date_defined':date_defined,
      'home':m['homeTeam']['name'],'home_team_id':m['homeTeam'].get('id'),'home_external_id':m['homeTeam'].get('external_id'),
      'away':m['awayTeam']['name'],'away_team_id':m['awayTeam'].get('id'),'away_external_id':m['awayTeam'].get('external_id'),
      'home_goals':m.get('homeTeamGoals') if final else None,'away_goals':m.get('awayTeamGoals') if final else None,
      'state_id':state,'substate_id':m.get('fixtureSubStateTypeId'),'has_official_result':m.get('hasOfficialResult'),
      'cancelled':bool(m.get('canceledFixture')),'not_played':bool(m.get('notPlayedFixture')),'postponed':bool(m.get('postponedFixture'))}

def calc_table(matches, teams):
    rows={t:{'team_name':t,'played':0,'wins':0,'draws':0,'loses':0,'points':0,'gf':0,'ga':0,'home_played':0,'away_played':0,'home_wins':0,'home_draws':0,'home_loses':0,'home_gf':0,'home_ga':0,'away_wins':0,'away_draws':0,'away_loses':0,'away_gf':0,'away_ga':0} for t in teams}
    for m in matches:
      if m['state_id']!=5 or m['home_goals'] is None or m['away_goals'] is None: continue
      h,a=m['home'],m['away']; hg,ag=m['home_goals'],m['away_goals']; H,A=rows[h],rows[a]
      H['played']+=1;A['played']+=1;H['home_played']+=1;A['away_played']+=1;H['gf']+=hg;H['ga']+=ag;A['gf']+=ag;A['ga']+=hg;H['home_gf']+=hg;H['home_ga']+=ag;A['away_gf']+=ag;A['away_ga']+=hg
      if hg>ag: H['wins']+=1;H['points']+=3;H['home_wins']+=1;A['loses']+=1;A['away_loses']+=1
      elif hg<ag: A['wins']+=1;A['points']+=3;A['away_wins']+=1;H['loses']+=1;H['home_loses']+=1
      else: H['draws']+=1;A['draws']+=1;H['points']+=1;A['points']+=1;H['home_draws']+=1;A['away_draws']+=1
    return rows

def official_simplify(rows):
    out={}
    for r in rows:
      n=r['team_name'];out[n]={'played':r.get('played',r.get('number_matches')),'wins':r.get('total_wins',r.get('wins')),'draws':r.get('total_draws',r.get('draws')),'loses':r.get('total_loses',r.get('loses')),'points':r.get('points'),'gf':r.get('total_goals_for'),'ga':r.get('total_goals_against'), 'home_played':r.get('homePlayedGames'),'away_played':r.get('awayPlayedGames'),'home_wins':r.get('home_wins'),'home_draws':r.get('home_draws'),'home_loses':r.get('home_loses'),'home_gf':r.get('home_goals_for'),'home_ga':r.get('home_goals_against'),'away_wins':r.get('away_wins'),'away_draws':r.get('away_draws'),'away_loses':r.get('away_loses'),'away_gf':r.get('away_goals_for'),'away_ga':r.get('away_goals_against')}
    return out

def check_table(calc, official, label):
    if set(calc)!=set(official): raise RuntimeError(f'{label}: team set differs {set(calc)^set(official)}')
    fields=['played','wins','draws','loses','points','gf','ga','home_played','away_played','home_wins','home_draws','home_loses','home_gf','home_ga','away_wins','away_draws','away_loses','away_gf','away_ga']
    errors=[]
    for t,c in calc.items():
      for f in fields:
       if c[f]!=official[t][f]: errors.append(f'{t} {f}: calc {c[f]} != official {official[t][f]}')
    if errors: raise RuntimeError(label+' standings mismatch: '+'; '.join(errors[:20]))

def refresh():
    rounds=get_json(ROUNDS_URL)
    if not isinstance(rounds,list) or len(rounds)!=34 or sorted(int(r['round_number']) for r in rounds)!=list(range(1,35)): raise RuntimeError('Official round list incomplete or unexpected')
    raw=[]
    for rn in range(1,35):
      part=get_json(MATCH_URL.format(round=rn))
      if not isinstance(part,list) or len(part)!=9: raise RuntimeError(f'Round {rn}: expected 9 fixtures, got {len(part) if isinstance(part,list) else "invalid"}')
      raw.extend(part)
    matches=[compact_match(m) for m in raw]
    codes=[m['fixture_code'] for m in matches]
    if len(matches)!=306 or len(set(codes))!=306: raise RuntimeError('Fixture total/uniqueness validation failed')
    counts=Counter(x['round'] for x in matches)
    if any(counts[i]!=9 for i in range(1,35)): raise RuntimeError('Round fixture counts fail 9 each')
    appearances=Counter(t for m in matches for t in (m['home'],m['away']))
    if len(appearances)!=18 or set(appearances.values())!={34}: raise RuntimeError('Expected 18 teams with 34 appearances each')
    finals=[m for m in matches if m['state_id']==5]
    if any(m['home_goals'] is None or m['away_goals'] is None for m in finals): raise RuntimeError('Official final lacks score')
    unfinished=[m for m in matches if m['state_id']!=5]
    if any(m['home_goals'] is not None or m['away_goals'] is not None for m in unfinished): raise RuntimeError('Nonfinal scores were not nulled')
    table_json=get_json(TABLE_URL); table=table_json.get('standingsTable',[])
    if len(table)!=18: raise RuntimeError('Official standings not complete (18 rows)')
    official=official_simplify(table); clubs=sorted(appearances)
    calc=calc_table(matches,clubs); check_table(calc,official,'Official API')
    # Independently check completed results using ESPN, one UTC date at a time.
    dates=sorted({m['match_date_utc'][:10].replace('-','') for m in finals})
    events=[]
    for d in dates:
      payload=get_json(ESPN_URL.format(date=d)); events.extend(payload.get('events',[]))
    espn=[]
    for e in events:
      comps=e.get('competitions',[{}])[0].get('competitors',[])
      if len(comps)!=2: continue
      by={c.get('homeAway'):c for c in comps}
      if 'home' not in by or 'away' not in by: continue
      espn.append({'event_id':str(e.get('id')),'date':e.get('date'),'name':e.get('name'),'status':e.get('status',{}).get('type',{}).get('name'), 'home':by['home'].get('team',{}).get('displayName') or by['home'].get('team',{}).get('name'),'home_goals':by['home'].get('score'),'away':by['away'].get('team',{}).get('displayName') or by['away'].get('team',{}).get('name'),'away_goals':by['away'].get('score')})
    index=defaultdict(list)
    for e in espn:
      try: date=datetime.datetime.fromisoformat(e['date'].replace('Z','+00:00')).date().isoformat()
      except Exception: continue
      index[(date,alias(e['home']),alias(e['away']))].append(e)
    for m in finals:
      try: date=datetime.datetime.fromisoformat(m['match_date_utc'].replace('Z','+00:00')).date().isoformat()
      except Exception: raise RuntimeError(f"Bad official date {m['match_date_utc']}")
      found=index.get((date,alias(m['home']),alias(m['away'])),[])
      if len(found)!=1: raise RuntimeError(f"ESPN match not uniquely found: {date} {m['home']} v {m['away']} ({len(found)})")
      e=found[0]
      if e['status']!='STATUS_FULL_TIME' or str(e['home_goals'])!=str(m['home_goals']) or str(e['away_goals'])!=str(m['away_goals']): raise RuntimeError(f"ESPN status/score mismatch: {m['home']} v {m['away']} official {m['home_goals']}-{m['away_goals']} ESPN {e}")
    if len(finals)!=len(espn): raise RuntimeError(f'ESPN event count mismatch: {len(finals)} official finals vs {len(espn)} ESPN events fetched for completed dates')
    ec=[]
    for m in finals:
      ec.append({**m})
    espncalc=calc_table(ec,clubs); check_table(espncalc,official,'ESPN recomputation')
    now=datetime.datetime.now(datetime.timezone.utc)
    local=now.astimezone(ZoneInfo('America/Sao_Paulo'))
    log={'cutoff_utc':now.isoformat(),'cutoff_local':local.isoformat(),'league':'Liga Portugal Betclic','season_code':SEASON,'competition_external_id':COMP,'official_rounds_url':ROUNDS_URL,'official_fixtures_url_template':MATCH_URL,'official_standings_url':TABLE_URL,'espn_url_template':ESPN_URL,'rounds':34,'fixtures':306,'fixtures_per_round':9,'teams':18,'team_appearances':34,'official_finals':len(finals),'unstarted_or_nonfinal':len(matches)-len(finals),'espn_events_checked':len(espn),'espn_score_matches':len(finals),'official_table_teams_reconciled':18,'espn_table_teams_reconciled':18,'fixture_status_counts':{str(k):v for k,v in Counter(str(m['state_id']) for m in matches).items()},'validation':'PASS'}
    save('official_rounds.json',rounds); save('official_matches_compact.json',matches);save('official_standings_compact.json',table);save('espn_events_by_official_date.json',espn);save('source_log.json',log)
    print(json.dumps(log,ensure_ascii=False,indent=2))
if __name__=='__main__': refresh()
