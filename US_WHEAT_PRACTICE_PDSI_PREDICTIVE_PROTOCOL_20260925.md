# U.S. weighted all-classes-wheat PDSI predictive protocol

**Frozen:** 2026-09-25 after completing the state-share-weighted historical
association sensitivity and before computing any predictive score.

## Question and boundary

On the selected regional NASS counties that report both irrigated and
non-irrigated all-classes-wheat yield, does the fixed state-share-weighted
seasonal PDSI feature improve out-of-sample prediction of consecutive-year log
yield changes relative to a deterministic time-trend benchmark?

PDSI is the only moisture family in this comparison. No direct rainfall,
wet-day, intensity, dry-spell, or precipitation-extreme feature may enter any
model. Reported irrigation practices are fitted separately. This is historical
predictive validation, not a causal drought or irrigation effect, national U.S.
response, future drought projection, global transfer parameter, damage
function, or SCC input.

## Frozen input and outcome construction

- Reconstruct the exact 9,513 paired wheat county-years from
  `US_WHEAT_PRACTICE_PDSI_PROTOCOL_20260925.md`: fixed-primary full-season NOAA
  county PDSI combined across winter, spring, and durum candidates with fixed
  official 2009 state harvested-acre shares.
- Keep irrigated and non-irrigated outcomes separate. Within each
  county/practice, form a row only when harvest years are consecutive:
  `delta_log_yield = log(y_t) - log(y_t-1)` and
  `delta_pdsi = pdsi_t - pdsi_t-1`.
- As a prespecified nonlinear sensitivity, also construct
  `delta_pdsi_squared = pdsi_t^2 - pdsi_t-1^2`. Squaring occurs before
  differencing. Do not select between the linear primary and quadratic
  sensitivity after inspection.
- Do not bridge missing harvest years. Keep level endpoint years in the
  analysis table so no training difference may share either endpoint with a
  test difference.

## Frozen models

All fits include an intercept plus centered/scaled linear and quadratic terms
in the difference row's harvest year. Continuous columns are centered and
scaled using training rows only.

1. `trend_only`: deterministic year terms only.
2. `pdsi_linear`: year terms plus `delta_pdsi` (primary PDSI model).
3. `pdsi_quadratic`: year terms plus `delta_pdsi` and
   `delta_pdsi_squared` (prespecified sensitivity).

Use ordinary least squares with a training-only SVD tolerance of `1e-10`.
Report aggregate RMSE, MAE, correlation, and out-of-sample R-squared relative
to the training mean. Emit no row predictions and no fitted coefficients.

## Frozen validation splits

- The terminal block is difference-years 2001--2007. Development uses earlier
  differences. Score terminal rows only for counties represented in
  development. The terminal block is not used to alter features or thresholds.
- On development rows, score leave-one-state-out tests for every state with at
  least 50 test differences. Require at least five eligible states per
  practice.
- Before every fit, remove any training difference sharing a
  county/practice/level-year endpoint with a test difference. Require disjoint
  row keys and disjoint endpoint keys after purging.

The linear PDSI model passes the exploratory predictive gate only if its RMSE
improvement over `trend_only` reaches both `0.0001` and 1% of the benchmark
RMSE in every eligible development state and is positive in the terminal
block. This gate is deliberately stringent and is not a causal or agronomic
materiality threshold. The quadratic model is reported as a sensitivity and
cannot rescue a failed linear-primary gate.

## Validation and resources

Require an independent implementation to reconstruct the difference support,
split membership, endpoint purge, training-only scaling, and every aggregate
metric. Saved-precision discrepancies above `1e-10` fail. Run both production
and validation below 512 MiB RSS with one numerical thread. All causal,
irrigation-treatment, national-representativeness, future-drought,
global-transfer, damage, and SCC gates remain false regardless of predictive
performance.
