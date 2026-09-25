# Nonlinear drought structure does not improve global terminal prediction

Date: 2026-09-25

## Result

No Matiu-inspired nonlinear moisture family passes the frozen exploratory
promotion rule. The conclusion is negative but useful: adding squared
temperature, squared moisture, and temperature--moisture interactions does not
rescue the existing global drought response for SCC use.

The test uses exact validated common support, country-separated folds,
352,288 maize and 157,003 soybean training pairs, and 50,997 maize and 24,863
soybean terminal pairs. All transformations are applied at levels before
forming consecutive-year changes. Direct precipitation and drought-index
families are mutually exclusive.

## Incremental terminal RMSE

Negative values favor the nonlinear model. RMSE is in annual changes in log
yield.

| Crop | Moisture family | Pooled difference | Equal-country difference | Folds improving (pooled) | Conditional pooled 95% interval | Pass |
|---|---|---:|---:|---:|---:|---|
| Maize | Rainfall quantity | -0.000327 | -0.000680 | 4/5 | [-0.001074, +0.000362] | No |
| Maize | SPEI-1 | +0.001021 | +0.000950 | 2/5 | [-0.000165, +0.002483] | No |
| Maize | SPEI-3 | +0.001786 | +0.001268 | 1/5 | [+0.000135, +0.004076] | No |
| Maize | SPEI-6 | +0.003301 | +0.002056 | 0/5 | [+0.000942, +0.006567] | No |
| Soybean | Rainfall quantity | +0.003728 | +0.007867 | 1/5 | unsupported | No |
| Soybean | SPEI-1 | +0.008235 | +0.006520 | 0/5 | unsupported | No |
| Soybean | SPEI-3 | +0.008244 | +0.006735 | 0/5 | unsupported | No |
| Soybean | SPEI-6 | +0.005791 | +0.005231 | 0/5 | unsupported | No |

The maize quantity nonlinearity improves both aggregate scores and four folds,
but its conditional country-bootstrap interval includes zero. Every nonlinear
maize SPEI model is worse on both aggregate scores; SPEI-3 and SPEI-6 are
significantly worse under the conditional bootstrap. Every soybean nonlinear
model is worse, and the existing singleton scoring fold prevents the prescribed
stratified bootstrap. No unsupported interval is interpreted as evidence.

## Interpretation boundary

This is an exploratory test on previously inspected terminal years, not a
replication of Matiu et al. (2017). The source study uses country mixed models,
one-month SPEI, flexible detrending, and lag terms; this benchmark uses global
crop-grid first differences, country-held-out prediction, three SPEI scales,
and an extreme-heat control. The result does not show that drought or
temperature--drought interaction is biologically unimportant. It shows that
this parsimonious nonlinear extension does not provide stable incremental
prediction on the project's current panel.

Accordingly, no drought coefficient is promoted, no literature percentile
contrast is converted to a slope, and the narrow annual-rainfall quantity SCC
is unchanged. A future drought SCC requires a new or independently held-out
response design plus a matched pulse/base drought increment.

## Reproduction and resource bounds

Protocol: `MATIU_STRUCTURE_PREDICTION_PROTOCOL_20260925.md`.
Program: `scripts/matiu_structure_prediction.py`.
Tracked aggregate outputs: `data/provenance/matiu_structure_maize_20260925.json`
and `data/provenance/matiu_structure_soy_20260925.json`. Ignored run directories
retain the identical job outputs and bounded-run receipts.

The successful jobs were sequential. Sampled peak process-group RSS was
695,009,280 bytes for maize and 411,172,864 bytes for soybean, below the frozen
1.25 GiB ceiling. The structural validator checks hashes, claim flags, metric
identities, fold-stability logic, and the zero-promotion result.
