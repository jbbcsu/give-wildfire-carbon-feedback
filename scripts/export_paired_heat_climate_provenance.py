"""Aggregate scenario pilot evidence; no climate rows or third-party content."""
import json
from pathlib import Path
from summarize_contiguous_climate_contrasts import ROOT,sha256

if __name__=='__main__':
    out=ROOT/'data/provenance/paired_heat_climate_20260908.json'
    if out.exists():raise ValueError('receipt exists')
    names=['ssp585_heat_request','registered_heat_archive_tests','ssp585_heat_acquisition',
           'scenario_heat_join_tests','ssp585_maize_heat29','ssp585_soy_heat30',
           'paired_heat_climate_tests','paired_heat_climate','ssp585_maize_heat_ranges','ssp585_soy_heat_ranges']
    sources=['data/interim/ssp585_heat_cutout_20260908/receipt.json',
             'data/interim/ssp585_heat_cutout_20260908/paired_climate_comparison.json']
    sources += ['data/interim/'+d+'/'+f for d in ('ssp585_maize_heat29_20260908','ssp585_soy_heat30_20260908') for f in ('receipt.json','historical_heat_ranges.json')]
    sources += ['outputs/'+n+'_20260908_resource.json' for n in names]
    result=dict(role='matched_climate_scenario_inputs_only',causal_or_scc_result=False,
        code_sha256=sha256(Path(__file__)),
        receipts=[dict(path=p,sha256=sha256(ROOT/p),content=json.loads((ROOT/p).read_text())) for p in sources],
        logs=[dict(path='outputs/'+n+'_20260908.log',sha256=sha256(ROOT/'outputs'/f'{n}_20260908.log')) for n in names])
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
