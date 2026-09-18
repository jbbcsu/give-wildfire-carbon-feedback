#!/usr/bin/env python3
"""Screen author PEEPS monthly rainfall levels on rainfed-maize centers.

This is a calendar-year climate-input physicality diagnostic, not a crop
exposure, yield response, welfare, or SCC calculation.
"""
import argparse
import calendar
from decimal import Decimal, getcontext
import json
from pathlib import Path
import shutil

import numpy as np
import pyarrow.parquet as pq
import xarray as xr

from extract_peeps_full_month_mpi import MONTHS, MODEL, SCENARIO, OUTER_MD5
from probe_peeps_author_december_prediction import YEARS, checked_source
from probe_peeps_december_crop_support import (
    WEIGHT_SHA256, file_hash, nearest_circular, nearest_linear,
)


def summarize_common_support(rain_2015, rain_2100, hectares):
    """Annual amount and month-share TV on identical nonnegative support."""
    if rain_2015.shape != rain_2100.shape or rain_2015.shape[0] != 12:
        raise ValueError('expect matching 12-month arrays')
    if rain_2015.shape[1] != len(hectares) or not np.all(hectares > 0):
        raise ValueError('invalid area geometry')
    if not (np.isfinite(rain_2015).all() and np.isfinite(rain_2100).all()):
        raise ValueError('nonfinite rainfall')
    total_a = rain_2015.sum(axis=0)
    total_b = rain_2100.sum(axis=0)
    common = ((rain_2015 >= 0).all(axis=0) & (rain_2100 >= 0).all(axis=0)
              & (total_a > 0) & (total_b > 0))
    common_area = float(hectares[common].sum())
    result = {'common_valid_centers': int(common.sum()),
              'common_valid_area_ha': common_area,
              'common_valid_area_percent': 100 * common_area / float(hectares.sum())}
    if not np.any(common):
        result.update(mean_annual_2015_mm=None, mean_annual_2100_mm=None,
                      mean_annual_change_mm=None, mean_annual_change_percent=None,
                      mean_cell_month_share_tv=None)
        return result
    weights = hectares[common]
    mean_a = float(np.average(total_a[common], weights=weights))
    mean_b = float(np.average(total_b[common], weights=weights))
    shares_a = rain_2015[:, common] / total_a[common][None, :]
    shares_b = rain_2100[:, common] / total_b[common][None, :]
    tv = 0.5 * np.abs(shares_b - shares_a).sum(axis=0)
    result.update(mean_annual_2015_mm=mean_a,
                  mean_annual_2100_mm=mean_b,
                  mean_annual_change_mm=mean_b - mean_a,
                  mean_annual_change_percent=100 * (mean_b - mean_a) / mean_a,
                  mean_cell_month_share_tv=float(np.average(tv, weights=weights)))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('monthly_receipt', type=Path)
    parser.add_argument('gmst_receipt', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    if shutil.disk_usage(project).free < 130 * 2**30:
        raise RuntimeError('free disk below reserve')
    receipt_path = args.monthly_receipt.resolve()
    if not receipt_path.is_relative_to(project / 'data/interim'):
        parser.error('monthly receipt must be ignored interim')
    source = json.loads(receipt_path.read_text())
    if (source['status'] != 'whole_author_archive_md5_verified_selected_members_acquired'
            or source['outer_archive_md5'] != OUTER_MD5
            or source['selected_months'] != list(MONTHS)
            or source['model'] != MODEL or source['scenario'] != SCENARIO
            or len(source['selected_members']) != 12):
        raise ValueError('unexpected published monthly source receipt')
    gmst_path, gmst_record = checked_source(project, args.gmst_receipt)
    if gmst_record['model'] != MODEL or gmst_record['scenario'] != SCENARIO:
        raise ValueError('published coefficient and GMST source mismatch')
    with xr.open_dataset(gmst_path) as ds:
        years = ds.time.dt.year.values.astype(int)
        tas = ds.tas.values.astype(float)
    if not np.array_equal(years, np.arange(2015, 2101)) or not np.isfinite(tas).all():
        raise ValueError('invalid author absolute-GMST series')
    temperatures = {year: float(tas[years == year][0]) for year in YEARS}
    if not all(250 < value < 330 for value in temperatures.values()):
        raise ValueError('implausible absolute GMST')

    weight_path = project / 'data/interim/mirca_os_v2/irrigation_shares_2000.parquet'
    if file_hash(weight_path) != WEIGHT_SHA256:
        raise ValueError('MIRCA rainfed-area source changed')
    area = pq.read_table(weight_path,
                         columns=['lat', 'lon_360', 'crop', 'irrigation', 'rainfed_area_ha'],
                         filters=[('crop', '=', 'mai'), ('irrigation', '=', 'noirr')],
                         use_threads=False).to_pandas()
    if not len(area) or not ((area.crop == 'mai') & (area.irrigation == 'noirr')).all():
        raise ValueError('wrong MIRCA crop/regime')
    if not np.isfinite(area.rainfed_area_ha.to_numpy(dtype=float)).all() or (area.rainfed_area_ha < 0).any():
        raise ValueError('invalid rainfed hectares')
    zero_rows = int((area.rainfed_area_ha == 0).sum())
    area = area.loc[area.rainfed_area_ha > 0].copy()
    if not len(area) or area.duplicated(['lat', 'lon_360']).any():
        raise ValueError('empty or duplicated positive maize centers')
    lat, lon, hectares = (area[name].to_numpy(dtype=float)
                           for name in ('lat', 'lon_360', 'rainfed_area_ha'))
    if not (np.isfinite(lat).all() and np.isfinite(lon).all()
            and np.all((-90 <= lat) & (lat <= 90))
            and np.all((0 <= lon) & (lon < 360))):
        raise ValueError('invalid crop coordinates')

    rain = {year: np.empty((12, len(hectares)), dtype=np.float64) for year in YEARS}
    grid_lat = grid_lon = ii = jj = None
    sentinels = []
    getcontext().prec = 50
    for month_index, (month, item) in enumerate(zip(MONTHS, source['selected_members'], strict=True), 1):
        expected = f'{MODEL}_{SCENARIO}_pr_monthly_patterns_{month}.nc'
        path = receipt_path.parent / expected
        if (item['name'] != expected or not path.is_file() or
                path.stat().st_size != item['bytes'] or file_hash(path) != item['sha256']):
            raise ValueError(f'published monthly coefficient changed: {month}')
        with xr.open_dataset(path) as ds:
            attrs = {'source_id': MODEL, 'experiment_id': SCENARIO,
                     'variable_id': 'pr', 'variable_units': 'kg m-2 s-1',
                     'grid_label': 'gn', 'variant_label': 'ensemble_avg'}
            if any(str(ds.attrs.get(key, '')) != value for key, value in attrs.items()):
                raise ValueError(f'wrong coefficient metadata: {month}')
            if dict(ds.sizes) != {'param': 1, 'lat': 192, 'lon': 384}:
                raise ValueError(f'wrong coefficient dimensions: {month}')
            this_lat, this_lon = ds.lat.values, ds.lon.values
            if grid_lat is None:
                grid_lat, grid_lon = this_lat.copy(), this_lon.copy()
                ii, jj = nearest_linear(lat, grid_lat), nearest_circular(lon, grid_lon)
                samples = np.linspace(0, len(hectares) - 1, 100, dtype=int)
                for k in samples:
                    expected_i = int(np.argmin(np.abs(grid_lat - lat[k])))
                    expected_j = int(np.argmin(np.abs(((grid_lon - lon[k] + 180) % 360) - 180)))
                    if ii[k] != expected_i or jj[k] != expected_j:
                        raise ValueError('independent nearest-center audit failed')
                native_area = np.bincount(ii * len(grid_lon) + jj, weights=hectares,
                                          minlength=len(grid_lat) * len(grid_lon))
                if not np.isclose(native_area.sum(), hectares.sum(), rtol=1e-12, atol=0):
                    raise ValueError('area not conserved')
            elif not (np.array_equal(this_lat, grid_lat) and np.array_equal(this_lon, grid_lon)):
                raise ValueError('monthly grids differ')
            slope, intercept = ds.slope.values[0], ds.intercept.values[0]
            if not (np.isfinite(slope).all() and np.isfinite(intercept).all()):
                raise ValueError('nonfinite coefficients')
            for year in YEARS:
                seconds = 86400 * calendar.monthrange(year, month_index)[1]
                native_flux = slope * temperatures[year] + intercept
                if not np.isfinite(native_flux).all():
                    raise ValueError('nonfinite published prediction')
                rain[year][month_index - 1] = native_flux[ii, jj] * seconds
                if year in (2015, 2100):
                    k = int(samples[(month_index - 1) % len(samples)])
                    decimal_mm = ((Decimal(str(float(slope[ii[k], jj[k]])))
                                  * Decimal(str(temperatures[year]))
                                  + Decimal(str(float(intercept[ii[k], jj[k]]))))
                                  * Decimal(seconds))
                    actual_mm = float(native_flux[ii[k], jj[k]] * seconds)
                    if abs(float(decimal_mm) - actual_mm) > 1e-9:
                        raise ValueError('independent Decimal sentinel disagrees')
                    sentinels.append({'year': year, 'month': month,
                                      'mapped_center_row': k, 'predicted_mm': float(decimal_mm)})

    total_area = float(hectares.sum())
    result_years = []
    for year in YEARS:
        monthly = []
        for m, month in enumerate(MONTHS):
            bad = rain[year][m] < 0
            negative_area = float(hectares[bad].sum())
            monthly.append({'month': month, 'negative_centers': int(bad.sum()),
                            'negative_area_ha': negative_area,
                            'negative_area_percent': 100 * negative_area / total_area,
                            'min_mapped_monthly_mm': float(rain[year][m].min())})
        any_bad = (rain[year] < 0).any(axis=0)
        any_bad_area = float(hectares[any_bad].sum())
        result_years.append({'year': year, 'author_absolute_gmst_K': temperatures[year],
                             'any_negative_month_area_ha': any_bad_area,
                             'any_negative_month_area_percent': 100 * any_bad_area / total_area,
                             'months': monthly})
    result = {'status': 'author_published_monthly_crop_center_physicality_not_validation_or_scc',
              'model': MODEL, 'scenario': SCENARIO, 'coefficient_archive_md5': OUTER_MD5,
              'author_gmst_sha256': gmst_record['member_sha256'],
              'mirca_sha256': WEIGHT_SHA256,
              'mapping': 'MIRCA2000 rainfed maize center to nearest native MPI grid center',
              'exposure': 'calendar-year monthly proxy, not crop year or daily sequence',
              'positive_area_rows': len(hectares), 'excluded_zero_area_rows': zero_rows,
              'mapped_native_cells': int(np.count_nonzero(native_area)),
              'total_rainfed_maize_area_ha': total_area,
              'independent_mapping_rows': len(samples),
              'decimal_sentinels': sentinels, 'year_screens': result_years,
              'common_2015_2100': summarize_common_support(rain[2015], rain[2100], hectares),
              'yield_damage_scc_estimated': False}
    output = args.output.resolve()
    if not output.is_relative_to(project / 'data/interim') or output.exists():
        parser.error('fresh ignored interim output required')
    payload = json.dumps(result, indent=2) + '\n'
    if len(payload.encode()) > 128 * 1024:
        raise ValueError('unexpected output size')
    output.write_text(payload)
    print(json.dumps({'status': result['status'],
                      'year_screens': [{k: v for k, v in x.items() if k != 'months'}
                                       for x in result_years],
                      'common_2015_2100': result['common_2015_2100']}))


if __name__ == '__main__':
    main()
