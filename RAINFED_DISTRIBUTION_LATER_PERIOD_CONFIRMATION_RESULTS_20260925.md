# Rainfed distribution later-period confirmation (2026-09-25)

## Decision

The frozen 1982–1989 patterns do **not** confirm on the genuinely later local 2012–2016 rainfed panels. Neither of the two available comparisons passes the prespecified confirmation gate, so predictive family-level promotion remains unauthorized.

| Crop | Frozen candidate | Seasonal-quantity OOF RMSE | Candidate OOF RMSE | Candidate minus reference | Paired 10°-cluster 95% interval | Holm-adjusted tail probability | Blocks improved | Folds improved | Pass |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Maize | timing/concentration | 0.282276 | 0.282768 | +0.000492 | [+0.000030, +0.001167] | 0.0680 | 46.8% | 0/5 | No |
| Soybean | all distribution | 0.182467 | 0.180745 | -0.001722 | [-0.008388, +0.003127] | 0.7443 | 41.8% | 2/5 | No |

For maize, the frozen timing/concentration extension is worse than seasonal quantity in every spatial fold, and the paired geographic interval lies entirely on the adverse side. For soybean, the pooled full-distribution RMSE is lower, but the interval crosses zero, only two folds improve, and fewer than half the occupied geographic blocks improve. The soybean pooled result is therefore geographically unstable rather than a confirmation.

## Frozen design

- Selection outcomes: 1982–1989.
- Confirmation outcomes: independent 2012–2016 GDHY rainfed (`noirr`) crop-grid years.
- Frozen comparisons: maize timing/concentration versus seasonal quantity; soybean all-distribution versus seasonal quantity.
- No other model family was searched in the confirmation data.
- Models are refitted and scored by five-fold spatial out-of-fold prediction within the later period. This confirms model-family portability, not transport of early-period coefficients.
- Fixed out-of-fold losses are paired within 10-degree geographic blocks and resampled with 5,000 cluster-bootstrap replicates.
- Multiplicity family: exactly two frozen comparisons, adjusted using Holm.
- A comparison must improve pooled RMSE, have an interval upper bound below zero, pass the Holm threshold, improve all five folds, and improve a majority of occupied blocks.

Maize uses 61,302 observed levels, 46,773 consecutive pairs, and 126 occupied 10-degree blocks. Soybean uses 27,181 observed levels, 21,026 pairs, and 55 blocks. Stage-duration, precipitation, and wet-day reconciliation errors are exactly zero for both sources.

## Spring wheat

Spring wheat occurrence/intensity was the third exploratory pattern proposed for confirmation, but no local `data/interim/swh_noirr_2012_2016_stage_estimation_panel.parquet` exists. It is recorded as unavailable. No crop proxy, irrigation substitution, synthetic panel, or imputation was used.

## Claim gates and validation

- Confirmation pass count: 0/2.
- Predictive family-level promotion: false.
- Coefficients, row predictions, and bootstrap draws are not exported.
- Causal interpretation, economic winner/loser interpretation, production selection, response draws, damages, and SCC use remain false.
- Maximum reported worker RSS: 398,442,496 bytes (380.0 MiB), below 512 MiB.
- A deterministic full recomputation matches all non-runtime fields and peaked at 401,047,552 bytes.
- An independently implemented two-test Holm calculation matches exactly.

## Artifacts

- Contract: `config/rainfed_distribution_later_period_confirmation_v1.toml`
- Evaluator: `scripts/evaluate_rainfed_distribution_later_period_confirmation.py`
- Validator: `scripts/validate_rainfed_distribution_later_period_confirmation.py`
- Contract test: `scripts/test_rainfed_distribution_later_period_confirmation.py`
- Result: `data/provenance/rainfed_distribution_later_period_confirmation_20260925.json`
- Validation: `data/provenance/rainfed_distribution_later_period_confirmation_validation_20260925.json`

## Consequence

The early-period predictive patterns should not be promoted as global distribution-response functions. The next defensible evidence step is additional independent years or a genuinely independent yield product with the same two comparisons kept frozen. Country, economic, damage, marginal-CO2, and GIVE SCC calculations remain downstream of a replicated predictive result and causal identification; this failed confirmation does not authorize them.
