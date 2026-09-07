"""Descriptive historical contrasts; not a production response export."""
from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
import tomllib

import numpy as np

from global_continuous_geographic_cluster_audit import (
    ROOT, add_moments, fit_beta, moments, prepare_differences,
    resolve_inputs, sha256,
)

PROTOCOL = ROOT / 'GLOBAL_HISTORICAL_ASSOCIATION_PROTOCOL_20260907.md'
DIRECT = ['log1p_precip_mm', 'stage1_precip_share', 'stage2_precip_share',
          'cdd_max_days', 'rx5day_mm', 'precipitation_concentration_hhi']
DROUGHT = ['season_scpdsi_mean'] + [f'stage{i}_scpdsi_mean' for i in (1, 2, 3)]


def cluster_fit(blocks):
    """OLS and CR1 covariance from complete-cluster sufficient statistics."""
    if len(blocks) < 2:
        raise ValueError('at least two clusters required')
    total = None
    for value in blocks.values():
        total = add_moments(total, value)
    gram, cross, _, n = total
    p = len(cross)
    if n <= p:
        raise ValueError('no residual degrees of freedom')
    beta, condition = fit_beta(total)
    scale = np.sqrt(np.diag(gram) / n)
    scaled_gram = gram / np.outer(scale, scale)
    # Solve for each cluster influence in a scale-normalized system.
    scores = np.stack([(value[1] - np.einsum('ij,j->i', value[0], beta,
                                          optimize=False)) / scale
                       for value in blocks.values()])
    influence = np.linalg.solve(scaled_gram, scores.T).T / scale
    g = len(blocks)
    correction = g / (g - 1) * (n - 1) / (n - p)
    covariance = correction * np.einsum('ni,nj->ij', influence, influence,
                                       optimize=False)
    if not np.isfinite(covariance).all():
        raise ValueError('nonfinite covariance')
    return beta, covariance, dict(pairs=n, parameters=p, clusters=g,
                                  scaled_gram_condition=condition)


def partial_contrast(beta, covariance, vector):
    value = float(np.einsum('i,i->', vector, beta, optimize=False))
    variance = float(np.einsum('i,ij,j->', vector, covariance, vector, optimize=False))
    if variance < -1e-12:
        raise ValueError('negative contrast variance')
    se = float(np.sqrt(max(variance, 0)))
    bounds = [value - 1.96 * se, value + 1.96 * se]
    return dict(log_yield_contrast=value, cluster_standard_error=se,
                log_yield_interval=bounds,
                fitted_percent_contrast=float(100 * np.expm1(value)),
                fitted_percent_interval=[float(100 * np.expm1(v)) for v in bounds])


def design(data, columns, control):
    years = np.asarray(data['years'])
    if not np.isin(years, np.arange(1983, 2011)).all():
        raise ValueError('association fit attempted outside training period')
    if control == 'quadratic_year':
        year = (years - 2000.) / 10
        prefix = [np.ones(len(years)), year, year**2]
        labels = ['intercept', 'year', 'year_squared']
    elif control == 'year_intercepts':
        prefix = [np.ones(len(years))] + [(years == y).astype(float)
                                        for y in range(1984, 2011)]
        labels = ['intercept'] + [f'end_year_{y}' for y in range(1984, 2011)]
    else:
        raise ValueError('unknown time control')
    x = np.column_stack(prefix + [data['differences'][c] for c in columns])
    if not np.isfinite(x).all():
        raise ValueError('nonfinite design')
    return x, labels + columns


def contrast_vectors(labels, family):
    requests = ({'rain_index_plus_0.1': {'log1p_precip_mm': 0.1}}
                if family.startswith('quantity') else {})
    if family == 'quantity_distribution':
        requests['stage3_to_stage2_share_0.1'] = {'stage2_precip_share': 0.1}
    if family == 'scpdsi_mean':
        requests['scpdsi_plus_1'] = {'season_scpdsi_mean': 1.}
    if family == 'scpdsi_stages':
        requests['all_stage_scpdsi_plus_1'] = {c: 1. for c in DROUGHT[1:]}
    result = {}
    for name, values in requests.items():
        vector = np.zeros(len(labels))
        for column, value in values.items():
            vector[labels.index(column)] = value
        result[name] = vector
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('output exists')
    config_path = ROOT / 'config/global_continuous_geographic_cluster_v1.toml'
    config = tomllib.loads(config_path.read_text())
    output = dict(role='exploratory_historical_partial_associations',
                  causal_or_scc_result=False, production_response_export=False,
                  interval_kind='normal_CR1_conditional_spatial_block_sensitivity',
                  protocol_sha256=sha256(PROTOCOL), code_sha256=sha256(Path(__file__)),
                  helper_sha256=sha256(ROOT/'scripts/global_continuous_geographic_cluster_audit.py'),
                  input_registry_sha256=sha256(config_path), crops={})
    for crop, code, threshold in [('maize', 'mai', 29), ('soy', 'soy', 30)]:
        paths, hashes = resolve_inputs(config, crop)
        heat = [f'stage{i}_tmean_c' for i in (1, 2, 3)] + [
            f'stage{i}_tmax_{threshold}c_degree_days' for i in (1, 2, 3)]
        specs = dict(quantity=heat+DIRECT[:1], quantity_distribution=heat+DIRECT,
                     scpdsi_mean=heat+DROUGHT[:1], scpdsi_stages=heat+DROUGHT[1:])
        accumulators, names, bands = {}, {}, []
        for lower in range(-90, 90, 10):
            data = prepare_differences(paths, DIRECT, heat, DROUGHT, lower, 1982, 2010)
            if data is None:
                continue
            if data['crop_codes'] != [code]:
                raise ValueError('unexpected crop code')
            bands.append(dict(lat_min=lower, pairs=len(data['dy'])))
            cluster_ids = {width: (np.floor((data['lat']+90)/width).astype(int)*1000
                                  + np.floor(data['lon']/width).astype(int))
                           for width in (10, 20)}
            for control in ('quadratic_year', 'year_intercepts'):
                for family, columns in specs.items():
                    x, labels = design(data, columns, control)
                    names[control, family] = labels
                    for width, ids in cluster_ids.items():
                        groups = accumulators.setdefault((control, family, width), {})
                        for block in np.unique(ids):
                            mask = ids == block
                            value = moments(x[mask], data['dy'][mask])
                            groups[int(block)] = add_moments(groups.get(int(block)), value)
                    del x
            del data
            gc.collect()
            print(crop, lower, 'association moments complete', flush=True)
        fits = []
        for (control, family, width), blocks in accumulators.items():
            item = dict(time_controls=control, moisture_family=family,
                        cluster_width_degrees=width)
            try:
                beta, covariance, audit = cluster_fit(blocks)
                vectors = contrast_vectors(names[control, family], family)
                item.update(status='completed', **audit,
                            contrasts={k: partial_contrast(beta, covariance, v)
                                       for k, v in vectors.items()})
            except (ValueError, np.linalg.LinAlgError, FloatingPointError) as error:
                item.update(status='failed', reason=str(error))
            fits.append(item)
        output['crops'][crop] = dict(input_hashes=hashes, bands=bands, fits=fits)
        del accumulators
        gc.collect()
    temporary = args.out.with_suffix('.partial')
    temporary.write_text(json.dumps(output, indent=2, allow_nan=False)+'\n')
    temporary.replace(args.out)
    if any(f['status'] != 'completed' for c in output['crops'].values() for f in c['fits']):
        raise SystemExit('one or more planned fits failed; inspect complete result record')


if __name__ == '__main__':
    np.seterr(invalid='raise', divide='raise', over='raise')
    main()
