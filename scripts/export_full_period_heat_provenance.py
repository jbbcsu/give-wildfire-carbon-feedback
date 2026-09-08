"""Persist aggregate full-period evidence and resource history, not climate rows."""
import json
from pathlib import Path
import shutil
from summarize_contiguous_climate_contrasts import ROOT,sha256


def main():
    out=ROOT/'data/provenance/full_period_heat_20260908.json'
    if out.exists():raise ValueError('receipt exists')
    files=[];directories=[];resources=[];logs=[]
    for model in ('gfdl','ipsl'):
        for scenario in ('ssp126','ssp585'):
            for year in (2031,2051):
                stem=f'{model}_{scenario}_{year}_heat_20260908'
                directories.append('data/interim/'+stem);files.append('data/interim/'+stem+'/receipt.json')
                for action in ('request','acquisition'):
                    resources.append(f'outputs/{stem}_{action}_resource.json');logs.append(f'outputs/{stem}_{action}.log')
                if (model,scenario,year)==('ipsl','ssp126',2031):
                    resources.append(f'outputs/{stem}_acquisition_v2_resource.json');logs.append(f'outputs/{stem}_acquisition_v2.log')
            for crop in ('mai','soy'):
                stem=f'{model}_{scenario}_{crop}_full_heat_20260908'
                directories.append('data/interim/'+stem)
                files += [f'data/interim/{stem}/'+n for n in ('receipt.json','historical_heat_ranges.json')]
                for job in (stem,f'{model}_{scenario}_{crop}_full_heat_ranges_20260908'):
                    resources.append('outputs/'+job+'_resource.json');logs.append('outputs/'+job+'.log')
        files += [f'data/interim/{model}_ssp585_soy_full_heat_20260908/'+n for n in ('exact_overlap.json','paired_climate_comparison.json')]
        for job in (f'{model}_full_heat_overlap_20260908',f'{model}_full_heat_comparison_20260908'):
            resources.append('outputs/'+job+'_resource.json');logs.append('outputs/'+job+'.log')
    for stem in ('fullperiod_heat_cutout_dates_20260908','fullperiod_prepare_heat_subset_pilot_20260908',
        'fullperiod_prepare_heat_subset_pilot_v2_20260908','fullperiod_authorized_heat_subset_pilot_v2_20260908',
        'fullperiod_full_period_heat_20260908','fullperiod_extend_heat_cutout_two_crops_20260908',
        'fullperiod_paired_heat_climate_20260908'):
        resources.append('outputs/'+stem+'_resource.json');logs.append('outputs/'+stem+'.log')
    receipts=[]
    for name in files+resources:
        p=ROOT/name;content=json.loads(p.read_text())
        # Bind climate/product payloads without copying them into Git.
        if name.endswith('/receipt.json'):
            for product in content.get('products',[]):
                if sha256(ROOT/product['path'])!=product['sha256']:raise ValueError('product changed')
            for artifact,digest in content.get('artifact_hashes',{}).items():
                if sha256(p.parent/artifact)!=digest:raise ValueError('cutout changed')
        receipts.append(dict(path=name,sha256=sha256(p),content=content))
    retained={d:sum(p.stat().st_size for p in (ROOT/d).rglob('*') if p.is_file()) for d in directories}
    report=dict(role='two_model_full_period_joint_climate_diagnostics',causal_or_scc_result=False,
        years=[2032,2059],latitudes=[39.25,39.75],not_global_representative=True,
        retained_new_input_and_output_bytes=retained,total_retained_bytes=sum(retained.values()),
        free_bytes_at_export=shutil.disk_usage(ROOT).free,receipts=receipts,
        logs=[dict(path=p,sha256=sha256(ROOT/p)) for p in logs],
        test_failure_note='Initial legacy source-request fixture used an undated fake filename. It was updated to a dated synthetic source and explicit Gregorian count to meet the strengthened contract. No empirical validation failed and no scientific gate was relaxed.',
        acquisition_wait_note='The first IPSL SSP1262031 acquisition check found the registered server job still started, downloaded nothing and created no output directory. After server completion the same job was acquired, with a separate v2 resource log. No request was resubmitted.',
        evolving_code_note='Receipts retain hashes at execution. Later helper changes add independent-model overlap dispatch and a helper-code hash; original receipts are not rewritten.',
        code_sha256=sha256(Path(__file__)))
    out.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print('aggregate provenance',out.stat().st_size,'bytes; retained',report['total_retained_bytes'],'bytes')


if __name__=='__main__':main()
