# Frozen sorghum/cotton direct-weather predictive protocol

This protocol is fixed before any direct-weather model score is inspected. It
tests whether precipitation quantity predicts consecutive-year yield changes
and whether within-season timing or daily extremes add stable out-of-sample
value. It is a historical predictive diagnostic, not causal estimation.

## Sample and outcome

- Use the validated county-average daily-weather panel for the 8,727 geography-
  eligible paired crop--county--years.
- Analyze upland cotton and sorghum grain separately, and each reported
  irrigation practice separately.
- Outcome: consecutive-year change in log reported yield within crop,
  practice, and county; never bridge a missing year.
- Direct precipitation and temperature form one candidate family. Do not add
  PDSI, SPEI, scPDSI, or another moisture index.

## Common temperature and trend controls

Every model contains an intercept; standardized linear and quadratic harvest-
year trends; change in seasonal mean temperature; and change in squared
seasonal mean temperature. Scaling and fitting use training rows only.

## Prespecified precipitation models

1. `temperature_trend_only`: common controls only.
2. `total_quantity`: common controls plus changes in seasonal precipitation
   total and total squared. This is the parsimonious rainfall benchmark.
3. `stage_amounts`: common controls plus changes in rainfall amounts during
   stages 1, 2, and 3. This alternative jointly represents total and timing.
4. `quantity_plus_stage_shares`: `total_quantity` plus changes in stage-1 and
   stage-2 rainfall shares; stage 3 is the omitted share. This is the primary
   incremental within-season timing test.
5. `quantity_plus_extremes`: `total_quantity` plus changes in wet-day count,
   maximum consecutive dry days, and Rx5day. This is the daily-distribution/
   extremes test.

Precipitation concentration HHI, threshold interactions, alternative wet-day
cutoffs, and higher-order stage terms are reserved for later sensitivities and
cannot rescue a failed primary timing or extremes gate.

## Validation and numerical rules

- Development observations end in 1982--2007. Leave one state out when it has
  at least 40 development test rows; at least five states must qualify.
- The temporal test trains on development data and evaluates 2008--2018 rows
  from counties present in development; at least 50 rows are required.
- Remove training differences that share either level-year endpoint with a
  test difference.
- Solve standardized designs by SVD/einsum. Drop singular directions below
  `1e-10` times the largest singular value. Treat numerical warnings and any
  nonfinite coefficient, prediction, or score as failure.
- Material improvement is an RMSE reduction of at least
  `max(0.0001, 0.01 * comparator RMSE)`.

## Promotion gates

- Rainfall quantity passes only if `total_quantity` materially improves on
  `temperature_trend_only` in all eligible state folds and the terminal test.
- Timing passes only if `quantity_plus_stage_shares` materially improves on
  `total_quantity` in every fold.
- Extremes pass only if `quantity_plus_extremes` materially improves on
  `total_quantity` in every fold.
- `stage_amounts` is reported as an alternative and passes only if it improves
  on `total_quantity` in every fold.
- Decisions are separate by crop and practice. A pooled or favorable subset
  cannot override failure elsewhere. Null and negative results remain visible.

Only fold metrics and gate decisions are emitted. Coefficients and row-level
predictions are withheld. No predictive result authorizes a causal weather or
irrigation effect, national representativeness, future climate transfer,
damage, or SCC claim.
