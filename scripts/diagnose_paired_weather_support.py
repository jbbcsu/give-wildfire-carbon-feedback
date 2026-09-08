"""Descriptive empirical weather support; no response fitting or causal claims."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from allocate_outcome_exposures import KEYS
from allocate_irrigation_heat_basis import heat_basis_feature_names
from build_future_weighted_precipitation import ZERO
from compare_factual_counterclim import aligned_pair, load_product
from compare_historical_climate_sources import GRID, observed
from summarize_contiguous_climate_contrasts import ROOT, sha256

PROTOCOL = 'PAIRED_WEATHER_SUPPORT_PROTOCOL_20260908.md'
PRIOR = 'data/interim/counterclim_soy_joint_20260908/paired_comparison.json'
FLAGS = ['outside_any_marginal', 'beyond_joint_distance', 'constant_violation',
         'joint_or_constant', 'inside_marginals_beyond_joint', 'factual_loo_beyond']


def cell_support(factual, counter):
    """Arrays must already have matching years and the same feature order."""
    a = np.asarray(factual, dtype=float)
    b = np.asarray(counter, dtype=float)
    if a.ndim != 2 or a.shape != b.shape or a.shape[0] < 3 or a.shape[1] < 1:
        raise ValueError('same nonempty feature dimensions and at least three years required')
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('nonfinite support input')
    scale = a.std(axis=0, ddof=1)
    varying = scale > 1e-12
    marginal = (b < a.min(axis=0) - 1e-10) | (b > a.max(axis=0) + 1e-10)
    constant = (np.abs(b[:, ~varying] - a[0, ~varying]) > 1e-10).any(axis=1)
    if varying.any():
        aa = (a[:, varying] - a[:, varying].mean(axis=0)) / scale[varying]
        bb = (b[:, varying] - a[:, varying].mean(axis=0)) / scale[varying]
        reference = np.sqrt(np.mean((aa[:, None] - aa[None, :]) ** 2, axis=2))
        np.fill_diagonal(reference, np.inf)
        loo = reference.min(axis=1)
        nearest = np.sqrt(np.mean((bb[:, None] - aa[None, :]) ** 2, axis=2)).min(axis=1)
    else:
        loo = np.zeros(len(a))
        nearest = np.zeros(len(b))
    threshold = float(np.quantile(loo, .95, method='linear'))
    beyond = nearest > threshold + 1e-10
    outside = marginal.any(axis=1)
    return dict(rows=len(a), varying_dimensions=int(varying.sum()), threshold=threshold,
                nearest=nearest, marginal=marginal, outside_any_marginal=outside,
                beyond_joint_distance=beyond, constant_violation=constant,
                joint_or_constant=beyond | constant,
                inside_marginals_beyond_joint=(~outside) & beyond,
                factual_loo_beyond=loo > threshold + 1e-10)


def summarize_support(factual, counter, columns):
    a, b = aligned_pair(factual, counter, columns)
    counts = dict.fromkeys(FLAGS, 0)
    fractions = {k: [] for k in FLAGS}
    feature_counts = np.zeros(len(columns), dtype=int)
    dimensions, thresholds, distances = [], [], []
    cell_rows = []
    for key, cell in a.groupby(level=GRID, sort=True):
        result = cell_support(cell[columns], b.loc[cell.index, columns])
        row = dict(zip(GRID, key))
        row.update(rows=result['rows'], varying_dimensions=result['varying_dimensions'],
                   distance_threshold=result['threshold'])
        for name in FLAGS:
            count = int(result[name].sum())
            counts[name] += count
            fractions[name].append(count / result['rows'])
            row[name + '_rows'] = count
        feature_counts += result['marginal'].sum(axis=0)
        dimensions.append(result['varying_dimensions'])
        thresholds.append(result['threshold'])
        distances.extend(result['nearest'].tolist())
        cell_rows.append(row)
    return dict(features=columns, rows=len(a), cells=len(cell_rows),
                flags={k: dict(rows=counts[k], pooled_fraction=counts[k] / len(a),
                               equal_cell_fraction=float(np.mean(fractions[k]))) for k in FLAGS},
                outside_marginal_by_feature={c: dict(rows=int(n), fraction=float(n / len(a)))
                                             for c, n in zip(columns, feature_counts)},
                varying_dimensions_min=int(min(dimensions)), varying_dimensions_max=int(max(dimensions)),
                all_constant_cells=int(sum(d == 0 for d in dimensions)),
                zero_distance_threshold_cells=int(sum(t == 0 for t in thresholds)),
                distance_quantiles={str(q): float(np.quantile(distances, q)) for q in (.1, .5, .9, .95)},
                cell_diagnostics=cell_rows)


def verify_prior(prior, crop, sources, observed_sources):
    if prior.get('status') != 'paired_climate_diagnostic_validated':
        raise ValueError('prior paired diagnostic not validated')
    entries = [e for e in prior['comparisons'] if e['crop'] == crop]
    if len(entries) != 1 or entries[0]['sources'] != sources or entries[0]['retained_observed_sources'] != observed_sources:
        raise ValueError('prior paired source identities changed')


def select_observed_keys(factual, counter, obs):
    if obs.empty or obs.duplicated(KEYS).any():
        raise ValueError('invalid observed cohort keys')
    index = pd.MultiIndex.from_frame(obs[KEYS])
    selected = []
    for frame in (factual, counter):
        if frame.duplicated(KEYS).any():
            raise ValueError('duplicate climate keys')
        indexed = frame.set_index(KEYS)
        if not index.isin(indexed.index).all():
            raise ValueError('observed cohort missing from climate product')
        selected.append(indexed.loc[index].reset_index())
    return selected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('fresh output required')
    prior = json.loads((ROOT / PRIOR).read_text())
    result = dict(status='paired_weather_support_diagnostic_validated',
                  role='descriptive_empirical_weather_support_not_causal_overlap_certificate',
                  crop_yield_estimated=False, causal_or_scc_result=False,
                  protocol_sha256=sha256(ROOT / PROTOCOL), code_sha256=sha256(Path(__file__)),
                  prior=dict(path=PRIOR, sha256=sha256(ROOT / PRIOR)), crops=[])
    for crop, label, threshold, expected in [('mai', 'maize', 29, (8465, 292)),
                                            ('soy', 'soy', 30, (4321, 149))]:
        factual, fr, fs = load_product(crop, 'obsclim')
        counter, cr, cs = load_product(crop, 'counterclim')
        obs, os = observed(crop, label, threshold)
        verify_prior(prior, crop, [fs, cs], os)
        if fr['calendars'] != cr['calendars'] or fr['weight_sha256'] != cr['weight_sha256']:
            raise ValueError('paired calendar or irrigation weights changed')
        if (len(obs), len(obs[GRID].drop_duplicates())) != expected:
            raise ValueError('observed cohort counts changed')
        f, c = select_observed_keys(factual, counter, obs)
        zeros = pd.concat([factual[GRID + [ZERO]], counter[GRID + [ZERO]]]).groupby(GRID)[ZERO].max()
        valid = zeros.index[zeros.eq(0)]
        shape_mask = pd.MultiIndex.from_frame(f[GRID]).isin(valid)
        quantity = ['log1p_precip_mm']
        joint = quantity + [f'stage{s}_tmean_c' for s in (1, 2, 3)] + [
            col for col in heat_basis_feature_names([threshold], 3) if col.endswith('_degree_days')]
        distribution = joint + ['cdd_max_days', 'rx5day_mm', 'stage1_precip_share',
                                'stage2_precip_share', 'precipitation_concentration_hhi']
        if tuple(map(len, [quantity, joint, distribution])) != (1, 7, 12):
            raise ValueError('feature contract changed')
        entry = dict(crop=crop, climate_receipts=[fs, cs], observed_sources=os,
                     cohort_rows=len(f), cohort_cells=expected[1], families={})
        for name, cols, mask in [('quantity', quantity, np.ones(len(f), dtype=bool)),
                                 ('joint_quantity_heat', joint, np.ones(len(f), dtype=bool)),
                                 ('joint_quantity_heat_distribution', distribution, shape_mask)]:
            entry['families'][name] = summarize_support(f.loc[mask], c.loc[mask], cols)
        entry['shape_excluded_cells'] = expected[1] - entry['families']['joint_quantity_heat_distribution']['cells']
        result['crops'].append(entry)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print([(e['crop'], {k: v['flags']['joint_or_constant']['pooled_fraction']
                       for k, v in e['families'].items()}) for e in result['crops']])


if __name__ == '__main__':
    main()
