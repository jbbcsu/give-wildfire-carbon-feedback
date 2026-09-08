"""Export aggregate independent-model/window evidence; no raw climate rows."""
import json
from pathlib import Path
from summarize_contiguous_climate_contrasts import ROOT,sha256

if __name__=='__main__':
    out=ROOT/'data/provenance/ipsl_and_window_20260908.json'
    if out.exists():raise ValueError('receipt exists')
    names=['ipsl_realization_join_tests','ipsl_pair_comparison_tests','ipsl_paired_heat_climate','precip_window_tests','precip_window_sensitivity']
    files=[]
    for s in ('ssp126','ssp585'):
        names += ['ipsl_'+s+x for x in ('_heat_request','_acquisition','_maize_heat29','_soy_heat30')]
        files += ['data/interim/ipsl_'+s+x+'_20260908/receipt.json' for x in ('_heat_cutout','_maize_heat29','_soy_heat30')]
    files += ['data/interim/ipsl_ssp585_heat_cutout_20260908/'+x for x in ('paired_climate_comparison.json','precipitation_window_sensitivity.json')]
    files += ['outputs/'+n+'_20260908_resource.json' for n in names]
    result=dict(role='independent_model_and_exploratory_window_climate_diagnostics',causal_or_scc_result=False,
        code_sha256=sha256(Path(__file__)),
        receipts=[dict(path=p,sha256=sha256(ROOT/p),content=json.loads((ROOT/p).read_text())) for p in files],
        logs=[dict(path='outputs/'+n+'_20260908.log',sha256=sha256(ROOT/'outputs'/f'{n}_20260908.log')) for n in names])
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
