#!/usr/bin/env python3
"""Independently rebuild the published monthly maize-center diagnostics."""
import argparse
import calendar
import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import xarray as xr


MONTHS = ('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec')
YEARS = (2015, 2030, 2050, 2100)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def close(a, b, label):
    if not np.isclose(a, b, rtol=2e-11, atol=1e-8):
        raise ValueError(f'independent audit differs at {label}: {a} vs {b}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_receipt', type=Path)
    parser.add_argument('gmst_receipt', type=Path)
    parser.add_argument('screen', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    paths = [path.resolve() for path in (args.source_receipt, args.gmst_receipt, args.screen, args.output)]
    if any(not path.is_relative_to(root / 'data/interim') for path in paths) or paths[-1].exists():
        parser.error('all input/output paths must be ignored interim and output fresh')
    source, gmst_meta, screen = [json.loads(path.read_text()) for path in paths[:3]]
    if (source['selected_months'] != list(MONTHS) or source['model'] != 'MPI-ESM1-2-HR'
            or source['scenario'] != 'ssp585' or len(source['selected_members']) != 12
            or screen['coefficient_archive_md5'] != source['outer_archive_md5']):
        raise ValueError('wrong input source')
    gmst_path = root / gmst_meta['output_relative_to_project']
    if digest(gmst_path) != gmst_meta['member_sha256']:
        raise ValueError('GMST source changed')
    with xr.open_dataset(gmst_path) as dataset:
        years = dataset.time.dt.year.values.astype(int)
        gmst = dataset.tas.values.astype(float)
    if not np.array_equal(years, np.arange(2015, 2101)):
        raise ValueError('GMST years differ')
    temperature = {year: gmst[np.where(years == year)[0][0]] for year in YEARS}
    area = pq.read_table(root / 'data/interim/mirca_os_v2/irrigation_shares_2000.parquet',
                         columns=['lat', 'lon_360', 'crop', 'irrigation', 'rainfed_area_ha'],
                         filters=[('crop', '=', 'mai'), ('irrigation', '=', 'noirr')],
                         use_threads=False).to_pandas()
    area = area.loc[area.rainfed_area_ha > 0]
    lat = area.lat.to_numpy(dtype=float)
    lon = area.lon_360.to_numpy(dtype=float)
    weight = area.rainfed_area_ha.to_numpy(dtype=float)
    close(weight.sum(), screen['total_rainfed_maize_area_ha'], 'area')
    rain = {year: np.empty((12, len(weight))) for year in YEARS}
    ii = jj = None
    for m, member in enumerate(source['selected_members']):
        path = paths[0].parent / member['name']
        if digest(path) != member['sha256']:
            raise ValueError(f'member changed: {m}')
        with xr.open_dataset(path) as dataset:
            if ii is None:
                native_lat = dataset.lat.values
                native_lon = dataset.lon.values
                ii = np.empty(len(weight), dtype=int)
                jj = np.empty(len(weight), dtype=int)
                for start in range(0, len(weight), 512):
                    stop = min(start + 512, len(weight))
                    ii[start:stop] = np.abs(lat[start:stop, None] - native_lat).argmin(axis=1)
                    distance = np.abs(((lon[start:stop, None] - native_lon + 180) % 360) - 180)
                    jj[start:stop] = distance.argmin(axis=1)
            beta = dataset.slope.values[0, ii, jj]
            alpha = dataset.intercept.values[0, ii, jj]
            for year in YEARS:
                rain[year][m] = (alpha + beta * temperature[year]) * 86400 * calendar.monthrange(year, m + 1)[1]
    for row in screen['year_screens']:
        year = row['year']
        bad = rain[year] < 0
        close(weight[bad.any(axis=0)].sum(), row['any_negative_month_area_ha'], f'{year} any negative area')
        for m, month_row in enumerate(row['months']):
            close(weight[bad[m]].sum(), month_row['negative_area_ha'], f'{year} {m} negative area')
            close(rain[year][m].min(), month_row['min_mapped_monthly_mm'], f'{year} {m} minimum')
    a, b = rain[2015], rain[2100]
    total_a, total_b = a.sum(axis=0), b.sum(axis=0)
    common = ((a >= 0).all(axis=0) & (b >= 0).all(axis=0) & (total_a > 0) & (total_b > 0))
    reported = screen['common_2015_2100']
    if common.sum() != reported['common_valid_centers']:
        raise ValueError('common center count differs')
    close(weight[common].sum(), reported['common_valid_area_ha'], 'common valid area')
    mean_a = np.average(total_a[common], weights=weight[common])
    mean_b = np.average(total_b[common], weights=weight[common])
    close(mean_a, reported['mean_annual_2015_mm'], 'annual 2015')
    close(mean_b, reported['mean_annual_2100_mm'], 'annual 2100')
    tv = 0.5 * np.abs(a[:, common] / total_a[common] - b[:, common] / total_b[common]).sum(axis=0)
    close(np.average(tv, weights=weight[common]), reported['mean_cell_month_share_tv'], 'month-share TV')
    result = {'status': 'independent_source_redecode_and_full_center_rebuild_passed',
              'all_48_month_year_negative_area_checks': True,
              'all_48_month_year_minimum_checks': True,
              'four_any_month_area_checks': True,
              'common_area_amount_share_checks': True,
              'yield_damage_scc_estimated': False}
    paths[-1].write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
