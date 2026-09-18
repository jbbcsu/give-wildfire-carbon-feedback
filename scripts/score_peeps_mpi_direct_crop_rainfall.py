#!/usr/bin/env python3
"""Score published PEEPS monthly levels against two-member source rainfall."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import calendar

import numpy as np
import xarray as xr

from reconstruct_peeps_mpi_ssp585_rainfall import summarize


AUTHOR_SHA = 'fafe91fafb0f64b1448501bb49b623e21ad86e3c882a6b65b5fb337d8b6fa753'
GMST_SHA = 'cd632ffb21d171c48787f5d4766a2ae29f22d657db56a074738a7dc2c9a2bad3'
DIRECT_RECEIPTS = {
    ('r1i1p1f1', 2015): 'c42d66fb1355b1aadf50d5504b04db3bfbc05951becbd353ae3de6543cec373a',
    ('r1i1p1f1', 2100): 'a743a103679f734b2b499213d3b5906879cf10cc1e289bb2776d0601ada6445a',
    ('r2i1p1f1', 2015): 'f6a500f12b2ef585a4794ebb6b0a019eba773dcc5d3620f10e77c364efacd352',
    ('r2i1p1f1', 2100): '6b38c160a4ac6ac1432d6522e593a79f2fe0c4dd36733655e3e2c555650424eb',
}
MEMBERS = ('r1i1p1f1', 'r2i1p1f1')
YEARS = (2015, 2100)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('author_receipt', type=Path)
    parser.add_argument('gmst_receipt', type=Path)
    parser.add_argument('direct_receipts', nargs=4, type=Path)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    author_path, gmst_path, output = (x.resolve() for x in
                                      (args.author_receipt, args.gmst_receipt, args.out_dir))
    direct_paths = [x.resolve() for x in args.direct_receipts]
    if (any(not path.is_relative_to(root / 'data/interim') for path in
            (author_path, gmst_path, output, *direct_paths))
            or output.exists() or shutil.disk_usage(root).free < 130 * 2**30):
        parser.error('ignored project inputs, fresh output and disk reserve required')
    if sha(author_path) != AUTHOR_SHA or sha(gmst_path) != GMST_SHA:
        raise ValueError('published author source receipt changed')
    author, gmst_record = json.loads(author_path.read_text()), json.loads(gmst_path.read_text())
    if (author['model'] != 'MPI-ESM1-2-HR' or author['scenario'] != 'ssp585'
            or author['outer_archive_md5'] != 'eed1a0e8a43bf915c78ec68d0f37e357'):
        raise ValueError('wrong published source')
    gmst_file = root / gmst_record['output_relative_to_project']
    if sha(gmst_file) != gmst_record['member_sha256']:
        raise ValueError('published GMST member changed')
    with xr.open_dataset(gmst_file) as dataset:
        calendar_year = dataset.time.dt.year.values.astype(int)
        absolute_gmst = dataset.tas.values.astype(float)
    if not np.array_equal(calendar_year, np.arange(2015, 2101)):
        raise ValueError('published annual GMST years changed')
    temperature = {year: float(absolute_gmst[calendar_year == year][0]) for year in YEARS}
    artifacts = {}
    for path in direct_paths:
        receipt = json.loads(path.read_text())
        if (receipt['status'] != 'single_member_single_chunk_direct_mpi_crop_rainfall_not_scored'
                or len(receipt['members']) != 1 or len(receipt['years']) != 1
                or len(receipt['chunks']) != 1 or not receipt['chunks'][0]['gcs_crc32c_verified']):
            raise ValueError('direct source chunk incomplete or CRC unverified')
        key = (receipt['members'][0], receipt['years'][0])
        if key not in DIRECT_RECEIPTS or sha(path) != DIRECT_RECEIPTS[key] or key in artifacts:
            raise ValueError('direct source receipt hash/set differs')
        npz = path.parent / 'direct_crop_center_monthly_mm.npz'
        if sha(npz) != receipt['direct_arrays_sha256']:
            raise ValueError('direct extracted array changed')
        with np.load(npz, allow_pickle=False) as saved:
            arrays = {name: saved[name].copy() for name in saved.files}
        artifacts[key] = (receipt, arrays)
    if set(artifacts) != set(DIRECT_RECEIPTS):
        raise ValueError('four-member-year source matrix incomplete')
    first = artifacts[(MEMBERS[0], YEARS[0])][1]
    hectares = first['hectares']
    ii, jj = first['ii'], first['jj']
    if (len(hectares) != 30821 or not np.isfinite(hectares).all()
            or not np.all(hectares > 0)):
        raise ValueError('rainfed crop weights changed')
    for _, arrays in artifacts.values():
        if not all(np.array_equal(arrays[field], first[field]) for field in ('hectares', 'ii', 'jj')):
            raise ValueError('direct crop center mapping/weights differ across chunks')
    direct = {}
    for year in YEARS:
        a = artifacts[(MEMBERS[0], year)][1][f'{MEMBERS[0]}_{year}_monthly_mm']
        b = artifacts[(MEMBERS[1], year)][1][f'{MEMBERS[1]}_{year}_monthly_mm']
        if a.shape != (12, len(hectares)) or b.shape != a.shape:
            raise ValueError('direct member monthly geometry differs')
        direct[year] = (a + b) / 2
    predicted = {year: np.empty((12, len(hectares)), dtype=np.float64) for year in YEARS}
    if len(author['selected_members']) != 12:
        raise ValueError('published monthly coefficient count changed')
    for month, member in enumerate(author['selected_members'], 1):
        path = author_path.parent / member['name']
        if sha(path) != member['sha256'] or not member['name'].endswith(
                f'_patterns_{("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")[month-1]}.nc'):
            raise ValueError('published coefficient file changed')
        with xr.open_dataset(path) as ds:
            beta, alpha = ds.slope.values[0, ii, jj], ds.intercept.values[0, ii, jj]
            for year in YEARS:
                predicted[year][month - 1] = (beta * temperature[year] + alpha) * 86400 * calendar.monthrange(year, month)[1]
    results = []
    for year in YEARS:
        results.append({'year': year, 'author_absolute_gmst_K': temperature[year],
                        **summarize(direct[year], predicted[year], hectares)})
    output.mkdir(parents=True)
    arrays = {'hectares': hectares, 'ii': ii, 'jj': jj}
    for year in YEARS:
        arrays[f'direct_ensemble_mean_mm_{year}'] = direct[year]
        arrays[f'published_mm_{year}'] = predicted[year]
    saved = output / 'source_vs_published_crop_center_mm.npz'
    np.savez_compressed(saved, **arrays)
    report = {'status': 'same_source_in_sample_peeps_monthly_reconstruction_not_holdout_or_scc',
              'author_receipt_sha256': AUTHOR_SHA, 'gmst_receipt_sha256': GMST_SHA,
              'direct_receipt_sha256': {f'{m}_{y}': DIRECT_RECEIPTS[(m, y)]
                                        for m in MEMBERS for y in YEARS},
              'source_vs_published_arrays_sha256': sha(saved),
              'crop_center_count': len(hectares), 'rainfed_maize_area_ha': float(hectares.sum()),
              'results': results, 'yield_damage_scc_estimated': False}
    (output / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'results':
                      [{k: value for k, value in result.items() if k != 'months'}
                       for result in results]}))


if __name__ == '__main__':
    main()
