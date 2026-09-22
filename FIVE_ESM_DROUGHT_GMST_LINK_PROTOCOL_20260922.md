# Five-ESM drought--GMST endpoint-link protocol

Status: frozen before fitting or inspecting any drought-per-GMST slope.

## Objective and claim boundary

Test whether the completed late-century crop-calendar SPEI scenario contrasts
have a stable same-realization global-temperature scaling across five named
ESMs and two higher-forcing SSP contrasts. This is the closest direct
diagnostic to the wildfire project's temperature-to-impact link that can be
constructed from the validated local assets without inventing a new climate
model or downloading more data.

The estimand is an **endpoint scenario slope**, not anthropogenic attribution,
a CO2-only response, a causal climate coefficient, a transient emulator, or a
marginal-emissions response. SSP differences include non-CO2 forcing and
internal variability. Even a successful predictive diagnostic cannot enter
GIVE damages or SCC until a matched baseline/pulse mapping and a separately
validated crop-yield response exist.

## Frozen inputs

Use the independently validated 15-case matrix
`data/interim/five_esm_late_drought_crop_matrix_20260921/result.json` and its
validation receipt. Use the exact local same-realization annual-GMST Parquet
files in `data/interim/isimip3b` for GFDL-ESM4, IPSL-CM6A-LR,
MPI-ESM1-2-HR and MRI-ESM2-0 member `r1i1p1f1`, and UKESM1-0-LL member
`r1i1p1f2`, each under SSP1-2.6/3-7.0/5-8.5 for 2091--2100. Hash every input.
Require exactly one row for every year and use only 2092--2099, matching the
crop-window matrix. Average the eight annual GMST values equally, as in the
registered late-window weather normalization. Do not use 2091 or 2100, refit
SPEI parameters, alter crop support, or impute missing records.

## Frozen response form

For each of the 90 crop--window--SPEI-scale--area-basis cells, form ten points:
SSP3-7.0 minus SSP1-2.6 and SSP5-8.5 minus SSP1-2.6 for each ESM. Let `x` be
the eight-year mean GMST difference and `y` the corresponding SPEI difference.
Fit the one-parameter origin-constrained slope

`beta = sum(x*y) / sum(x*x)`.

The zero intercept encodes exact zero scenario difference at zero temperature
difference and avoids estimating an intercept from ten endpoints. Named ESMs
and the two contrasts receive equal weight; do not treat them as independent
probability draws. Report the slope in SPEI units K-1, fitted RMSE, zero-change
RMSE, and all ten observed/predicted/residual records. Do not add quadratic,
interaction, ESM-specific-slope, weighting, or feature-selection alternatives
after seeing results.

The primary cells are maize and soybean, rainfed, whole-season SPEI-3. All
other windows, scales and area bases are declared robustness cells rather than
alternative primaries.

## Frozen holdouts and pass rules

1. Whole-ESM: omit one ESM's two contrasts, fit on the other eight points, and
   score the two held endpoints. Repeat for all five. A cell passes only if its
   fitted RMSE is strictly below zero-change RMSE in every ESM holdout.
2. Whole-scenario: fit on the five SSP5-8.5 contrasts and score SSP3-7.0, then
   reverse. A cell passes only if fitted RMSE is strictly below zero-change
   RMSE in both holdouts.
3. A diagnostic cell passes the combined predictive rule only if both rules
   pass and the ten-point denominator is finite and positive. No tolerance,
   fold exclusion, or post-result relaxation is allowed.

Report pass counts over all 90 cells and the complete primary results. The
holdouts are reuse of the same climate ensemble, not independent validation;
passing them would show only internal transport stability. Do not calculate
confidence intervals or probabilities from five models.

## Reproducibility and resource limits

Write one aggregate JSON containing source hashes, 90 fits, all held-out
scores, named observations, and closed downstream gates. A separately written
validator must reread all matrix and GMST inputs, recompute every slope,
prediction, residual, RMSE, pass flag and aggregate count, and bind the output
hash. Use one numerical worker, sampled RSS <=512 MiB, <=64 MiB retained
output, and >=130 GiB free disk. No raw-data download, yield fitting,
monetization, GIVE execution, or SCC calculation is authorized by this
protocol.
