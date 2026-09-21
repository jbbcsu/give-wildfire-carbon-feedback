# FishMIP--FAO global historical temporal diagnostic

## Purpose and post-existing-evidence status

Compare the global time pattern of the four validated historical FishMIP total
catch-density trajectories with the provisional global marine-tonnage series
from the independently reconciled FAO FishStat headless export. Both inputs
have already been inspected in separate analyses, so this is a transparent
post-existing-evidence diagnostic, not a new untouched validation or a model
selection exercise.

The comparison can test whether historical model trajectories resemble the
observed aggregate direction and variation. It cannot attribute discrepancies
to climate: observed catches also reflect effort, management, reporting,
markets, technology, stock depletion, and spatial redistribution, while the
model `histsoc` assumptions are not an identified reconstruction of those
drivers.

## Frozen inputs and support

Require the exact 1950--2014 historical `tc` files for BOATS and EcoOcean under
GFDL-ESM4 and IPSL-CM6A-LR, with SHA-256 values recorded in the executable.
Use the intersection of their finite first-month masks and require the already
validated time-stable support to remain finite and nonnegative in every month.
For each path, calculate a cosine-latitude-weighted spatial mean for each
month and the arithmetic mean of the twelve monthly means for each year.
Absolute model levels are never averaged across ecosystem models.

The observed source is the exact symbol-preserving 1950--2024 headless export,
SHA-256 `ca58247c4f6044948b01048e4a808d21a4975c9f4171e3d0d1fbc321e46ebb52`,
under its exact contract. For 1950--2014, sum positive values only where
`environment_class=marine` and `measure_code=Q_tlw`; retain status meanings and
never turn missing/suppressed values into observed zero. This is the same
provisional filter used in the descriptive support audit; the supported
FishStat GUI-menu reconciliation remains open.

## Frozen comparisons

Normalize observed tonnage and each model path by its own 2005--2014 mean.
For the full 1950--2014 period and the fixed 1980--2014 sensitivity, report:

- Pearson correlation, mean bias, RMSE, and log-RMSE of normalized levels;
- correlation, RMSE, and sign agreement for annual first differences; and
- separate ordinary least-squares slopes of observed and modeled normalized
  levels on centered calendar year.

Report every forcing/model path. Do not select, average, probability-weight,
or calibrate a model from these diagnostics. The later period is a reporting-
quality sensitivity fixed before calculation, not a preferred fit window.
A separately implemented reader must reconstruct all annual indices and
reported metrics from the frozen raw inputs.

## Claim boundary

This result is not species-, stock-, country-, fleet-, or EEZ-level validation.
It supplies no effort or management identification, climate attribution,
marginal CO2 pulse, welfare response, economic damage, probability weight, or
SCC. A weak match does not invalidate every modeled biophysical response, and
a strong match would not prove causal skill.
