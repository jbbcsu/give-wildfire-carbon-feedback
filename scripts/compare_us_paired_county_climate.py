"""Matched county climate-source and detrending diagnostics, no yield effects."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from build_us_paired_county_climate import ROOT, PAIR, PROTOCOL, base, checked, identity, sha256

DIRECTORY = 'data/interim/us_paired_county_climate_20260908'
SHAPE = ['stage1_precip_share', 'stage2_precip_share', 'stage3_precip_share', 'precipitation_concentration_hhi']
CORE = ['precip_mm', 'cdd_max_days', 'rx5day_mm'] + [f'stage{s}_tmean_c' for s in (1, 2, 3)]
HEAT = [f'stage{s}_{kind}_{threshold}c' + ('_c_days' if kind == 'tmax_exceedance' else '')
        for s in (1, 2, 3) for threshold in (29, 30) for kind in ('tmax_exceedance', 'tmax_days_gt')]


def paired_summary(candidate, reference, columns):
    for f in (candidate, reference):
        if f.empty or f.duplicated(PAIR).any() or not np.isfinite(f[columns].to_numpy()).all():
            raise ValueError('invalid county climate comparison input')
    a = candidate.set_index(PAIR).sort_index()
    b = reference.set_index(PAIR).sort_index()
    if not a.index.equals(b.index):
        raise ValueError('county climate comparison keys differ')
    delta = (a[columns]-b[columns]).reset_index()
    by_county = delta.groupby('county_geoid')[columns].mean()
    annual = delta.groupby('harvest_year')[columns].mean()
    return dict(rows=len(delta), counties=len(by_county),
                differences={c: dict(equal_county_mean=float(by_county[c].mean()),
                                    county_p10=float(by_county[c].quantile(.1)),
                                    county_p90=float(by_county[c].quantile(.9)),
                                    pooled_county_year_mean=float(delta[c].mean())) for c in columns},
                annual_equal_county_means=[dict(harvest_year=int(y), counties=int((delta.harvest_year == y).sum()),
                                                **{c: float(v) for c, v in row.items()}) for y, row in annual.iterrows()])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('fresh comparison output required')
    receipt_path = ROOT / DIRECTORY / 'receipt.json'
    r = json.loads(receipt_path.read_text())
    if r['status'] != 'us_paired_county_climate_inputs_validated' or r['protocol_sha256'] != sha256(ROOT/PROTOCOL) or r['code_sha256'] != sha256(ROOT/'scripts/build_us_paired_county_climate.py'):
        raise ValueError('county climate construction identity changed')
    paths = {p['scenario']: checked(p) for p in r['products']}
    if set(paths) != {'obsclim', 'counterclim'}:
        raise ValueError('county climate path coverage differs')
    factual, counter = [pd.read_parquet(paths[s]) for s in ('obsclim', 'counterclim')]
    cfg = base.load_config(base.DEFAULT_CONFIG)
    original, source = base.validate_panel(cfg)
    if source != r['input']:
        raise ValueError('NASS/nClimGrid source identity changed')
    heat_receipt_path = ROOT / 'data/provenance/us_daily_heat_expansion_20260907.json'
    heat_receipt = json.loads(heat_receipt_path.read_text())
    heat_path = ROOT / 'data/interim/us_county/nass_direct_practice_daily_heat_1981_2019.parquet'
    if sha256(heat_path) != heat_receipt['output_sha256']:
        raise ValueError('nClimGrid heat identity changed')
    heat = pd.read_parquet(heat_path, columns=PAIR+HEAT)
    original = original.merge(heat, on=PAIR, how='left', validate='many_to_one')
    all_columns = CORE+HEAT+SHAPE+['zero_precipitation_season']
    selected = original.loc[pd.MultiIndex.from_frame(original[PAIR]).isin(pd.MultiIndex.from_frame(factual[PAIR]))]
    reference = selected[PAIR+['season_start', 'season_end', 'season_days']+all_columns].drop_duplicates()
    if len(reference) != 573 or reference.duplicated(PAIR).any():
        raise ValueError('practice-specific weather differs or rows missing')
    for field in ['season_start', 'season_end']:
        reference[field] = pd.to_datetime(reference[field]).dt.normalize()
    for f in (factual, counter):
        pd.testing.assert_frame_equal(f.set_index(PAIR).sort_index()[['season_start', 'season_end', 'season_days']],
                                      reference.set_index(PAIR).sort_index()[['season_start', 'season_end', 'season_days']],
                                      check_dtype=False)
    result = dict(status='us_paired_county_climate_comparison_validated', crop_yield_estimated=False,
        causal_or_scc_result=False, geographically_representative=False, independently_untouched_holdout=False,
        climate_receipt=identity(receipt_path), nclimgrid_source=source,
        heat_receipt=identity(heat_receipt_path), code_sha256=sha256(Path(__file__)), protocol_sha256=sha256(ROOT/PROTOCOL), comparisons=[])
    for crop in ('corn_grain', 'soybeans'):
        f, c, n = [t.loc[t.outcome_crop == crop].copy() for t in (factual, counter, reference)]
        zeros = pd.concat([t[PAIR+['zero_precipitation_season']] for t in (f, c, n)]).groupby(PAIR).zero_precipitation_season.max()
        shape_keys = zeros.index[zeros.eq(0)]
        shape_frames = [t.loc[pd.MultiIndex.from_frame(t[PAIR]).isin(shape_keys)] for t in (f, c, n)]
        entry = dict(crop=crop, shape_excluded_county_years=int(zeros.gt(0).sum()), contrasts=[])
        for name, a, b, sa, sb in [('factual_minus_counterclim', f, c, shape_frames[0], shape_frames[1]),
                                    ('gswp_factual_minus_nclimgrid', f, n, shape_frames[0], shape_frames[2])]:
            entry['contrasts'].append(dict(name=name, core=paired_summary(a, b, CORE+HEAT),
                                          shape=paired_summary(sa, sb, SHAPE) if len(sa) else None))
        result['comparisons'].append(entry)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print([(e['crop'], [(c['name'], {k: c['core']['differences'][k]['equal_county_mean'] for k in ['precip_mm', 'cdd_max_days', 'rx5day_mm', 'stage2_tmean_c', 'stage2_tmax_exceedance_29c_c_days']}) for c in e['contrasts']]) for e in result['comparisons']])


if __name__ == '__main__':
    main()
