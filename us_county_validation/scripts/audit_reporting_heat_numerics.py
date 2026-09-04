"""Independently check every fit's coefficients and cluster covariance via QR.

Reuses the original sample/design and FE residualization; this is a numerical
audit, not an independent replication of the identification or sample design.
"""
import argparse
import json
from pathlib import Path
import sys
import warnings

import numpy as np
import pandas as pd
import estimate_us_direct_practice_precipitation_association as base
import run_reporting_heat_sensitivity as sensitivity


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('audit output already exists')
    original = base.clustered_ols
    checks = []

    def checked(y, x, cluster):
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter('always', RuntimeWarning)
            fit = original(y, x, cluster)
        scale = x.std(axis=0)
        z = x / scale
        q, r = np.linalg.qr(z, mode='reduced')
        beta = np.linalg.solve(r, np.einsum('ni,n->i', q, y, optimize=False))
        residual = y - np.einsum('ni,i->n', z, beta, optimize=False)
        codes, labels = pd.factorize(cluster, sort=True)
        scores = np.stack([np.einsum('ni,n->i', z[codes == g],
                           residual[codes == g], optimize=False)
                           for g in range(len(labels))])
        # Cluster coefficient influences via triangular solves, not X'X inverse.
        influence = np.linalg.solve(r, np.linalg.solve(r.T, scores.T)).T / scale
        n, k = x.shape
        correction = len(labels)/(len(labels)-1) * (n-1)/(n-k)
        covariance = correction * np.einsum('gi,gj->ij', influence, influence,
                                           optimize=False)
        target = fit['covariance_beta_cluster_county']
        if not np.isfinite(target).all():
            raise ValueError('nonfinite original covariance')
        np.testing.assert_allclose(fit['beta'], beta/scale, rtol=1e-7, atol=1e-10)
        np.testing.assert_allclose(target, covariance, rtol=1e-6, atol=1e-10)
        checks.append(dict(rows=n, terms=k,
            maximum_absolute_beta_difference=float(np.max(np.abs(fit['beta']-beta/scale))),
            maximum_absolute_covariance_difference=float(np.max(np.abs(target-covariance))),
            covariance_relative_frobenius_error=float(np.linalg.norm(target-covariance)/np.linalg.norm(covariance)),
            runtime_warnings=[str(w.message) for w in captured]))
        return fit

    base.clustered_ols = checked
    rerun = args.out.with_suffix('.rerun.json')
    sys.argv = [sys.argv[0], '--out', str(rerun)]
    sensitivity.main()
    original_path = base.PROJECT/'data/provenance/us_reporting_heat_sensitivity_20260904.json'
    if json.loads(original_path.read_text()) != json.loads(rerun.read_text()):
        raise ValueError('sensitivity rerun differs from saved results')
    result = dict(status='passed', fit_count=len(checks), checks=checks,
        saved_results_sha256=base.sha256(original_path),
        audit_code_sha256=base.sha256(Path(__file__)),
        scope='independent_QR_coefficient_and_covariance_check_same_design_and_FE')
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(f'QR numerical audit passed for {len(checks)} fits')


if __name__ == '__main__':
    main()
