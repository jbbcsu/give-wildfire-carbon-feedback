# U.S. source-matched crop response: prospective exploratory contract

Registered September 8, 2026, before regional feature completion or any fit
under this contract. New work; old completed analyses and source contracts are
unchanged. This contract authorizes historical association diagnostics only.
No causal, national-representative, counterclim yield, damage, welfare, or SCC
claims or coefficient export to production are authorized.

## Question and finite next stage

How sensitive is the estimated precipitation–yield association to the daily
weather source, holding actual NASS outcomes and the estimation sample fixed?
Fit GSWP factual and nClimGrid separately. This is a source-robustness bridge
toward a later climate-response study, not that study's validation certificate.
No counterclim weather or future outcomes enter estimation or model selection.
See `PRECIPITATION_LITERATURE_UPDATE_20260908.md` for the literature rationale.

## Required inputs and immutable lineage

1. Require regional construction status `us_regional_county_climate_inputs_validated`
   and comparison status `us_regional_county_climate_comparison_validated` in
   `data/interim/us_regional_county_climate_20260908/`. Verify receipt/product
   hashes, exact source identities, physical checks and both 573-row pilot
   parities. Bind the completed artifacts in a new input manifest before
   fitting. They do not yet exist at registration; do not invent their hashes.
2. Use the original direct-practice panel and validated heat panel:
   `data/interim/us_county/nass_direct_practice_nclimgrid_1981_2019.parquet`,
   SHA256 `205a94ae92c12810026c9c5d0ac0fa3760e46ebc39669e528ba20a125a0c46d7`;
   `data/interim/us_county/nass_direct_practice_daily_heat_1981_2019.parquet`,
   SHA256 `380735986e48291c092b83b588bf0a96b335bccf632bff033988795338ffe4df`.
   Validate their existing source receipts, outcome IDs and calendar roles.
3. Pin regional builder SHA256
   `f2d9bd21dd3c0cee265f97ee3a7af4c6efb3931d4cea9cc5baaeb6db250e80b7`
   and comparator SHA256
   `dd78be99cfa36e528f68ad1ee563011e6dcea68ab80576242221cd2180539262`.
   If a genuine bug requires a change, document the amendment and rerun affected
   validation before binding inputs; never accept a stale receipt silently.

## Sample and outcomes

Years 1982–2010; corn grain and soybeans; directly reported non-irrigated and
irrigated yields, in bushels/acre, modeled as log yield. Preserve county/crop/
practice/year keys and paired-practice availability from the original panel.
No imputation, outcome winsorization, yield-based geography selection, or new
NASS query. Use only whole counties with finite daily coverage under the
registered regional construction. Report excluded counties/years by crop and
reason; this selection is not representative of the country.

Join factual GSWP weather by county/crop/year, many-to-one; exact NASS usual
dates, season length and both-practice weather equality must survive. Assert
that replacing weather changes neither yields nor outcome keys. No centroid
weather and no implied practice-specific field mask: these are whole-county
exposures using fixed NASS calendars, not measured irrigation water delivery.

Primary cross-source comparison uses identical finite rows with positive
seasonal precipitation in BOTH factual products, so amount and timing models
share the same sample. Report zero-rain exclusions. If those exclusions exist,
also estimate quantity-only on all otherwise eligible finite rows as a named
sample sensitivity; zero rainfall itself is not an invalid quantity.
Counterclim zero-rain flags do NOT determine this historical fitting sample.
Retain minimum 500 rows and 25 counties in EACH crop/practice fit. Fail and
report unsupported groups; never pool groups or reduce gates to get a result.

## Fixed model specification

For each weather source, crop and practice separately:

- County and state-by-harvest-year fixed effects; equal observation weights.
- Primary moisture basis: P/100 and (P/100)^2, P in millimetres.
- Controls: all three stage mean temperatures, stage Tmax exceedance degree-
  days and counts of days above threshold, each linear and squared. Primary
  threshold 29 C for corn, 30 C for soy; the other threshold is a separately
  reported sensitivity, not selected by significance. Same threshold in both
  sources for each comparison.
- Incremental timing candidate: stage 1 and stage 2 precipitation shares,
  linear, with stage 3 omitted. This is a restricted timing test, not a claim
  to exhaust dry spells, Rx5 or sequence dynamics. Quantity remains primary.
- No new interactions, splines, ML hyperparameter search or drought terms in
  this finite stage. Existing scPDSI evidence remains a competing-moisture
  benchmark; no matched paired drought index has been constructed.

This yields 32 scheduled fits: two sources x two crops x two practices x two
forms x two thresholds. At most eight additional primary-threshold quantity
fits are needed only when the positive-rain restriction changes the sample.
Save all attempted fits, failures and diagnostic denominators, not only
significant results. Do not use counterclim predictions as a fit-selection
criterion. No production-promotion decision is made by these fits.

## Numerical checks and reporting

Use tested alternating fixed-effect residualization (tolerance 1e-10,
maximum 1000 iterations), within-column SD floor 1e-10 and scaled QR with
condition-number ceiling 1e8. Transform nonlinear regressors BEFORE
residualization. Pin helper/code hashes; independent synthetic checks must
cover exact keys, weather replacement, known coefficients, rank failure and
rejection of counterclim-as-training data before the real run.

Reuse the explicitly labeled county-cluster sandwich convention of the prior
QR benchmark for comparability; report its finite-sample correction and that
it does not account for all absorbed fixed-effect degrees of freedom or
cross-county residual dependence. Its normal-approximation intervals are
diagnostic, not calibrated causal uncertainty. Do not compare source-specific
confidence-interval overlap as a statistical test of coefficient differences.
Any formal paired source-difference interval needs a separately specified
joint resampling/influence calculation, not independent-error arithmetic.

Report precipitation coefficients, all controls, convergence/rank diagnostics,
sample coverage and within-fit residual RMSE. RMSE here is IN-SAMPLE, not
out-of-sample performance or evidence to promote timing. Curves/contrasts, if
subsequently computed, must state identical reference rainfall and source-
specific support; do not silently compare slopes at different source quantiles
or label old unsupported +100 mm contrasts supported. Keep row predictions
and covariance artifacts in ignored output directories, not production.

## Validation and transport boundaries

1982–2010 overlaps the inspected historical data; no untouched holdout is
claimed. Existing 2012–2019 validation was also reused. This source sensitivity
cannot create a new independent test set. Blocked validation must be separately
frozen before the next candidate evaluation, with this reuse disclosed; future
unseen years require actual matched new weather/outcome preparation.

Fitting with GSWP removes one direct source mismatch but does not eliminate
weather measurement error, omitted drivers, reporting selection, spatial
dependence, adaptation confounding or global transfer uncertainty. Historical
weather associations cannot identify CO2 fertilization or long-run adaptation.
The difference between irrigation regressions is not an irrigation treatment
effect. ATTRICI historical trend removal is not an anthropogenic forcing or
GIVE marginal-pulse experiment. Counterclim yield contrasts remain outside
this contract until a separate justified response/support design is reviewed.

## Execution and handoff

Do not run tests or estimation alongside the active regional acquisition/
construction chain. Once it completes, review climate outputs, create the
input-binding manifest, implement the separate estimator and run tests, then
run this finite association stage immediately if checks pass. Use one numeric
thread, 1024 MiB sampled RSS, 64 MiB owned output/scratch and 130 GiB free-space
floor. Preserve failures and prior outputs. No new user decision or download
approval is required for this already-authorized diagnostic work.
