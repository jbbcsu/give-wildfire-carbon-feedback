#!/usr/bin/env python3
import csv,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 cfg=json.loads((ROOT/'config/macro_comparator_v1.json').read_text());src=ROOT/cfg['source']['result_file'];out=ROOT/cfg['outputs']['summary']
 with out.open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
 checks={'source_hash':digest(src)==cfg['source']['sha256'],'three_published_rows':len(rows)==3,'central_exact':abs(float(rows[0]['scc'])-1206.96927919086)<1e-9,'published_ci':rows[0]['lower_95']=='399' and rows[0]['upper_95']=='2015','nonadditive':all(r['additive_to_give']=='false' for r in rows),'not_residual':all(r['omitted_sector_residual']=='false' for r in rows),'all_comparability_gates_closed':not any(cfg['comparability_gates'].values()),'status':cfg['status']=='MUTUALLY_EXCLUSIVE_COMPARATOR'}
 result={'schema':'macro_comparator_validation/v1','status':'PASS' if all(checks.values()) else 'FAIL','checks':checks};(ROOT/cfg['outputs']['validation']).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps(result,indent=2));return 0 if all(checks.values()) else 1
if __name__=='__main__':raise SystemExit(main())
