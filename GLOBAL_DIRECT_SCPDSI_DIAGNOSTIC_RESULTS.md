# Validated global direct-quantity versus historical scPDSI diagnostic

## Status and claim boundary

The version-1 nonproduction diagnostic completed on real maize and soybean
data and passed full immediate-input, split, fit, metric, and SHA-256
recomputation. It emits aggregate held-out metrics only: no coefficients or
row predictions. It is a historical predictive comparison, not a causal
precipitation or drought response, climate-to-drought projection, agricultural
damage function, production-model selection, or SCC result.

The common sample contains 209,036 consecutive crop-grid-year first
differences: 101,157 maize early-period pairs, 45,633 maize later-period pairs,
41,678 soybean early-period pairs, and 20,568 soybean later-period pairs. Every
model uses identical outcome pairs and stage temperature/heat controls. Direct
seasonal quantity and scPDSI are fit in separate moisture families and are
never stacked.

## Spatial-fold results

The table averages each loss over the five unbuffered hashed 5-degree spatial
folds. Percent changes compare the ratio of the model's mean loss to the
controls-only mean; negative values are lower loss. `RMSE folds` and `MAE
folds` count folds with lower loss than controls. These are equal-pair-weighted
metrics, not area-, production-, revenue-, or welfare-weighted metrics.

| Crop | Model | Mean RMSE | RMSE change | RMSE folds | Mean MAE | MAE change | MAE folds |
|---|---|---:|---:|---:|---:|---:|---:|
| Maize | Controls only | 0.290401 | 0.000% | 0/5 | 0.183818 | 0.000% | 0/5 |
| Maize | Direct seasonal quantity | 0.288589 | -0.624% | 5/5 | 0.183554 | -0.144% | 4/5 |
| Maize | scPDSI seasonal mean | 0.289055 | -0.463% | 5/5 | 0.184264 | +0.243% | 2/5 |
| Maize | scPDSI seasonal summary | 0.288697 | -0.587% | 5/5 | 0.184129 | +0.169% | 2/5 |
| Maize | scPDSI stage means | 0.289169 | -0.424% | 5/5 | 0.184370 | +0.301% | 2/5 |
| Soybean | Controls only | 0.211282 | 0.000% | 0/5 | 0.147888 | 0.000% | 0/5 |
| Soybean | Direct seasonal quantity | 0.209670 | -0.763% | 5/5 | 0.147847 | -0.028% | 2/5 |
| Soybean | scPDSI seasonal mean | 0.210911 | -0.176% | 4/5 | 0.148107 | +0.148% | 2/5 |
| Soybean | scPDSI seasonal summary | 0.210183 | -0.520% | 4/5 | 0.147638 | -0.169% | 4/5 |
| Soybean | scPDSI stage means | 0.210938 | -0.163% | 4/5 | 0.148123 | +0.159% | 2/5 |

Direct seasonal quantity has the lowest mean spatial-fold RMSE for both crops
and lowers RMSE in all ten crop-by-fold comparisons. The absolute improvements
are small. MAE is less uniform: direct quantity lowers maize MAE in four folds
but soybean MAE in only two. Richer scPDSI summaries therefore do not
uniformly dominate the parsimonious quantity representation, while the metric
sensitivity also prevents a production-model promotion from this diagnostic.

## Retrospective temporal and stress checks

The 1982--1989 to 2012--2016 score is explicitly retrospective. The acquired
CRU scPDSI file records a 1901--2025 calibration period, so test and post-test
climate enter the index transform. Regression fitting and scaling use early
rows only, but this is not a prospective scPDSI holdout. Direct quantity lowers
retrospective RMSE by 0.170% for maize and 0.344% for soybean, while increasing
MAE by 0.395% and 0.728%. All three scPDSI variants increase soybean RMSE by
1.48--1.57% and MAE by 2.54--2.72% in this retrospective score.

RMSE winners in the crop-specific, endpoint-purged stress checks are:

| Stress holdout | Maize winner (change from controls) | Soybean winner (change from controls) |
|---|---|---|
| Long direct dry spell | scPDSI seasonal summary (-0.688%) | Direct quantity (-1.787%) |
| High direct Rx5day | scPDSI seasonal summary (-0.189%) | Controls only (0.000%) |
| scPDSI drought at or below -2 | scPDSI seasonal summary (-1.063%) | Direct quantity (-1.495%) |
| High heat | scPDSI seasonal summary (-0.533%) | Direct quantity (-2.151%) |
| Union | scPDSI seasonal summary (-0.811%) | scPDSI seasonal summary (-1.211%) |

The stress results are heterogeneous rather than a universal drought-index
win. In particular, direct quantity worsens maize RMSE in the direct-dry and
direct-wet holdouts, while the scPDSI seasonal summary is the lowest-RMSE maize
model in all five stress checks. For soybean, direct quantity wins three of
five and controls alone win the high-Rx5day check. These descriptive skill
patterns do not identify drought or precipitation effects.

## Remaining gates

- No production selection metric or rule is authorized; RMSE, MAE, and R2 are
  all retained, and metric sensitivity is reported.
- Spatial folds are unbuffered. Adjacent train/test blocks are possible;
  buffered-block and leave-region or climate-zone sensitivity are pending.
- A separate hash-locked paired 10-degree-cell bootstrap sensitivity now
  quantifies spatial-OOF loss-difference variation conditional on the fitted
  fold models. It does not refit training samples or cover model-choice,
  causal, response, future-climate, damage, or SCC uncertainty. All twelve
  scPDSI-versus-direct RMSE/MAE intervals include zero; see
  `DIRECT_SCPDSI_PAIRED_LOSS_UNCERTAINTY.md`.
- The common-30 C maize heat-control sensitivity is constructed but not yet
  evaluated. The primary run uses 29 C for maize and 30 C for soybean.
- SPEI and soil-moisture competing families are not yet built.
- A frozen pre-holdout drought-index calibration is required for a prospective
  temporal comparison.
- Historical predictive skill cannot be transported to future climate,
  damages, welfare, or SCC without separate causal-response,
  climate-to-moisture, adaptation, and welfare validation.

## Reproducibility identity

- Config SHA-256: `260326ec5b797ac85a807575b884896ad918e58c60df71f227cbb061e277236a`
- Input-audit SHA-256: `cf8a4f55327e7b90855e3896e437b3390d7308a3869ab94750ccd6906eaec68c`
- Result SHA-256: `94494d1c0da127aaa8b31f7447780a083842b481f9806dcd5af5faef95f409c6`
- Validation-receipt SHA-256: `bff6c56861f508f113e81b1892b68cc9ad588afc8c53a23367a005b16efa5346`
- Validation status: `validated_nonproduction_predictive_diagnostic`

The ignored result and input files can be regenerated with the commands in
`DIRECT_SCPDSI_PREDICTIVE_DIAGNOSTIC.md`.
