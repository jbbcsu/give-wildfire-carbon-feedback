#!/usr/bin/env python3
"""Extract published macro SCC comparison rows without recomputing or harmonizing them."""
import csv,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 cfg=json.loads((ROOT/'config/macro_comparator_v1.json').read_text());src=ROOT/cfg['source']['result_file']
 if digest(src)!=cfg['source']['sha256']:raise ValueError('source result hash mismatch')
 with src.open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
 selected=[]
 for spec in cfg['published_result']['comparison_rows']:
  want='global' if 'global' in spec['label'] else 'local';data='BU' if spec['label'].startswith('BU') else 'PWT'
  matches=[r for r in rows if r['Year']=='2024' and r['Data']==data and r['Temperature']==want]
  if len(matches)!=1:raise ValueError('published comparison row not unique')
  actual=float(matches[0]['SCC'])
  if abs(actual-spec['scc'])>1e-9:raise ValueError('published SCC mismatch')
  selected.append({'comparison':spec['label'],'publication':'Bilal and Kaenzig (2026)','paper_doi':cfg['source']['paper_doi'],'estimate_year':2024,'currency_unit':'2024 international dollars per metric tonne CO2','scc':format(actual,'.12f'),'lower_95':399 if spec['label'].startswith('PWT global') else '', 'upper_95':2015 if spec['label'].startswith('PWT global') else '', 'pure_rate_time_preference':'2%','additive_to_give':'false','omitted_sector_residual':'false'})
 out=ROOT/cfg['outputs']['summary'];out.parent.mkdir(parents=True,exist_ok=True)
 with out.open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(selected[0]),lineterminator='\n');w.writeheader();w.writerows(selected)
 receipt={'schema':'macro_comparator_receipt/v1','created_at_utc':datetime.now(timezone.utc).isoformat(),'status':cfg['status'],'source':{'path':cfg['source']['result_file'],'sha256':cfg['source']['sha256'],'repository_commit':cfg['source']['commit']},'output':{'path':cfg['outputs']['summary'],'sha256':digest(out),'rows':len(selected)},'additive_to_give':False,'omitted_sector_residual':False}
 rp=ROOT/cfg['outputs']['receipt'];rp.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');print(json.dumps(receipt,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
