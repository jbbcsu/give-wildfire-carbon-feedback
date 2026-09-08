"""Export aggregate receipts only; never approval text, credentials or climate rows."""
import json
from pathlib import Path
from summarize_contiguous_climate_contrasts import ROOT, sha256

if __name__=='__main__':
    out=ROOT/'data/provenance/real_heat_cutout_20260908.json'
    if out.exists():raise ValueError('receipt already exists')
    paths=[
        'data/interim/authorized_heat_subset_real_20260908/receipt.json',
        'data/interim/authorized_heat_subset_real_20260908/reconciliation.json',
        'data/interim/two_crop_heat_real_20260908/receipt.json',
        'data/interim/two_crop_heat_real_20260908/historical_heat_ranges.json']
    names=['authorized_heat_subset_real_20260908','two_crop_heat_join_tests_20260908',
           'two_crop_heat_real_20260908','future_heat_range_tests_20260908','future_heat_ranges_20260908']
    paths += ['outputs/'+name+'_resource.json' for name in names]
    result=dict(role='aggregate_real_climate_input_validation_not_yield_or_scc',
        causal_or_scc_result=False,approval_record_exported=False,
        export_code_sha256=sha256(Path(__file__)),
        receipts=[dict(path=p,sha256=sha256(ROOT/p),content=json.loads((ROOT/p).read_text())) for p in paths],
        logs=[dict(path='outputs/'+name+'.log',sha256=sha256(ROOT/'outputs'/f'{name}.log')) for name in names])
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
