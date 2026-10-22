#!/usr/bin/env python3
"""Validate published artifact content against the latest fail-closed snapshots."""
import json,re,sys
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parent
f=json.loads((ROOT/'source_snapshots/official_matches_compact.json').read_text())
s=json.loads((ROOT/'source_snapshots/official_standings_compact.json').read_text())
log=json.loads((ROOT/'source_snapshots/source_log.json').read_text())
page=(ROOT/'index.html').read_text(encoding='utf-8')
assert len(f)==306 and len(s)==18 and log.get('validation')=='PASS', 'source validation manifest not PASS or counts wrong'
assert log.get('official_finals')==72 and log.get('espn_score_matches')==72, 'independent result audit incomplete'
assert sum(m['state_id']==5 for m in f)==log['official_finals']
assert all((m['home_goals'] is not None and m['away_goals'] is not None) if m['state_id']==5 else (m['home_goals'] is None and m['away_goals'] is None) for m in f), 'final/nonfinal score sanitization failed'
assert 'id="data" type="application/json">' in page
embedded=page.split('id="data" type="application/json">',1)[1].split('</script>',1)[0]
payload=json.loads(embedded)
assert payload['fixtures']==f and payload['standings']==s, 'embedded dataset differs from validated snapshots'
assert payload['source']['cutoff_local']==log['cutoff_local']
for marker in ['id="table"','id="profileTeam"','id="roundSelect"','id="metricSelect"','id="splitSelect"','id="homeTeam"','id="awayTeam"','id="h2h"','id="estimate"']:
 assert marker in page, f'missing UI component: {marker}'
assert 'Zonas oficiais — validação pendente' in page and 'não é aconselhamento de apostas' in page.lower(), 'required disclosure missing'
assert (ROOT/'site/index.html').read_text(encoding='utf-8')==page, 'deploy artifact differs from validated root HTML'
class Check(HTMLParser):
 def __init__(self):super().__init__();self.ids=[]
 def handle_starttag(self,tag,attrs):
  for k,v in attrs:
   if k=='id':self.ids.append(v)
c=Check();c.feed(page)
assert len(c.ids)==len(set(c.ids)), 'duplicate HTML id'
print(json.dumps({'status':'PASS','fixtures':len(f),'finals':log['official_finals'],'teams':len(s),'official_table_reconciled':log['official_table_teams_reconciled'],'ESPN_scores_reconciled':log['espn_score_matches'],'embedded_dataset_matches':True,'interactive_sections':['standings/team selection','profile and last five','round/team fixture filters','Top 5 metric and split filters','matchup 1X2/goals','H2H'],'cutoff_local':log['cutoff_local'],'html_bytes':len(page.encode())},ensure_ascii=False,indent=2))
