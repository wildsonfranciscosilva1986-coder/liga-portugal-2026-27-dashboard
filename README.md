# Liga Portugal Betclic 2026/27 — painel

Painel responsivo e interativo baseado nos dados oficiais da Liga Portugal, com verificação independente dos resultados finais pela ESPN. O site mantém o endereço de GitHub Pages deste repositório.

## Atualização e validação

O workflow `Refresh Liga Portugal Betclic 2026-27` roda diariamente às 06:10 no horário de São Paulo (`09:10 UTC`) e também pode ser iniciado manualmente. Antes da publicação, busca sequencialmente todas as 34 jornadas e a classificação oficial, verifica 306 jogos (9 por jornada), 18 equipes e 34 aparições por clube, recalcula a tabela e compara todos os campos disponíveis. Para cada resultado final, consulta a ESPN por data UTC, valida status FT e placar exato e recalcula a classificação de forma independente. A execução falha fechada se houver lacunas ou divergências.

O workflow salva os snapshots de origem e o HTML atualizado no mesmo repositório antes do deploy. Para atualizar manualmente:

```sh
python3 refresh_validate.py
python3 build_dashboard.py
python3 validate_build.py
```

## Conteúdo e ressalvas

- Classificação oficial, calendário/resultados, últimos cinco, recortes casa/fora, rankings Top 5, comparação de times e H2H da época.
- Placares de jogos não finalizados são omitidos; horários não confirmados são mostrados como “a confirmar”.
- As estimativas são descrições Poisson simplificadas, com pequenas amostras, e não são aconselhamento de apostas.
- As fichas de competição oficiais 911 e 915 divergem quanto à distribuição das vagas europeias. O painel não rotula zonas europeias nem atribui vagas até a discrepância ser resolvida por fonte normativa inequívoca.

Fontes: API oficial Liga Portugal e ESPN Soccer API (ver `source_snapshots/source_log.json` para URLs e corte de cada captura).
