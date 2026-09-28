# Sorghum/cotton PDSI predictive results

## Frozen test

The preregistered test predicts consecutive-year log-yield changes separately
for crop and irrigation practice. Six leave-one-state-out development folds
and one 2008--2018 same-county terminal test compare: year trend only,
seasonal linear PDSI, seasonal quadratic PDSI, and three-stage linear PDSI.
Training differences sharing a level-year endpoint with a test difference are
purged. The accepted run uses SVD/einsum with explicit finite-value gates.

## Result

No PDSI candidate passes its all-fold promotion gate in any of the four crop--
practice strata.

| Crop/practice | Seasonal linear vs trend | Stage linear vs seasonal | Seasonal quadratic vs linear |
|---|---:|---:|---:|
| Cotton, irrigated | 1/7 folds | 1/7 | 1/7 |
| Cotton, non-irrigated | 4/7 | 4/7 | 1/7 |
| Sorghum, irrigated | 2/7 | 3/7 | 4/7 |
| Sorghum, non-irrigated | 4/7 | 4/7 | 5/7 |

The non-irrigated results are suggestive but geographically unstable. Seasonal
PDSI improves terminal RMSE by 0.0308 log-yield units for cotton and 0.0508 for
sorghum, yet fails in three of six state folds for both crops. Stage-specific
PDSI improves terminal cotton RMSE by 0.0431 relative to seasonal PDSI but
fails three state folds; for non-irrigated sorghum it worsens terminal RMSE by
0.0291. The quadratic seasonal form passes five of seven non-irrigated sorghum
folds but fails Oklahoma, Texas, and therefore the all-fold rule despite a
positive terminal result.

## Interpretation

These results do not support promoting PDSI, nonlinear PDSI, or stage-specific
PDSI to a sorghum/cotton damage function. They do indicate that irrigation
stratification and state heterogeneity matter: gains are more frequent in the
non-irrigated strata, but the design does not identify a causal irrigation
effect. The PDSI family remains a robustness diagnostic. No coefficient, row
prediction, causal response, future projection, damage, or SCC value is
released.
