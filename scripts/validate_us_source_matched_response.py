"""Numerical replication with explicit bases and SVD, not causal validation."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from estimate_us_source_matched_response import load_inputs, write_new, identity, sha256, ROOT, base


def explicit_basis(frame, names):
    values = []
    for name in names:
        if name == 'precipitation_per_100mm':
            value = frame.precip_mm.to_numpy()/100
        elif name == 'precipitation_per_100mm_squared':
            value = (frame.precip_mm.to_numpy()/100)**2
        elif name.endswith('_squared'):
            value = frame[name[:-8]].to_numpy()**2
        else:
            value = frame[name].to_numpy()
        values.append(value)
    return np.column_stack(values)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--result', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    frames, mask, binding, _ = load_inputs()
    if json.loads(args.manifest.read_text()) != binding:
        raise ValueError('input binding changed')
    result = json.loads(args.result.read_text())
    if result['input_manifest'] != identity(args.manifest.resolve()) or result['causal_or_scc_result'] is not False:
        raise ValueError('result lineage or scope differs')
    checks = []
    for entry in result['estimates']:
        if entry['status'] != 'estimated':
            checks.append(dict(status='original_failure_preserved', entry=entry))
            continue
        f = frames[entry['weather_source']]
        selected = mask if entry['cohort'] == 'matched_positive' else np.ones(len(mask), dtype=bool)
        f = f.loc[selected & f.outcome_crop.eq(entry['crop']) & f.irrigation_practice.eq(entry['practice'])]
        r = entry['result']
        if len(f) != r['rows'] or f.county_geoid.nunique() != r['counties']:
            raise ValueError('fit support differs')
        raw = explicit_basis(f, r['terms'])
        groups = [pd.factorize(f.county_geoid, sort=True)[0],
                  pd.factorize(f.state.astype(str)+'_'+f.harvest_year.astype(str), sort=True)[0]]
        within, _, _ = base.alternating_residualize(np.column_stack([np.log(f.yield_bu_acre), raw]), groups, 1e-10, 1000)
        y, x = within[:, 0], within[:, 1:]
        scale = x.std(axis=0)
        z = x/scale
        b, _, rank, _ = np.linalg.lstsq(z, y, rcond=None)
        if rank != len(r['terms']):
            raise ValueError('SVD rank differs')
        beta = b/scale
        np.testing.assert_allclose(beta, r['beta'], rtol=1e-7, atol=1e-10)
        error = y-z@b
        orthogonality = float(np.max(np.abs(z.T@error))/len(f))
        group_mean = max(float(np.max(np.abs(pd.DataFrame(np.column_stack([y, z])).groupby(g).mean().to_numpy()))) for g in groups)
        if orthogonality > 1e-8 or group_mean > 1e-8:
            raise ValueError('OLS/fixed-effect orthogonality failed')
        # Independent scaled cross-product sandwich; original FE-degree-of-freedom
        # limitation retained explicitly, not corrected by this numerical audit.
        codes, labels = pd.factorize(f.county_geoid, sort=True)
        scores = np.zeros((len(labels), len(b)))
        np.add.at(scores, codes, z*error[:, None])
        influence = np.linalg.solve(z.T@z, scores.T).T/scale
        n, k = x.shape
        covariance = len(labels)/(len(labels)-1)*(n-1)/(n-k)*(influence.T@influence)
        np.testing.assert_allclose(covariance, r['covariance_county_cluster'], rtol=1e-6, atol=1e-11)
        checks.append(dict(status='numerically_replicated', weather_source=entry['weather_source'], crop=entry['crop'],
            practice=entry['practice'], form=entry['form'], threshold_c=entry['threshold_c'], cohort=entry['cohort'],
            maximum_beta_residual=float(np.max(np.abs(beta-np.array(r['beta'])))),
            maximum_covariance_residual=float(np.max(np.abs(covariance-np.array(r['covariance_county_cluster'])))),
            maximum_scaled_FE_group_mean=group_mean, maximum_scaled_OLS_moment=orthogonality))
    write_new(args.out, dict(status='us_source_matched_numerical_checks_complete', causal_or_scc_result=False,
        not_independent_outcome_or_causal_validation=True, shared_residualizer_disclosed=True,
        result=identity(args.result.resolve()), input_manifest=identity(args.manifest.resolve()),
        code_sha256=sha256(Path(__file__)), checks=checks))
    print('Numerically replicated', sum(c['status'] == 'numerically_replicated' for c in checks), 'fits')


if __name__ == '__main__':
    main()
