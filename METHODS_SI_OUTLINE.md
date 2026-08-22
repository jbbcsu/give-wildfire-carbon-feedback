# Methods Supporting Information blueprint

This outline is a reproducibility contract. Bracketed fields are completion items, not values to infer during manuscript drafting. Every derived dataset, model fit, figure, and SCC draw must be generated from the isolated `precipitation_scc` repository and a manifest entry.

## S1. Study design and preregistration

* State the main estimand, eligible crops, geographical support, historical period, baseline, welfare unit, and main/adaptive scenarios.
* Freeze the replacement rule: crop-specific responses pass through `CropResponseAggregation`; `JointAgriculture.agcost` then replaces the agriculture input otherwise supplied by MooreAg and is not additive.
* Declare outcome-blind choices: crop-stage definitions, primary feature set, transformations, model formula, minimum coverage, and skill gates.
* Define primary, secondary, exploratory, and failed specifications before SCC projections.

## S2. Data acquisition, permissions, and archival

For every input provide a manifest row and a machine-readable companion with release/DOI, URL/retrieval command, license/terms, access date, temporal/spatial coverage, units, raw and derived checksums, and intended use.

| Input | Additional required fields |
|---|---|
| GDHY yields | Crop-year interpretation, grid, missing values, calibration dependency |
| Crop calendars/irrigation/harvest weights | Calendar-year convention, multi-season treatment, crosswalk |
| Historical daily weather | Variables, regridding, quality control |
| ISIMIP daily climate | Experiment, GCM/member, forcing/bias-adjustment version, scenario, calendar |
| GGCMI/ISIMIP benchmark | Protocol, GCM/GGCM/CO2/water-management combinations, output units |
| Socioeconomic/welfare inputs | GIVE/GTAP release, currency year, FUND mapping |

List nonredistributable files and scripted retrieval instructions. Never package credentials, restricted data, or wildfire artifacts.

## S3. Harmonization and crop-season panel

1. Document coordinates, land mask, grid alignment, units, leap days/calendars, and cell-area/harvested-area weights.
2. Specify crop/season eligibility, rain-fed versus irrigated treatment, planting/harvest construction, and cross-year seasons.
3. Give pseudocode joining daily climate to each crop-season-grid-year; exclude partial seasons by declared rule.
4. Detail cell/crop to FUND aggregation; predictions must precede aggregation unless explicitly tested otherwise.
   Until a crop-specific phenology source is introduced, stage construction is a
   pre-specified fractional-season proxy (0–30%, 30–70%, 70–100%), explicitly
   reported as such rather than as observed phenology.
5. Report observation counts at every exclusion/filtering stage.

## S4. Daily feature definitions

Give exact formula, unit, threshold/percentile baseline, and stage aggregation for: crop-stage temperature anomaly; precipitation/water-balance anomaly; longest dry-day run; wet-day frequency; and stage-specific heavy-rain/water-excess measure. State reference-ET, VPD, radiation, CO2, and compound-event treatment. Include tests for dates, thresholds, anomalies, weights, and zero change.

## S5. Historical response estimation

Provide the complete outcome transformation and equation: fixed effects, interactions, crop/irrigation pooling, splines/knots, weights, sampling, regularization, and spatial-correlation/uncertainty method. Explain treatment of management trend and residual confounding. Keep temperature, CO2, radiation/VPD, and precipitation in one model.

Report coefficients/posteriors, support/correlation diagnostics, selection path, residuals, leverage rules, and failure criteria. Mark projections outside observed support as extrapolation.

## S6. Adaptation and CO2 fertilization

Reproduce `config/adaptation_scenarios.toml` exactly: formulas, values, dates, caps, and zero adaptation-cost assumption. Label fixed, trend, and upper as sensitivity schedules. State crop-model CO2 treatment and whether the estimator includes a CO2 proxy. Test that CO2-only changes are never described as precipitation attribution.

## S7. Climate projections and counterfactuals

Describe climate model/member/scenario selection, ISIMIP3BASD bias adjustment where used, crop-calendar feature construction, and scenario-to-GIVE/FAIR alignment. Retain spatial dependence by jointly sampling members. Record matched baseline/pulse IDs for FAIR, climate member, SSP, response draw, and adaptation draw. Define pulse timing/mass and show no-pulse/zero-warming conservation tests.

## S8. Welfare translation and GIVE integration

Specify the yield-to-welfare mechanism: GTAP-compatible mapping, emulator, or other layer. Demonstrate price/trade feedback enters once. Document fixed baseline crop-value shares, their full agricultural coverage or an explicit gap model, currency, FUND crosswalk, consumption, discounting, and SCC algorithm. Include wiring/schema/units and automated tests that crop-specific coefficients survive aggregation, incomplete coverage fails by default, and `agcost` replaces rather than augments MooreAg.

## S9. Attribution and overlap audit

Define joint-effect and precipitation-attribution decomposition, including feature groups/order averaging. Publish a reconciliation table: MooreAg excluded; CIAM retained for coastal effects; standard mortality/energy sectors retained subject to scope; optional aggregate damage functions disabled; noncoastal infrastructure flood excluded. Call this an accounting rule, not proof that overlap is zero.

## S10. Validation and benchmarks

* Spatial-blocked, temporal, and extreme-year holdouts.
* Errors/skill relative to named baseline, calibration/coverage, bias by yield/region, and response-shape stability.
* GGCMI/ISIMIP comparison with configuration matching; interpret as structural benchmark.
* Alternate weather, calendar, feature, and aggregation robustness.
* ML comparator protocol: distributed-lag fixed effects and gradient boosting precede LSTM/temporal fusion; ML proceeds only if it clears holdout and physical/counterfactual gates.

## S11. Uncertainty and sensitivity

Document distributions, draws, seeds, correlations, and IDs for climate, weather/bias correction, crop calendar, coefficients, CO2 treatment, adaptation, socioeconomic pathway, welfare mapping, and discounting. Report paired-draw uncertainty, leave-one-GCM-out, variance decomposition, upper-tail diagnostics, and extrapolation share. Do not independently resample regional climate patterns if that breaks spatial covariance.

## S12. Reproducibility package

Document directory tree, platforms, Julia/Python/R versions, lockfiles, environment creation, data retrieval, pipeline/test commands, runtime/memory expectations, frozen config IDs, and artifact checksums. Release synthetic/minimal fixtures so tests run without restricted raw data.

## SI figures and tables

* Figures S1–S3: coverage, calendar/crosswalk diagnostics, missingness.
* Figures S4–S7: feature distributions and observed support.
* Figures S8–S11: response/holdout/calibration/residual diagnostics.
* Figures S12–S15: process-model, alternate-input, and ML comparator results.
* Figures S16–S20: all SCC robustness, uncertainty, and attribution results.
* Tables S1–S3: source/provenance/license/checksum register.
* Tables S4–S6: variables, units, formulae, parameters/priors.
* Tables S7–S10: performance, regional impacts, SCC draws, exclusions.
