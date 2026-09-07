#!/usr/bin/env python3
"""Synthetic algebra and deterministic assignment tests only."""
from __future__ import annotations

import numpy as np

from global_continuous_geographic_cluster_audit import (
    MODELS, add_moments, bootstrap_contrasts, fit_beta, fold_ids, moments,
)


rng = np.random.default_rng(1907)
x = np.column_stack([np.ones(240), rng.normal(size=(240, 7))])
true_beta = rng.normal(size=x.shape[1])
y = np.einsum("ni,i->n", x, true_beta, optimize=False) + rng.normal(scale=0.2, size=len(x))
combined = add_moments(moments(x[:80], y[:80]), moments(x[80:180], y[80:180]))
beta, condition = fit_beta(combined)
expected = np.linalg.lstsq(x[:180], y[:180], rcond=None)[0]
assert np.allclose(beta, expected, rtol=1e-11, atol=1e-11)
assert np.isfinite(condition) and condition < 1e10

lat = np.array([-89.5, -0.5, 0.5, 89.5])
lon = np.array([0.5, 179.5, 180.5, 359.5])
lat_blocks, lon_blocks, folds = fold_ids(lat, lon)
assert lat_blocks.tolist() == [0, 8, 9, 17]
assert lon_blocks.tolist() == [0, 17, 18, 35]
assert folds.tolist() == [2, 2, 1, 1]
assert np.array_equal(folds, fold_ids(lat, lon)[2])

cluster_stats = {}
for fold in range(5):
    for block in range(2):
        stats = {}
        for index, model in enumerate(MODELS):
            count = 10 + fold + block
            stats[model] = ((1.0 + 0.1 * index) * count, count)
        cluster_stats[(fold, fold, block)] = stats
first = bootstrap_contrasts(cluster_stats, replicates=50, seed=20260907)
second = bootstrap_contrasts(cluster_stats, replicates=50, seed=20260907)
assert first == second
assert set(first) == {
    "quantity_minus_controls_only", "quantity_distribution_minus_quantity",
    "scpdsi_mean_minus_quantity", "scpdsi_stages_minus_quantity",
}
for interval in first.values():
    assert interval["p025"] <= interval["median"] <= interval["p975"]

singular = np.ones((20, 2))
try:
    fit_beta(moments(singular, np.arange(20.0)))
except ValueError as error:
    assert "ill-conditioned" in str(error)
else:
    raise AssertionError("singular design accepted")

print("geographic folds, accumulated fit, cluster bootstrap, and rank gate passed")
