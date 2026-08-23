# Empirical and validation protocol

## Estimation panel

Build a crop-season-grid-year panel for maize, rice, wheat, and soybean from
GDHY (1981–2016). Join daily ISIMIP3a climate and crop calendars before any
spatial aggregation. Partition by rain-fed/irrigated status where the data
support it. Exclude incomplete cross-year crop windows rather than filling
them silently. Fit the pre-specified response with grid/crop fixed effects,
flexible year effects, stage weather features, and temperature--precipitation
interactions. Record all changes as secondary specifications.
Daily-maximum heat features must use the identical calendar and stage
boundaries as precipitation features. For every registered threshold, stage
heat-day counts and degree-days must sum to their season-level values, while
the stage-day-weighted maximum-temperature mean must equal the seasonal mean.
Across ordered thresholds, hotter-day counts must be weakly decreasing and
the difference in degree-day totals must remain within the necessary bounds
implied by the two day counts and threshold gap. These nesting checks apply to
both seasonal and stage partitions and do not select a production threshold.
Historical monthly scPDSI benchmark features use the same crop windows,
day-weight monthly values across partial months, and require index coverage to
equal every stage length. Coordinate normalization may reorder exact grid
centres but must fail instead of spatially interpolating. Preserve its
historical-benchmark-only role through the join; it cannot be used as a future
baseline/pulse feature.

Because GDHY contains one aggregate yield per crop-season-grid-year, rainfed
and irrigated calendar exposures cannot be treated as two independent outcome
observations. Before a production all-area panel is built, obtain a versioned
crop-grid irrigated/rainfed area-share source that is independent of GDHY
yield, fixed to a documented pre-period baseline, and complete for every
included crop-grid. Collapse the regime-specific climate features to one
area-weighted exposure row per observed outcome. Shares must be finite,
nonnegative, invariant across outcome years, and sum to one; missing regime
features or weights fail rather than trigger renormalization. Retain the
rainfed-calendar-only panel as an explicitly narrowed diagnostic until that
gate clears. `scripts/allocate_outcome_exposures.py` enforces the data
contract but supplies no production weights.

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
   Run the paired response-bundle validator before integration. Its schema
   pass does not substitute for held-out skill, observed-support, or welfare
   validation.
   Run `AgricultureReplacementAudit.audit_agriculture_replacement` on the
   constructed Mimi model before either member of a paired SCC run. The audit
   must find exactly one internal producer for `DamageAggregator.damage_ag`,
   identify it as `JointAgriculture.agcost`, and find no instantiated
   `Agriculture` component. The unmodified GIVE graph must fail this test and
   serves as a negative control. A graph pass is necessary but not sufficient
   for SCC authorization.
   Run `scripts/test_give_replacement_harness.jl` against the unmodified GIVE
   repository as a build-only positive control. It must delete the legacy
   component, retain the RFF socioeconomic aggregators and declared sector
   flags, pass the graph audit, and build with synthetic zero-response arrays.
   Supply feature and adaptation arrays on GIVE's complete model time axis;
   component `first=2020` does not shorten Mimi's external parameter arrays.
7. After the crop-response and replacement components run, require matched
   finite `(time, region, crop)` crop outputs and `(time, region)` regional
   outputs. Every required baseline/pulse output must agree before the
   registered first-divergence year. A separately declared zero-pulse control
   must agree across the complete horizon. Require at least one modeled year
   before and at/after divergence so conservation cannot pass vacuously. This
   component-output audit is not a substitute for a full GIVE paired marginal
   run, welfare calibration, or SCC reconciliation.

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

`scripts/evaluate_crop_response_models.py` turns those labels into a
crop-specific held-out predictive audit. It first-differences consecutive
observations within crop/irrigation/grid cells, compares the registered
seasonal precipitation-only, seasonal joint, and stage-joint feature sets,
and reports spatial-fold, final-year, and climate-extreme metrics against a
zero-change benchmark. The transformation removes time-invariant grid levels;
it does not establish causal identification or solve time-varying omitted
variables. Coefficients are deliberately omitted from its output and the
result cannot be used to populate an SCC response bundle.

Before reporting a multi-crop diagnostic, run
`scripts/validate_response_evaluation_audit.py` with every expected crop-season
label. It binds the result to the response-specification SHA-256, requires the
exact crop-by-model-by-holdout product, reconciles spatial-fold row counts, and
recomputes every improvement-over-zero identity. Partial or stale audits fail.
The emitted best-model fields are descriptive summaries of the frozen audit,
not permission to select a preferred SCC response.
