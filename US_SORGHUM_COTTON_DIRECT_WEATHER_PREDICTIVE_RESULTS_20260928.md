# Sorghum/cotton direct-weather predictive results

## Result

The frozen comparison evaluates seasonal rainfall quantity, stage amounts,
stage shares, and wet/dry extremes under common temperature and time controls.
It uses six leave-one-state-out development folds plus one 2008--2018 same-
county terminal test, separately by crop and practice. No candidate passes its
all-seven-fold promotion gate in any stratum.

| Crop/practice | Total rain vs temperature | Stage amounts vs total | Stage shares vs total | Extremes vs total |
|---|---:|---:|---:|---:|
| Cotton, irrigated | 2/7 | 3/7 | 2/7 | 3/7 |
| Cotton, non-irrigated | 2/7 | 4/7 | 4/7 | 4/7 |
| Sorghum, irrigated | 1/7 | 4/7 | 2/7 | 3/7 |
| Sorghum, non-irrigated | 3/7 | 3/7 | 4/7 | 3/7 |

The clearest within-season hint is non-irrigated cotton. Stage shares improve
terminal RMSE by 0.0248 log-yield units relative to total rainfall and pass
Arkansas, Mississippi, Texas, and the terminal test, but fail Louisiana, New
Mexico, and Oklahoma. Stage amounts show the same 4/7 count. The extremes
model passes four non-irrigated-cotton state folds, but its terminal improvement
(0.00281) is below the registered 1% materiality threshold (0.00393).

For non-irrigated sorghum, stage shares pass four state folds but worsen the
terminal RMSE by 0.0186. Total seasonal rainfall itself is not stable: it passes
only two of seven cotton comparisons in either practice, one of seven for
irrigated sorghum, and three of seven for non-irrigated sorghum.

## Interpretation

The evidence does not justify replacing the parsimonious global benchmark with
a U.S. sorghum/cotton quantity, timing, or extremes response. It does show why
within-season features and winners/losers must be reported: favorable results
are crop-, practice-, state-, and period-specific. These predictive null gates
do not invalidate the separate global-maize quantity benchmark, which uses a
different outcome, geography, and estimand. No coefficient, row prediction,
causal effect, future transfer, damage, or SCC value is released.
