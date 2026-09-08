"""Revalidate an unchanged failed payload; preserve original failure and receipts."""
import argparse
import json
from pathlib import Path
from validate_counterclim_crop_domain import validate_counterclim,AMENDMENT
from summarize_contiguous_climate_contrasts import ROOT,sha256


def main():
    p=argparse.ArgumentParser();p.add_argument('--input-dir',type=Path,required=True);args=p.parse_args()
    d=args.input_dir.resolve();out=d/'crop_domain_receipt.json';failure=d/'failure.json'
    if not d.is_relative_to(ROOT/'data/interim') or out.exists():raise ValueError('new receipt in existing ignored input directory required')
    r=json.loads(failure.read_text())
    if r['status']!='failed_preserved' or not r['error'].startswith('cutout contains '):raise ValueError('not the preserved full-grid missingness failure')
    cp=ROOT/r['config_path']
    if sha256(cp)!=r['config_sha256']:raise ValueError('original source config changed')
    c=json.loads(cp.read_text());var=c['specifiers']['climate_variable'];file=d/f'{var}_cutout.nc'
    if sha256(file)!=r['climate_sha256'] or sha256(d/'cutout.zip')!=r['archive_sha256']:
        raise ValueError('preserved payload hash differs')
    content=validate_counterclim(file,c)
    r['original_failure']=dict(path=str(failure.relative_to(ROOT)),sha256=sha256(failure),
        error=r.pop('error'),error_type=r.pop('error_type'))
    r.update(status='crop_domain_climate_content_validated',content_validation=content,
        revalidation_no_download=True,original_full_grid_gate_failed=True,
        domain_amendment_sha256=sha256(ROOT/AMENDMENT),
        artifact_hashes={file.name:sha256(file),'cutout.zip':sha256(d/'cutout.zip')})
    r['code_hashes'].update({name:sha256(ROOT/'scripts'/name) for name in ('revalidate_counterclim_cutout.py','validate_counterclim_crop_domain.py')})
    out.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
    print('New crop-domain receipt; original missingness failure and payload unchanged',content['crop_cells'])


if __name__=='__main__':main()
