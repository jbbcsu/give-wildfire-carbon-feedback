#!/usr/bin/env python3
"""Probe positivity of one published PEEPS model/month against its own GMST.

No outcome data or holdout is used; this is a physical-screen diagnostic.
"""
import argparse
from decimal import Decimal, getcontext
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
import xarray as xr


YEARS = (2015, 2030, 2050, 2100)


def checked_source(project, receipt_path):
    receipt_path = receipt_path.resolve()
    if not receipt_path.is_relative_to(project / 'data/interim'):
        raise ValueError('only ignored project interim inputs accepted')
    record = json.loads(receipt_path.read_text())
    path = project / record['output_relative_to_project']
    if path.parent != receipt_path.parent or not path.is_file():
        raise ValueError('source path/receipt mismatch')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    if path.stat().st_size != record['member_bytes'] or digest.hexdigest() != record['member_sha256']:
        raise ValueError('source checksum or size changed')
    return path, record


def probe(coefficient_path, gmst_path):
    with xr.open_dataset(coefficient_path) as coef, xr.open_dataset(gmst_path) as gmst:
        if coef.attrs.get('source_id') != 'MPI-ESM1-2-HR' or coef.attrs.get('experiment_id') != 'ssp585':
            raise ValueError('wrong published precipitation pattern')
        if coef.attrs.get('variable_id') != 'pr' or coef.attrs.get('variable_units') != 'kg m-2 s-1':
            raise ValueError('unexpected source rainfall units')
        if dict(coef.sizes) != {'param': 1, 'lat': 192, 'lon': 384}:
            raise ValueError('unexpected published coefficient grid')
        year = gmst.time.dt.year.values.astype(int)
        tas = gmst.tas.values.astype(float)
        if len(year) != 86 or not np.array_equal(year, np.arange(2015, 2101)):
            raise ValueError('GMST not contiguous 2015-2100')
        if not np.isfinite(tas).all() or not np.all((250 < tas) & (tas < 330)):
            raise ValueError('invalid published absolute GMST')
        slope = coef.slope.values[0]
        intercept = coef.intercept.values[0]
        if not (np.isfinite(slope).all() and np.isfinite(intercept).all()):
            raise ValueError('nonfinite published coefficients')
        getcontext().prec = 50
        results = []
        for y in YEARS:
            T = float(tas[np.where(year == y)[0][0]])
            prediction = slope * T + intercept
            if not np.isfinite(prediction).all():
                raise ValueError('nonfinite predicted rainfall')
            audit = []
            for i, j in ((0, 0), (46, 96), (96, 192), (191, 383)):
                exact = Decimal(str(float(slope[i, j]))) * Decimal(str(T)) + Decimal(str(float(intercept[i, j])))
                if abs(float(exact) - float(prediction[i, j])) > 2e-18:
                    raise ValueError('independent Decimal sentinel differs')
                audit.append([i, j, float(exact)])
            results.append({'year': y, 'author_gmst_K': T,
                            'negative_native_global_cells': int(np.count_nonzero(prediction < 0)),
                            'zero_native_global_cells': int(np.count_nonzero(prediction == 0)),
                            'min_predicted_mm_per_day': float(prediction.min() * 86400),
                            'max_predicted_mm_per_day': float(prediction.max() * 86400),
                            'decimal_sentinels_flux_kg_m2_s': audit})
    return {'status': 'published_author_same_scenario_positivity_probe_not_holdout',
            'source_model': 'MPI-ESM1-2-HR', 'source_scenario': 'ssp585',
            'month': 'dec', 'grid_cell_count_including_ocean': 192 * 384,
            'precipitation_flux_units': 'kg m-2 s-1', 'results': results,
            'crop_weighting_applied': False, 'yield_damage_scc_estimated': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('coefficient_receipt', type=Path)
    parser.add_argument('gmst_receipt', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    if shutil.disk_usage(project).free < 130 * 2**30:
        raise RuntimeError('free disk below reserve')
    coefficient_path, coefficient_receipt = checked_source(project, args.coefficient_receipt)
    gmst_path, gmst_receipt = checked_source(project, args.gmst_receipt)
    if coefficient_receipt['model'] != gmst_receipt['model'] or coefficient_receipt['scenario'] != gmst_receipt['scenario']:
        raise ValueError('published coefficient and predictor mismatch')
    output_path = args.output.resolve()
    if not output_path.is_relative_to(project / 'data/interim') or output_path.exists():
        parser.error('fresh ignored interim output required')
    result = probe(coefficient_path, gmst_path)
    result['coefficient_sha256'] = coefficient_receipt['member_sha256']
    result['author_gmst_sha256'] = gmst_receipt['member_sha256']
    result_text = json.dumps(result, indent=2) + '\n'
    if len(result_text.encode()) > 16384:
        raise ValueError('unexpected output size')
    output_path.write_text(result_text)
    print(json.dumps({'status': result['status'], 'results':
                      [{k: value for k, value in item.items() if k != 'decimal_sentinels_flux_kg_m2_s'}
                       for item in result['results']]}))


if __name__ == '__main__':
    main()
