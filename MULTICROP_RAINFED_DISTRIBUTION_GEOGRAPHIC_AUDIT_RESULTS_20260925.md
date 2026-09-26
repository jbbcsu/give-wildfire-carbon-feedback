# Multicrop rainfed distribution geographic audit (2026-09-25)

## Decision

No crop-by-distribution comparison passes the prespecified descriptive predictive-support gate. The gate requires all four of:

1. the paired 10-degree-cluster bootstrap 95% RMSE-difference interval is below zero;
2. the bootstrap tail probability remains at or below 0.05 after Holm adjustment across all 30 crop-by-model tests;
3. candidate RMSE is lower in every one of the five held-out spatial folds; and
4. more than half of occupied 10-degree blocks have lower candidate mean squared error.

This is a useful negative result. Aggregate spatial out-of-fold improvements from the parent diagnostic are not yet geographically and multiplicity-robust enough to support a response-model choice.

## Closest signals

Five comparisons have unadjusted paired-cluster intervals entirely below zero. None survives the 30-test Holm correction.

| Crop | Distribution extension | OOF RMSE difference | Cluster-bootstrap 95% interval | Raw tail probability | Holm-adjusted | Blocks improved | Folds improved |
|---|---|---:|---:|---:|---:|---:|---:|
| Maize | timing/concentration | -0.000850 | [-0.001536, -0.000203] | 0.0120 | 0.3599 | 58.1% | 5/5 |
| Maize | occurrence/intensity | -0.001010 | [-0.001973, -0.000046] | 0.0388 | 1.0000 | 58.9% | 3/5 |
| Maize | all distribution | -0.001067 | [-0.002068, -0.000115] | 0.0256 | 0.7167 | 54.3% | 3/5 |
| Soybean | all distribution | -0.002575 | [-0.004946, -0.000352] | 0.0236 | 0.6843 | 55.4% | 5/5 |
| Spring wheat | occurrence/intensity | -0.002532 | [-0.004726, -0.000045] | 0.0460 | 1.0000 | 67.2% | 5/5 |

The closest prespecified patterns are therefore maize timing/concentration, soybean all-distribution, and spring-wheat occurrence/intensity: each improves all five folds and a majority of occupied blocks, but none retains multiplicity-adjusted support. These are candidates for new-data confirmation, not selected response models.

## Geographic support

| Crop | Pairs | Occupied 10-degree blocks | Effective block count | Largest pair share |
|---|---:|---:|---:|---:|
| Maize | 105,157 | 129 | 67.3 | 2.64% |
| First rice | 66,720 | 108 | 48.8 | 3.74% |
| Second rice | 11,107 | 27 | 10.6 | 16.58% |
| Soybean | 42,770 | 56 | 28.0 | 5.84% |
| Spring wheat | 35,833 | 64 | 33.0 | 6.45% |
| Winter wheat | 60,033 | 86 | 45.6 | 4.35% |

Second rice has notably weak and concentrated geographic support. Its intervals and block shares should be treated as especially coarse sensitivity evidence.

## Scope and limitations

- Scores are fixed five-fold spatial out-of-fold predictions. Every candidate is paired against seasonal quantity on the same crop-grid-year differences.
- The bootstrap resamples 10-degree geographic blocks while retaining all observations in each sampled block. Fits are not reestimated inside bootstrap replicates, so intervals are conditional on the fixed fitted models.
- The Holm family contains all six crops times five distribution extensions. Tail probabilities are descriptive bootstrap tail measures, not causal-test probabilities.
- Block signs describe held-out prediction error only. A lower-error block is not a crop-impact winner, an economic winner, a beneficial-rainfall location, or a welfare result.
- No row predictions, bootstrap draws, or coefficients are exported.
- Causal interpretation, economic winner/loser interpretation, production selection, response draws, damages, and SCC use are all unauthorized.
- The maximum reported worker RSS is 493,092,864 bytes (470.2 MiB), below the 512 MiB contract. A deterministic validator recomputation peaked at 492,568,576 bytes and matched all non-runtime fields; its independent Holm calculation also matched.

## Artifacts

- Contract: `config/multicrop_rainfed_distribution_geographic_audit_v1.toml`
- Evaluator: `scripts/evaluate_multicrop_rainfed_distribution_geographic_audit.py`
- Synthetic tests: `scripts/test_multicrop_rainfed_distribution_geographic_audit.py`
- Validator: `scripts/validate_multicrop_rainfed_distribution_geographic_audit.py`
- Result: `data/provenance/multicrop_rainfed_distribution_geographic_audit_20260925.json`
- Validation: `data/provenance/multicrop_rainfed_distribution_geographic_audit_validation_20260925.json`

## Next gate

The highest-value confirmation is to freeze the three closest patterns above before observing additional years or an independent yield product, then repeat the paired geographic audit as a three-test external confirmation family. Genuine country- or subnational heterogeneity requires a separately locked boundary crosswalk and sufficient within-unit support; it should not be inferred from these grid blocks. Only a replicated predictive result would justify the further causal identification work needed before geographic impacts, economic winners/losers, damages, or GIVE SCC calculations.
