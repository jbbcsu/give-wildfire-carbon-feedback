"""Publish aggregate audits, including the initial full-grid validation failure."""
import json
from pathlib import Path
import shutil
from summarize_contiguous_climate_contrasts import ROOT,sha256


def main():
    out=ROOT/'data/provenance/factual_counterclim_pilot_20260908.json'
    if out.exists():raise ValueError('new aggregate provenance required')
    files=[];jobs=[];directories=[]
    for scenario in ('obsclim','counterclim'):
        for var in ('pr','tas','tasmax'):
            for year in (1981,1991,2001):
                stem=f'{scenario}_{var}_{year}_20260908';d='data/interim/'+stem
                directories.append(d);files.append(d+'/receipt.json')
                jobs += [stem+'_request',stem+'_acquisition']
                if (scenario,var,year)==('counterclim','pr',1981):
                    files += [d+'/failure.json',d+'/crop_domain_receipt.json']
        for crop in ('mai','soy'):
            stem=f'{scenario}_{crop}_joint_20260908';d='data/interim/'+stem
            directories.append(d);files.append(d+'/receipt.json');jobs.append(stem)
    files += ['data/interim/counterclim_soy_joint_20260908/paired_comparison.json',
              'data/provenance/counterclim_catalogue_feasibility_20260908.json',
              'data/interim/obsclim_soy_joint_20260908/parity_diagnosis.json',
              'data/interim/obsclim_soy_joint_20260908/precision_reconciliation.json']
    jobs += ['counterclim_catalogue_feasibility_20260908','counterclim_lineage_description_20260908',
        'counterclim_lineage_caveats_20260908','counterclim_missing_domain_audit_20260908',
        'observational_climate_contract_20260908','counterclim_crop_domain_tests_20260908',
        'factual_counterclim_comparison_tests_20260908','counterclim_pr_1981_revalidation_20260908',
        'counterclim_registered_acquisition_tests_20260908','counterclim_full_grid_gate_tests_20260908',
        'counterclim_full_grid_gate_tests_20260908_v2',
        'counterclim_full_grid_gate_tests_20260908_v3','counterclim_owned_disk_monitor_tests_20260908',
        'factual_counterclim_comparison_real_20260908','factual_counterclim_comparison_real_20260908_v2',
        'factual_counterclim_comparison_tests_20260908_v2','factual_parity_diagnosis_20260908',
        'factual_parity_year_location_20260908','factual_precision_reconciliation_20260908',
        'factual_precision_reconciliation_20260908_v2']
    resources=['outputs/'+j+'_resource.json' for j in jobs];records=[]
    permitted_failure='outputs/counterclim_pr_1981_20260908_acquisition_resource.json'
    for name in files+resources:
        path=ROOT/name;r=json.loads(path.read_text())
        if name in resources:
            if name in (permitted_failure,'outputs/factual_counterclim_comparison_real_20260908_resource.json',
                        'outputs/factual_precision_reconciliation_20260908_resource.json'):
                if r['status']!='command_failed' or r['returncode']!=1:raise ValueError('original failure evidence differs')
            elif name in ('outputs/counterclim_full_grid_gate_tests_20260908_resource.json','outputs/counterclim_full_grid_gate_tests_20260908_v2_resource.json'):
                if r['status']!='disk_reserve_breached' or r['returncode']!=-9:raise ValueError('original disk-stop evidence differs')
            elif r['status']!='completed':raise ValueError('unexpected incomplete job')
        if name.endswith('/receipt.json') or name.endswith('/crop_domain_receipt.json'):
            for key in ('artifacts','artifact_hashes'):
                for artifact,digest in r.get(key,{}).items():
                    if sha256(path.parent/artifact)!=digest:raise ValueError('changed climate artifact')
            for product in r.get('products',[]):
                if sha256(ROOT/product['path'])!=product['sha256']:raise ValueError('changed joint product')
        records.append(dict(path=name,sha256=sha256(path),content=r))
    comparison=json.loads((ROOT/'data/interim/counterclim_soy_joint_20260908/paired_comparison.json').read_text())
    if comparison['status']!='paired_climate_diagnostic_validated':raise ValueError('paired result is not validated')
    retained={d:sum(p.stat().st_size for p in (ROOT/d).rglob('*') if p.is_file()) for d in directories}
    previous=ROOT/'data/provenance/ipsl_historical_climate_benchmark_20260908.json'
    prev=json.loads(previous.read_text())
    result=dict(role='paired_historical_trend_climate_inputs_not_crop_damages',causal_or_scc_result=False,
        original_full_grid_failure_preserved=True,crop_domain_imputation=False,
        original_parity_failure_preserved=True,original_uniform_precision_hypothesis_failure_preserved=True,
        original_disk_guard_interruptions_preserved=2,
        records=records,logs=[dict(path='outputs/'+j+'.log',sha256=sha256(ROOT/'outputs'/f'{j}.log')) for j in jobs],
        retained_new_input_output_bytes=retained,total_retained_bytes=sum(retained.values()),
        prior_climate_stages_retained_bytes=prev['total_retained_bytes']+prev['previous_gfdl_historical_retained_bytes']+prev['previous_full_period_retained_bytes'],
        prior_provenance_sha256=sha256(previous),free_bytes_at_export=shutil.disk_usage(ROOT).free,
        code_sha256=sha256(Path(__file__)))
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('Aggregate audit bytes',out.stat().st_size,'new retained',result['total_retained_bytes'])


if __name__=='__main__':main()
