"""Registered source-matched historical associations, never climate/SCC inputs."""
import argparse
import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd

from build_us_regional_county_climate import ROOT, PAIR, base, checked, identity, sha256
from compare_us_paired_county_climate import HEAT
from estimate_daily_heat_rainfall_associations import qr_clustered_ols

PROTOCOL = 'US_SOURCE_MATCHED_RESPONSE_PROTOCOL_20260908.md'
DIRECTORY = ROOT/'data/interim/us_regional_county_climate_20260908'
KEY = PAIR + ['irrigation_practice']
WEATHER = ['precip_mm', 'stage1_precip_share', 'stage2_precip_share'] + [f'stage{s}_tmean_c' for s in (1, 2, 3)] + HEAT
PINNED = {
    'scripts/build_us_regional_county_climate.py': 'f2d9bd21dd3c0cee265f97ee3a7af4c6efb3931d4cea9cc5baaeb6db250e80b7',
    'scripts/compare_us_regional_county_climate.py': 'dd78be99cfa36e528f68ad1ee563011e6dcea68ab80576242221cd2180539262',
    'data/interim/us_county/nass_direct_practice_nclimgrid_1981_2019.parquet': '205a94ae92c12810026c9c5d0ac0fa3760e46ebc39669e528ba20a125a0c46d7',
    'data/interim/us_county/nass_direct_practice_daily_heat_1981_2019.parquet': '380735986e48291c092b83b588bf0a96b335bccf632bff033988795338ffe4df',
}


def write_new(path, value):
    path = path.resolve()
    path.relative_to(ROOT/'data/interim')
    partial = path.with_suffix(path.suffix+'.partial')
    if path.exists() or partial.exists():
        raise ValueError('fresh output required')
    path.parent.mkdir(parents=True, exist_ok=True)
    with partial.open('x') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')
    partial.replace(path)


def align_sources(frame, factual):
    if factual.empty or factual.duplicated(PAIR).any() or set(factual.scenario) != {'obsclim'}:
        raise ValueError('unique factual training climate required')
    if frame.duplicated(KEY).any():
        raise ValueError('duplicate outcome key')
    original = frame.loc[pd.MultiIndex.from_frame(frame[PAIR]).isin(pd.MultiIndex.from_frame(factual[PAIR]))].copy()
    original = original.sort_values(KEY).reset_index(drop=True)
    if original.empty or len(original[PAIR].drop_duplicates()) != len(factual):
        raise ValueError('factual/outcome support differs')
    practices = original.groupby(PAIR).irrigation_practice.agg(lambda x: set(x))
    if not practices.map(lambda x: x == {'irrigated', 'non_irrigated'}).all():
        raise ValueError('paired practice support changed')
    dates = ['season_start', 'season_end', 'season_days']
    observed = original[PAIR+dates+WEATHER].drop_duplicates()
    if observed.duplicated(PAIR).any():
        raise ValueError('weather or dates differ across practices')
    a, b = [x.set_index(PAIR).sort_index()[dates].copy() for x in (observed, factual)]
    for col in dates[:2]:
        a[col], b[col] = pd.to_datetime(a[col]).dt.normalize(), pd.to_datetime(b[col]).dt.normalize()
    pd.testing.assert_frame_equal(a, b, check_dtype=False)
    replacement = original.drop(columns=WEATHER).merge(factual[PAIR+WEATHER], on=PAIR, validate='many_to_one')
    replacement = replacement.sort_values(KEY).reset_index(drop=True)
    pd.testing.assert_frame_equal(original[KEY+['yield_bu_acre', 'log_yield']], replacement[KEY+['yield_bu_acre', 'log_yield']])
    for item in (original, replacement):
        if not np.isfinite(item[WEATHER].to_numpy(dtype=float)).all() or item.precip_mm.lt(0).any():
            raise ValueError('nonfinite or negative weather')
        shares = item[['stage1_precip_share', 'stage2_precip_share']]
        if shares.lt(0).any().any() or shares.sum(axis=1).gt(1+1e-8).any():
            raise ValueError('invalid precipitation shares')
    matched_positive = original.precip_mm.gt(0).to_numpy() & replacement.precip_mm.gt(0).to_numpy()
    return {'nclimgrid': original, 'gswp_obsclim': replacement}, matched_positive


def load_inputs():
    for path, digest in PINNED.items():
        if sha256(ROOT/path) != digest:
            raise ValueError('pinned input/code changed: '+path)
    rp, cp = DIRECTORY/'receipt.json', DIRECTORY/'comparison.json'
    receipt, comparison = [json.loads(p.read_text()) for p in (rp, cp)]
    if receipt['status'] != 'us_regional_county_climate_inputs_validated' or comparison['status'] != 'us_regional_county_climate_comparison_validated':
        raise ValueError('completed regional inputs/comparison required')
    if receipt['code_sha256'] != PINNED['scripts/build_us_regional_county_climate.py'] or comparison['code_sha256'] != PINNED['scripts/compare_us_regional_county_climate.py']:
        raise ValueError('construction/comparison code receipt differs')
    if comparison['climate_receipt'] != identity(rp):
        raise ValueError('comparison does not bind climate receipt')
    if receipt['protocol_sha256'] != sha256(ROOT/'US_REGIONAL_COUNTY_FEATURE_PROTOCOL_20260908.md'):
        raise ValueError('regional protocol changed')
    if receipt['feature_helper_sha256'] != sha256(ROOT/'scripts/build_us_paired_county_climate.py'):
        raise ValueError('feature implementation changed')
    products = {p['scenario']: p for p in receipt['products']}
    if set(products) != {'obsclim', 'counterclim'} or len(receipt['products']) != 2:
        raise ValueError('paired products differ')
    for product in products.values():
        checked(product)
    cfg = base.load_config(base.DEFAULT_CONFIG)
    original, source = base.validate_panel(cfg)
    if source != receipt['input']:
        raise ValueError('outcome source differs from climate construction')
    hp = ROOT/'data/provenance/us_daily_heat_expansion_20260907.json'
    heat_path = ROOT/'data/interim/us_county/nass_direct_practice_daily_heat_1981_2019.parquet'
    if json.loads(hp.read_text())['output_sha256'] != sha256(heat_path):
        raise ValueError('heat receipt changed')
    original = original.loc[original.harvest_year.between(1982, 2010)]
    original = original.merge(pd.read_parquet(heat_path, columns=PAIR+HEAT), on=PAIR, validate='many_to_one', how='left')
    factual = pd.read_parquet(checked(products['obsclim']))
    frames, mask = align_sources(original, factual)
    paths = [ROOT/p for p in PINNED] + [rp, cp, hp, ROOT/PROTOCOL, Path(__file__), Path(base.__file__),
        base.ESTIMATION_PRIMITIVES, base.DEFAULT_CONFIG,
        ROOT/'us_county_validation/scripts/estimate_daily_heat_rainfall_associations.py',
        ROOT/'scripts/build_us_paired_county_climate.py',
        ROOT/'scripts/compare_us_paired_county_climate.py',
        ROOT/'US_REGIONAL_COUNTY_FEATURE_PROTOCOL_20260908.md']
    paths += [checked(p) for p in products.values()]
    binding = dict(schema='us_source_matched_response_inputs_v1', sources=[identity(p) for p in paths],
        historical_association_only=True, causal_or_scc_result=False,
        rows=len(mask), matched_positive_rows=int(mask.sum()), excluded_zero_rain_rows=int((~mask).sum()),
        support=[dict(crop=c, practice=p, rows=len(g), counties=int(g.county_geoid.nunique()))
                 for (c, p), g in frames['nclimgrid'].loc[mask].groupby(['outcome_crop', 'irrigation_practice'])])
    return frames, mask, binding, cfg


def fit(frame, crop, practice, form, threshold, cfg):
    subset = frame.loc[frame.outcome_crop.eq(crop)&frame.irrigation_practice.eq(practice)].copy()
    if len(subset) < 500 or subset.county_geoid.nunique() < 25:
        raise ValueError('unchanged 500-row/25-county sample gate failed')
    current = copy.deepcopy(cfg)
    current['models']['heat_controls'] = [f'stage{s}_tmean_c' for s in (1, 2, 3)] + [c for c in HEAT if f'_{threshold}c' in c]
    x, names = base.raw_design(subset, form, current)
    groups = [pd.factorize(subset.county_geoid, sort=True)[0],
              pd.factorize(subset.state.astype(str)+'_'+subset.harvest_year.astype(str), sort=True)[0]]
    residual, iterations, change = base.alternating_residualize(np.column_stack([subset.log_yield, x]), groups, 1e-10, 1000)
    y, x = residual[:, 0], residual[:, 1:]
    if np.any(x.std(axis=0) <= 1e-10):
        raise ValueError('within predictor scale gate failed')
    output = qr_clustered_ols(y, x, subset.county_geoid.to_numpy())
    scale = x.std(axis=0)
    condition = float(np.linalg.cond(np.linalg.qr(x/scale, mode='reduced')[1]))
    return dict(rows=len(subset), counties=int(subset.county_geoid.nunique()), states=int(subset.state.nunique()),
        demeaning_iterations=iterations, demeaning_final_change=change, scaled_qr_condition_number=condition,
        terms=names, beta=output['beta'].tolist(), covariance_county_cluster=output['covariance_beta_cluster_county'].tolist(),
        standard_error_county_cluster=output['standard_error_cluster_county'].tolist(),
        in_sample_residual_rmse=output['residual_rmse'], within_r_squared=output['within_r_squared'],
        uncertainty_convention='G/(G-1)*(n-1)/(n-k_weather); absorbed_FE_rank_not_in_correction; no_cross_county_dependence_adjustment')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--bind-inputs', action='store_true')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    frames, mask, binding, cfg = load_inputs()
    if args.bind_inputs:
        if args.out is not None:
            raise ValueError('input binding must precede fitting in a separate invocation')
        write_new(args.manifest, binding)
        print('Bound real inputs; no fits:', binding['support'])
        return
    if args.out is None or args.out.exists():
        raise ValueError('fresh result output required')
    if json.loads(args.manifest.read_text()) != binding:
        raise ValueError('input/code binding changed after registration')
    results = []
    for weather_source, frame in frames.items():
        for crop in ('corn_grain', 'soybeans'):
            primary = 29 if crop == 'corn_grain' else 30
            for practice in ('non_irrigated', 'irrigated'):
                jobs = [('matched_positive', mask, f, t) for t in (primary, 59-primary) for f in ('quantity', 'quantity_timing')]
                if (~mask & frame.outcome_crop.eq(crop).to_numpy() & frame.irrigation_practice.eq(practice).to_numpy()).any():
                    jobs.append(('all_finite_quantity_sensitivity', np.ones(len(mask), bool), 'quantity', primary))
                for cohort, selected, form, threshold in jobs:
                    record = dict(weather_source=weather_source, crop=crop, practice=practice, form=form,
                        threshold_c=threshold, primary_threshold=threshold == primary, cohort=cohort)
                    try:
                        record.update(status='estimated', result=fit(frame.loc[selected], crop, practice, form, threshold, cfg))
                    except (ValueError, np.linalg.LinAlgError) as error:
                        record.update(status='failed_preserved', reason=str(error))
                    results.append(record)
    write_new(args.out, dict(schema='us_source_matched_response_v1', role='exploratory_historical_source_sensitivity',
        causal_or_scc_result=False, coefficient_export_to_production_allowed=False, new_untouched_holdout=False,
        counterclim_yield_estimated=False, input_manifest=identity(args.manifest.resolve()), estimates=results))
    print('Historical fits:', len(results), '; preserved failures:', sum(r['status'] != 'estimated' for r in results))


if __name__ == '__main__':
    main()
