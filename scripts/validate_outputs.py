#!/usr/bin/env python3
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p):
 with p.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def main():
 cfg=json.loads((ROOT/'config/grid_td_benchmark_v1.json').read_text());annual=read(ROOT/cfg['outputs']['annual']);by=read(ROOT/cfg['outputs']['by_gcm']);summary=read(ROOT/cfg['outputs']['summary'])
 checks={'annual_rows':len(annual)==276*6*3,'by_rows':len(by)==2*6*3,'summary_rows':len(summary)==2*3,'years':{int(r['year']) for r in annual}==set(range(2025,2301)),'variants':{r['adaptation_variant'] for r in annual}=={'NoAdapt','Proactive','Reactive'},'claim_gate':cfg['scope']['additivity_to_give_authorized'] is False,'no_outage_claim':all(r['outage_welfare_included']=='false' for r in by),'nonadditive':all(r['additive_to_give']=='false' for r in summary),'finite':all(abs(float(r['mean_2020usd_per_tco2']))<100 for r in summary)}
 out={'schema':'grid_td_validation/v1','status':'PASS' if all(checks.values()) else 'FAIL','checks':checks};(ROOT/cfg['outputs']['validation']).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');print(json.dumps(out,indent=2));return 0 if all(checks.values()) else 1
if __name__=='__main__':raise SystemExit(main())
