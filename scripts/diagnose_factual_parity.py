"""Aggregate discrepancy audit only; does not accept or repair failed parity."""
import argparse
import json
from pathlib import Path
import numpy as np
from compare_factual_counterclim import load_product,observed,FEATURES,ZERO,KEYS,heat_basis_feature_names
from summarize_contiguous_climate_contrasts import sha256


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    if args.out.exists():raise ValueError('new diagnostic output required')
    result=dict(role='failed_factual_parity_diagnosis_not_climate_results',gate_changed=False,
        factual_parity_passed=False,comparisons=[],code_sha256=sha256(Path(__file__)))
    for crop,label,threshold in [('mai','maize',29),('soy','soy',30)]:
        new,receipt,source=load_product(crop,'obsclim');old,old_sources=observed(crop,label,threshold)
        a=old.set_index(KEYS).sort_index();b=new.set_index(KEYS).sort_index().loc[a.index]
        columns=FEATURES+[v for v in heat_basis_feature_names([threshold],3) if not v.endswith('tmean_c')]+[ZERO]
        features={}
        for col in columns:
            x=a[col].to_numpy(dtype=float);y=b[col].to_numpy(dtype=float);finite=np.isfinite(x)&np.isfinite(y)
            delta=y[finite]-x[finite]
            features[col]=dict(rows=len(a),old_nonfinite=int((~np.isfinite(x)).sum()),new_nonfinite=int((~np.isfinite(y)).sum()),
                mismatched_rows=int((~np.isclose(x,y,atol=1e-8,rtol=1e-10,equal_nan=True)).sum()),
                max_absolute_difference=float(np.abs(delta).max()),mean_difference=float(delta.mean()),
                median_absolute_difference=float(np.median(np.abs(delta))))
        result['comparisons'].append(dict(crop=crop,new_source=source,old_sources=old_sources,features=features))
    args.out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps([{c['crop']:c['features']} for c in result['comparisons']],indent=2))


if __name__=='__main__':main()
