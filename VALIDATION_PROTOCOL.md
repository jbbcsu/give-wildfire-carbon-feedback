# Empirical and validation protocol

## Estimation panel

Build a crop-season-grid-year panel for maize, rice, wheat, and soybean from
GDHY (1981–2016). Join daily ISIMIP3a climate and crop calendars before any
spatial aggregation. Partition by rain-fed/irrigated status where the data
support it. Exclude incomplete cross-year crop windows rather than filling
them silently. Fit the pre-specified response with grid/crop fixed effects,
flexible year effects, stage weather features, and temperature--precipitation
interactions. Record all changes as secondary specifications.

## Three adaptation scenarios

`fixed` applies the observed response unchanged. `trend` and `upper` use the
transparent effectiveness schedules in `config/adaptation_scenarios.toml`.
They are stress-test scenarios, not empirical forecasts. Until a cost model is
estimated, all use zero `adaptation_cost_share`; report this limitation and do
not call the resulting SCC net of adaptation investment.

## Required comparisons

1. Seasonal precipitation-only, stage-feature, and joint temperature--water
   specifications must be compared by blocked space, time, and extreme-year
   holdouts.
   This comparison must include the direct precipitation-pattern, climatic
   water-balance (SPEI/PDSI), and soil-moisture exposure families defined in
   [the drought metrics plan](DROUGHT_METRICS_PLAN.md). PDSI/SPEI are competing
   drought representations, not covariates to stack mechanically with their
   underlying precipitation/temperature inputs.
2. Compare predicted yield changes to GGCMI/ISIMIP process ensemble ranges;
   disagreement is structural uncertainty, not grounds to average blindly.
3. Use FAOSTAT only as an aggregation/provenance check because GDHY is partly
   calibrated to it. Seek a genuinely independent subnational source for a
   formal external validation. The U.S. county extension supplies this layer:
   compare calendar-aligned crop-area-weighted climate drought measures with
   observed U.S. Drought Monitor county-week D1+ and severity-area exposures,
   then assess their incremental and non-duplicative predictive role for
   documented NASS crop yields. It is a historical validation test, not a
   projected SCC input.
4. Refit with an alternate weather product/bias correction and alternate crop
   calendar; retain uncertainty from both.
5. Require zero climate features to give zero loss, matched pulse/base
   climate draw IDs, nonzero pulse-minus-base precipitation features, and a
   one-for-one test that `JointAgriculture.agcost` replaces—not augments—the
   agricultural input to SCC. Assert that crop-value shares are nonnegative,
   fixed across paired climate paths, and sum to the complete agricultural
   value pool in every region; partial-coverage mode is diagnostic-only.

The ISIMIP/GDHY coordinate transformation is an explicit validation gate:
ISIMIP longitude is −180–180° with descending latitude, while GDHY longitude
is 0–360° with ascending latitude. Normalize longitudes before an exact
0.5-degree-centre join, and fail rather than interpolate if coordinates differ.

## ML gate

An LSTM/temporal-fusion model may proceed only if it improves calibrated
out-of-sample predictions versus the fixed-effects and gradient-boosted
benchmarks in held-out regions, years, and extremes; respects crop-stage
inputs and physical sign/shape constraints; and produces stable pulse
responses with precipitation altered while temperature and CO2 are fixed.
It is a comparator/emulator, not the primary causal estimator.

## Pilot-estimation boundary

The repository includes a grid/year fixed-effects pilot script only to test
data joins, dimensionality, and reproducibility. Its in-sample coefficients
are never inputs to `JointAgriculture` or SCC. The main analysis requires the
full global panel, crop-stage features, pre-specified nonlinear terms,
spatial/temporal holdouts, coefficient uncertainty, and welfare mapping.

## Executable holdout construction

`scripts/make_validation_folds.py` assigns deterministic 5° spatial-block
folds, reserves the final two harvest years, and labels grid-relative upper
tail dry-spell/heavy-rain cases from climate features only. It never reads or
uses `yield_t_ha` to select a holdout. The fixed seed and all thresholds are
stored in the output panel. These labels are a required evaluation layer, not
a claim that the tail definitions exhaust agricultural extremes.
