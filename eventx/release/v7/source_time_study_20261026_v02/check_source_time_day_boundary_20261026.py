from collections import defaultdict
from pathlib import Path
import json
import pyarrow.parquet as pq
from eventx.v7.source_time_quote_inputs_20261026 import SourceTimeQuoteTape
root=Path('/Users/zhurong/UROP');dev=root/'data/v7/family_training_20261025_v02';rows=defaultdict(list)
reference=pq.read_table(root/'data/v7/source_time_study_20261026/development/grid_ledger.parquet',columns=['market_id','date','t','features']).to_pylist()
checks=[]
for date,prior in [('2026-05-08','2026-05-07'),('2026-05-09','2026-05-08')]:
 by=defaultdict(list)
 for hour in [prior+'T23',date+'T00']:
  for row in pq.read_table(dev/'source_dev/hours'/hour/'quotes.parquet').to_pylist():by[row['market'].decode()].append(row)
 for r in reference:
  if r['date']!=date or r['t']%86400!=1800:continue
  actual=SourceTimeQuoteTape(by[r['market_id']]).features(r['t'])
  if actual!=r['features']:checks.append({'date':date,'market_id':r['market_id'],'old':r['features'],'continuous':actual})
out=root/'data/v7/source_time_study_20261026/day_boundary_diagnostic.json'
out.write_text(json.dumps({'checked_decisions':100,'differences':checks},indent=2)+'\n')
print(json.dumps({'checked_decisions':100,'differences':len(checks),'details':checks},indent=2))
