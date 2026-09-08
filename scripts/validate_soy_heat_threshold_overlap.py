"""Compare real 29/30C weighted soybean inputs; no outcome estimation."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from summarize_contiguous_climate_contrasts import ROOT, checked, sha256
from allocate_outcome_exposures import KEYS

if __name__=='__main__':
    parent_paths=[ROOT/'data/interim'/d/'receipt.json' for d in (
        'two_crop_heat_real_20260908','soy_heat30_real_20260908')]
    tables=[];sources=[]
    for p in parent_paths:
        receipt=json.loads(p.read_text());records=[r for r in receipt['products'] if r['crop']=='soy']
        if len(records)!=1:raise ValueError('exactly one soybean product required')
        record=records[0]
        if (record['esm'],record['member'],record['scenario'],record['years'])!=('GFDL-ESM4','r1i1p1f1','ssp126',list(range(2042,2050))):
            raise ValueError('realization/period differs')
        frame=pd.read_parquet(checked(record))
        if frame.duplicated(KEYS).any():raise ValueError('duplicate key')
        tables.append(frame.set_index(KEYS).sort_index());sources.append(dict(path=str(p.relative_to(ROOT)),sha256=sha256(p)))
    a,b=tables
    if not a.index.equals(b.index):raise ValueError('threshold supports differ')
    common=sorted(set(a.columns)&set(b.columns))
    pd.testing.assert_frame_equal(a[common],b[common],check_exact=True)
    checks=[]
    for stage in (1,2,3):
        d29=a[f'stage{stage}_tmax_29c_days'];d30=b[f'stage{stage}_tmax_30c_days']
        delta=a[f'stage{stage}_tmax_29c_degree_days']-b[f'stage{stage}_tmax_30c_degree_days']
        if not np.isfinite(np.array([d29,d30,delta])).all():raise ValueError('nonfinite')
        if (d30>d29+1e-10).any() or (delta<d30-1e-10).any() or (delta>d29+1e-10).any():
            raise ValueError('29/30C degree-day/count bounds fail')
        checks.append(dict(stage=stage,min_degree_day_difference=float(delta.min()),
                           max_degree_day_difference=float(delta.max()),rows=len(delta)))
    out=ROOT/'data/interim/soy_heat30_real_20260908/threshold_overlap.json'
    if out.exists():raise ValueError('receipt exists')
    out.write_text(json.dumps(dict(status='passed',rows=len(a),unchanged_common_fields=common,
        sources=sources,stage_checks=checks,causal_or_scc_result=False,
        code_sha256=sha256(Path(__file__))),indent=2)+'\n')
    print('exact unchanged rainfall/control fields and threshold bounds pass',len(a),'rows')
