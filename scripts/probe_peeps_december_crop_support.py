#!/usr/bin/env python3
"""Check author PEEPS December negative rain on mapped MIRCA rainfed maize."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
import pyarrow.parquet as pq
import xarray as xr

from probe_peeps_author_december_prediction import checked_source, YEARS


WEIGHT_SHA256 = '7512ffc580928a03f75bbce5f3d4263c9bb2c631a8ff04075973acb4b149e4ba'


def nearest_linear(points, centers):
    """Nearest ascending noncircular center, lower index for exact ties."""
    if np.any(np.diff(centers) <= 0):
        raise ValueError('center coordinates must ascend')
    hi = np.clip(np.searchsorted(centers, points), 0, len(centers) - 1)
    lo = np.maximum(hi - 1, 0)
    return np.where(np.abs(points - centers[lo]) <= np.abs(points - centers[hi]), lo, hi)


def nearest_circular(points, centers):
    """Nearest 0..360 longitude center with explicit antimeridian wrap."""
    values = np.mod(points, 360.0)
    hi_raw = np.searchsorted(centers, values)
    hi = hi_raw % len(centers)
    lo = (hi_raw - 1) % len(centers)
    d_hi = np.abs(((values - centers[hi] + 180) % 360) - 180)
    d_lo = np.abs(((values - centers[lo] + 180) % 360) - 180)
    return np.where(d_lo <= d_hi, lo, hi)


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('coefficient_receipt', type=Path)
    parser.add_argument('gmst_receipt', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    if shutil.disk_usage(project).free < 130 * 2**30:
        raise RuntimeError('free disk below reserve')
    coef_path, coef_record = checked_source(project, args.coefficient_receipt)
    gmst_path, gmst_record = checked_source(project, args.gmst_receipt)
    if coef_record['model'] != gmst_record['model'] or coef_record['scenario'] != gmst_record['scenario']:
        raise ValueError('published pattern/predictor mismatch')
    if coef_record['model'] != 'MPI-ESM1-2-HR' or coef_record['scenario'] != 'ssp585':
        raise ValueError('pilot source changed')
    weight_path = project / 'data/interim/mirca_os_v2/irrigation_shares_2000.parquet'
    if file_hash(weight_path) != WEIGHT_SHA256:
        raise ValueError('MIRCA area table SHA256 mismatch')
    area = pq.read_table(weight_path,
                         columns=['lat', 'lon_360', 'crop', 'irrigation', 'rainfed_area_ha'],
                         filters=[('crop', '=', 'mai'), ('irrigation', '=', 'noirr')],
                         use_threads=False).to_pandas()
    if not len(area) or not ((area.crop == 'mai') & (area.irrigation == 'noirr')).all():
        raise ValueError('wrong MIRCA crop or regime')
    # The share table emits both irrigation labels for every supported
    # center, including rainfed-zero cells. The preregistered target is
    # positive rainfed hectares only; keep the initial zero count in output.
    if not np.isfinite(area.rainfed_area_ha.to_numpy(dtype=float)).all() or (area.rainfed_area_ha < 0).any():
        raise ValueError('invalid source rainfed area')
    zero_rainfed_rows = int((area.rainfed_area_ha == 0).sum())
    area = area.loc[area.rainfed_area_ha > 0].copy()
    if not len(area):
        raise ValueError('no positive rainfed maize area')
    if area.duplicated(['lat', 'lon_360']).any():
        raise ValueError('duplicate MIRCA maize rainfed center')
    arrays = [area[c].to_numpy(dtype=float) for c in ('lat', 'lon_360', 'rainfed_area_ha')]
    lat, lon, hectares = arrays
    if any(not np.isfinite(x).all() for x in arrays) or np.any(hectares <= 0):
        raise ValueError('invalid mapped rainfed area')
    if not (np.all((-90 <= lat) & (lat <= 90)) and np.all((0 <= lon) & (lon < 360))):
        raise ValueError('invalid MIRCA coordinates')
    with xr.open_dataset(coef_path) as coef, xr.open_dataset(gmst_path) as gmst:
        centers_lat, centers_lon = coef.lat.values, coef.lon.values
        ii = nearest_linear(lat, centers_lat)
        jj = nearest_circular(lon, centers_lon)
        if not (np.all((0 <= ii) & (ii < len(centers_lat))) and np.all((0 <= jj) & (jj < len(centers_lon)))):
            raise ValueError('mapped grid index outside source domain')
        samples = np.linspace(0, len(area) - 1, 100, dtype=int)
        for index in samples:
            expected_lat = int(np.argmin(np.abs(centers_lat - lat[index])))
            expected_lon = int(np.argmin(np.abs(((centers_lon - lon[index] + 180) % 360) - 180)))
            if ii[index] != expected_lat or jj[index] != expected_lon:
                raise ValueError('independent nearest-center audit failed')
        slope, intercept = coef.slope.values[0], coef.intercept.values[0]
        years = gmst.time.dt.year.values.astype(int)
        temperature = gmst.tas.values.astype(float)
        if not np.array_equal(years, np.arange(2015, 2101)):
            raise ValueError('unexpected author GMST annual years')
        touched = np.unique(ii * len(centers_lon) + jj)
        total_area = float(np.sum(hectares, dtype=np.float64))
        area_by_native = np.bincount(ii * len(centers_lon) + jj,
                                     weights=hectares, minlength=len(centers_lat) * len(centers_lon))
        if not np.isclose(total_area, float(area_by_native.sum()), rtol=1e-12, atol=0):
            raise ValueError('rainfed area not conserved by center mapping')
        rows = []
        for y in YEARS:
            T = float(temperature[years == y][0])
            rain = slope * T + intercept
            bad_native = rain.ravel() < 0
            bad_crop_native = bad_native[touched]
            bad_area = float(area_by_native[bad_native].sum())
            if bad_area < 0 or bad_area > total_area:
                raise ValueError('invalid mapped negative-rain area')
            rows.append({'year': y, 'author_gmst_K': T,
                         'negative_native_global_cells': int(bad_native.sum()),
                         'negative_maize_touched_native_cells': int(bad_crop_native.sum()),
                         'rainfed_maize_area_with_negative_center_ha': bad_area,
                         'rainfed_maize_area_with_negative_center_percent': 100 * bad_area / total_area,
                         'min_rain_on_maize_mapped_native_cells_mm_day': float(rain.ravel()[touched].min() * 86400)})
    result = {'status': 'nearest_center_maize_physicality_screen_not_final_exposure',
              'source_model': 'MPI-ESM1-2-HR', 'source_scenario': 'ssp585', 'month': 'dec',
              'mapping': 'MIRCA2000 maize/noirr center to nearest MPI native lat/circular lon',
              'weight_sha256': WEIGHT_SHA256, 'coefficient_sha256': coef_record['member_sha256'],
              'author_gmst_sha256': gmst_record['member_sha256'],
              'mirca_rows': int(len(area)), 'touched_native_cells': int(len(touched)),
              'excluded_zero_rainfed_rows': zero_rainfed_rows,
              'total_rainfed_maize_area_ha': total_area,
              'independent_nearest_audit_rows': int(len(samples)),
              'results': rows, 'yield_damage_scc_estimated': False}
    output_path = args.output.resolve()
    if not output_path.is_relative_to(project / 'data/interim') or output_path.exists():
        parser.error('fresh ignored interim output required')
    serialized = json.dumps(result, indent=2) + '\n'
    if len(serialized.encode()) > 16384:
        raise ValueError('unexpected result output size')
    output_path.write_text(serialized)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
