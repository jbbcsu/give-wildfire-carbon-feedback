# Frozen sorghum/cotton PDSI predictive protocol

This protocol is fixed before inspecting any model score. Its purpose is to
test whether a PDSI-only moisture family predicts consecutive-year yield
changes and whether within-season stage detail improves on a parsimonious
seasonal mean. It does not estimate a causal weather response.

## Sample and outcome

- Use only the validated primary-calendar PDSI panel with exact irrigated and
  non-irrigated pairs and the three historically unstable Colorado counties
  already excluded.
- Analyze upland cotton and sorghum grain separately, and analyze each reported
  practice separately.
- Outcome: consecutive-year change in log reported yield within the same crop,
  practice, and county. Never difference across a gap.
- Moisture predictors are PDSI only. Do not add raw precipitation,
  temperature, SPEI, scPDSI, or another moisture representation.

## Candidate models

Every model includes an intercept plus standardized linear and quadratic
harvest-year trends learned on the training sample.

1. `trend_only`: year terms only.
2. `season_linear`: change in full-season day-weighted mean PDSI.
3. `season_quadratic`: changes in full-season PDSI and PDSI squared.
4. `stage_linear`: changes in the three stage-specific day-weighted mean PDSI
   values. This is an alternative representation, not an addition to the
   seasonal mean.

The stage model is the prespecified within-season test. Preplant PDSI,
threshold-day counts, and monthly minima are reserved for later sensitivity
work and cannot rescue a failed primary gate.

## Validation splits

- Development period: consecutive-year observations ending in 1982--2007.
- Geographic validation: leave one development-period state out whenever that
  state has at least 40 test rows. At least five states must qualify.
- Temporal validation: train on all development observations and test 2008--
  2018 observations from counties seen in development. At least 50 test rows
  are required.
- For every split, remove training differences sharing either level-year
  endpoint with a test difference. Standardization and rank selection use
  training rows only. Solve by SVD and drop singular directions below
  `1e-10` times the largest singular value.

## Gates

For each crop/practice/fold comparison, material improvement means an RMSE
reduction of at least `max(0.0001, 0.01 * comparator RMSE)`.

- Seasonal PDSI passes only if `season_linear` materially improves on
  `trend_only` in every eligible state fold and in the terminal test.
- Within-season timing passes only if `stage_linear` materially improves on
  `season_linear` in every eligible state fold and in the terminal test.
- `season_quadratic` is reported but promoted over `season_linear` only under
  the same all-fold rule.
- Gates are evaluated separately by crop and practice. No pooling can conceal
  a crop/practice failure. Null, negative, or unstable improvements are
  reported plainly.

Only aggregate fold metrics and gate decisions are emitted. Coefficients and
row predictions are suppressed at this stage. Predictive success does not
authorize causal, irrigation-treatment, national-representativeness, future-
climate, damage, global-transfer, or SCC claims.
