"""Cross-check two retained source assemblies on their exact common records."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from summarize_contiguous_climate_contrasts import MATRIX, checked, local_path, read_cell
from summarize_climate_scenario_contrasts import FEATURES, KEYS
from global_continuous_geographic_cluster_audit import ROOT,sha256


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    if args.out.exists():
        raise ValueError('output exists')
    long_result_path=local_path('data/provenance/climate_contiguous_contrasts_20260907.json')
    short_result_path=local_path('data/provenance/climate_scenario_contrasts_20260907.json')
    long_result=json.loads(long_result_path.read_text())
    short_result=json.loads(short_result_path.read_text())
    for path,digest in long_result['code_hashes'].items():
        checked(dict(path=path,sha256=digest))
    short_path=checked(dict(path='data/interim/isimip3b_expanded_fair_training/training.parquet',
                            sha256=short_result['input_sha256']))
    matrix_path=checked(dict(path=MATRIX,sha256=long_result['matrix_sha256']))
    rows=json.loads(matrix_path.read_text())['cells']
    result=dict(role='retained_source_overlap_check_not_new_climate_or_damage_estimate',
                code_sha256=sha256(Path(__file__)),
                long_result_sha256=sha256(long_result_path),short_result_sha256=sha256(short_result_path),
                years=list(range(2042,2050)),comparisons=[])
    for esm in sorted({r['esm'] for r in rows}):
        pieces=[]
        for batch in pq.ParquetFile(short_path).iter_batches(batch_size=8192,use_threads=False):
            frame=batch.to_pandas()
            mask=frame.esm_id.eq(esm)&frame.year.between(2042,2049)
            if mask.any():
                pieces.append(frame.loc[mask,['scenario']+KEYS+['feature_family','feature_value']])
        old=pd.concat(pieces,ignore_index=True).pivot(index=['scenario']+KEYS,columns='feature_family',values='feature_value')
        for row in [r for r in rows if r['esm']==esm]:
            audit=json.loads(checked(dict(path=row['audit'],sha256=row['audit_sha256'])).read_text())
            new,_=read_cell(audit,'mai_noirr')
            new=new.loc[new.year.between(2042,2049)].set_index(KEYS).sort_index()
            prior=old.loc[row['scenario']].sort_index()
            if not new.index.equals(prior.index):
                raise ValueError('overlap exact keys differ')
            differences=np.abs(new[FEATURES].to_numpy()-prior[FEATURES].to_numpy())
            maxima=differences.max(axis=0)
            tolerances=[1e-4 if f=='tmean_c' else 1e-3 if f in ('precip_mm','rx1day_mm','rx5day_mm') else 0 if f in ('wet_days_n','cdd_max_days') else 1e-10 for f in FEATURES]
            passed=bool(np.isfinite(differences).all() and (maxima<=tolerances).all())
            result['comparisons'].append(dict(esm=esm,scenario=row['scenario'],cell_years=len(new),
                passed=passed,max_absolute_differences=dict(zip(FEATURES,maxima.tolist())),
                absolute_tolerances=dict(zip(FEATURES,tolerances))))
    result['passed']=all(r['passed'] for r in result['comparisons']) and len(result['comparisons'])==11
    args.out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('source-overlap comparisons',len(result['comparisons']),'passed',result['passed'])
    if not result['passed']:
        raise SystemExit(1)


if __name__=='__main__':
    main()
