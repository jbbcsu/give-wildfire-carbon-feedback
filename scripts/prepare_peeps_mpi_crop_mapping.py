#!/usr/bin/env python3
"""Prepare a tiny verified MIRCA rainfed-maize to PEEPS-native mapping."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
import pyarrow.parquet as pq
import xarray as xr

from probe_peeps_december_crop_support import nearest_linear, nearest_circular


AUTHOR_RECEIPT_SHA256 = 'fafe91fafb0f64b1448501bb49b623e21ad86e3c882a6b65b5fb337d8b6fa753'
MIRCA_SHA256 = '7512ffc580928a03f75bbce5f3d4263c9bb2c631a8ff04075973acb4b149e4ba'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('author_receipt', type=Path)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    author_path, output = args.author_receipt.resolve(), args.out_dir.resolve()
    if (not author_path.is_relative_to(root / 'data/interim')
            or not output.is_relative_to(root / 'data/interim')
            or output.exists() or shutil.disk_usage(root).free < 130 * 2**30):
        parser.error('ignored input, fresh output and disk reserve required')
    if digest(author_path) != AUTHOR_RECEIPT_SHA256:
        raise ValueError('author coefficient receipt changed')
    author = json.loads(author_path.read_text())
    january = author_path.parent / 'MPI-ESM1-2-HR_ssp585_pr_monthly_patterns_jan.nc'
    entry = next((x for x in author['selected_members'] if x['name'] == january.name), None)
    if entry is None or digest(january) != entry['sha256']:
        raise ValueError('January author coefficient changed')
    weights = root / 'data/interim/mirca_os_v2/irrigation_shares_2000.parquet'
    if digest(weights) != MIRCA_SHA256:
        raise ValueError('MIRCA source changed')
    area = pq.read_table(weights,
                         columns=['lat', 'lon_360', 'crop', 'irrigation', 'rainfed_area_ha'],
                         filters=[('crop', '=', 'mai'), ('irrigation', '=', 'noirr')],
                         use_threads=False).to_pandas()
    if not len(area) or not ((area.crop == 'mai') & (area.irrigation == 'noirr')).all():
        raise ValueError('wrong crop or irrigation regime')
    if not np.isfinite(area.rainfed_area_ha.to_numpy(dtype=float)).all() or (area.rainfed_area_ha < 0).any():
        raise ValueError('invalid rainfed crop area')
    zero_rows = int((area.rainfed_area_ha == 0).sum())
    area = area.loc[area.rainfed_area_ha > 0].copy()
    if len(area) != 30821 or area.duplicated(['lat', 'lon_360']).any():
        raise ValueError('positive MIRCA support changed')
    lat, lon, hectares = (area[name].to_numpy(dtype=float) for name in
                          ('lat', 'lon_360', 'rainfed_area_ha'))
    with xr.open_dataset(january) as ds:
        native_lat, native_lon = ds.lat.values.copy(), ds.lon.values.copy()
    ii, jj = nearest_linear(lat, native_lat), nearest_circular(lon, native_lon)
    sample = np.linspace(0, len(lat) - 1, 100, dtype=int)
    for k in sample:
        expected_i = int(np.argmin(np.abs(native_lat - lat[k])))
        expected_j = int(np.argmin(np.abs(((native_lon - lon[k] + 180) % 360) - 180)))
        if ii[k] != expected_i or jj[k] != expected_j:
            raise ValueError('independent center-mapping audit disagrees')
    native_area = np.bincount(ii * len(native_lon) + jj, weights=hectares,
                              minlength=len(native_lat) * len(native_lon))
    if not np.isclose(native_area.sum(), hectares.sum(), rtol=1e-12, atol=0):
        raise ValueError('native-mapped rainfed area not conserved')
    output.mkdir(parents=True)
    arrays = output / 'mapping.npz'
    np.savez_compressed(arrays, ii=ii, jj=jj, hectares=hectares,
                        lat=lat, lon=lon, native_lat=native_lat, native_lon=native_lon)
    result = {'status': 'verified_peeps_native_rainfed_maize_center_mapping_not_exposure',
              'author_receipt_sha256': AUTHOR_RECEIPT_SHA256,
              'mirca_sha256': MIRCA_SHA256, 'mapping_sha256': digest(arrays),
              'positive_area_rows': len(hectares), 'zero_area_rows_excluded': zero_rows,
              'native_touched_cells': int(np.count_nonzero(native_area)),
              'rainfed_maize_area_ha': float(hectares.sum()),
              'independent_mapping_audit_rows': len(sample),
              'yield_damage_scc_estimated': False}
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
