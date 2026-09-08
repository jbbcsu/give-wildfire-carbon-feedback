"""Export owned aggregate receipts/hashes, not publisher content or climate rows."""
import json
from pathlib import Path
from summarize_contiguous_climate_contrasts import ROOT, sha256

if __name__=='__main__':
    out=ROOT/'data/provenance/heat30_welfare_progress_20260908.json'
    if out.exists():raise ValueError('receipt exists')
    names=['heat30_join_tests','heat30_range_tests','soy_heat30_real','soy_heat30_ranges',
           'soy_heat_threshold_overlap','hultgren_si_acquisition','hultgren_si_text',
           'hultgren_si_render','anticipated_weather_market_tests']
    files=['data/interim/soy_heat30_real_20260908/'+f for f in ('receipt.json','historical_heat_ranges.json','threshold_overlap.json')]
    files+=['outputs/'+n+'_20260908_resource.json' for n in names]
    result=dict(causal_or_scc_result=False,role='heat_inputs_and_primary_source_method_implementation_progress',
        export_code_sha256=sha256(Path(__file__)),
        receipts=[dict(path=p,sha256=sha256(ROOT/p),content=json.loads((ROOT/p).read_text())) for p in files],
        logs=[dict(path='outputs/'+n+'_20260908.log',sha256=sha256(ROOT/'outputs'/f'{n}_20260908.log')) for n in names],
        source_acquisition_receipt_sha256=sha256(ROOT/'data/provenance/hultgren_methods_si_acquisition_20260908.json'),
        visually_reviewed_pdf_pages_one_based=list(range(79,89)),
        rendered_page_hashes={str(i):sha256(ROOT/'outputs'/f'hultgren_si_K_20260908-{i}.png') for i in range(79,89)},
        publisher_content_exported=False)
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
