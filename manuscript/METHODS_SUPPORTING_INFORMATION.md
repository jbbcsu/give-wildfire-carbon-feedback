# Methods Supporting Information

## S1. Reproducibility scope

This document specifies a reproducible replacement for the temperature-only
agriculture pathway in GIVE. Raw data are excluded from Git; exact records are
stored in `data/provenance/`. The project has no wildfire inputs or code
dependencies.

## S2. Data acquisition and provenance

The outcome panel uses GDHY v1.2/v1.3 (Iizumi and Sakai, 2020), with the
downloaded archive checksum in its TOML record. Daily historical climate uses
ISIMIP3a GSWP3-W5E5; projections use ISIMIP3b CMIP6 bias-adjusted daily
fields. Crop calendars use GGCMI Phase 3 2015soc files (DOI
10.5281/zenodo.5062513). Capture the ISIMIP API response, file version,
license/terms, SHA-512, retrieval date, and URL for every file. Climate files
are multi-gigabyte global arrays and must be streamed/chunked; do not commit
them. See `data/input_manifest.csv`.

The U.S. validation outcome source is the dated USDA NASS Quick Stats crops
bulk snapshot `qs.crops_20260821.txt.gz`. Acquisition pins the declared byte
length, ETag, and last-modified value; downloads verified HTTP ranges and
refuses to continue a partial file if source identity changes; and records a
streaming SHA-512 only after completion. Raw records and the acquisition
sidecar are excluded from Git. Commodity, practice, geography, unit, and
suppression filters are fixed only after schema inspection and are recorded in
the processed-panel manifest.

## S3. Crop-year alignment

For every grid cell, crop, season, irrigation regime, and harvest year, read
planting and harvest dates from the selected calendar. Resolve cross-year
seasons explicitly and retain date/coverage flags. The current executable
pipeline partitions each valid season into transparent 0–30%, 30–70%, and
70–100% temporal windows; these are **not** claimed phenological stages. The
main specification will replace them with crop-specific establishment,
vegetative, reproductive, and maturity dates only after a licensed, globally
consistent phenology source is selected. Exclude unrecoverable incomplete
windows. No annual country precipitation may be used to stand in for stage
weather.

## S4. Climate features

### S4.1 Climate-to-precipitation projection

The project does not claim or train a new free-standing precipitation
emulator. Direct daily ISIMIP/CMIP fields are the reference. Candidate fast
projection chains are evaluated against those fields with entire ESMs and
scenarios held out. The current published-method candidate combines a
MESMER-M-TP monthly response with a published daily occurrence/amount weather
generator; STITCHES supplies a sequence-preserving benchmark and MESMER-X an
independent Rx1day benchmark. RIG (Huang et al., 2026 preprint) is the closest
known joint daily global temperature--precipitation system under flexible
radiative forcing, but is not executable as of 22 August 2026 because its
authors state that code will be released upon publication. ACE2-SOM is a
high-complexity robustness model rather than the default.

Every candidate must reproduce crop-calendar totals, early/middle/late or
phenological-stage shares, wet-day frequency, consecutive dry days, Rx1day,
Rx5day, heat--precipitation dependence, and spatially synchronized crop-region
events. For SCC use, paired base/pulse runs share stochastic innovations and
must show stable, convergent feature differences as pulse size is reduced.
Aggregate growing-season precipitation results are additionally benchmarked
against OSCAR-crop v1.0; that published model does not validate daily timing
or extreme-weather effects.

For each stage, calculate mean temperature; precipitation total; wet-day
count; maximum consecutive dry days; Rx1day and Rx5day; and, after a specified
method, water balance. Calculate maximum-temperature days and degree-days only
for explicitly registered crop/specification thresholds. Stage heat-day and
degree-day totals must reconcile additively to the season; the stage-day-
weighted maximum-temperature mean must reconcile to the seasonal mean.
For every adjacent ordered threshold pair, require weakly decreasing hot-day
counts and require the degree-day difference to lie between the threshold gap
times the hotter-day and cooler-day counts. These algebraic checks detect
corrupt summaries but do not choose a response threshold. Convert
precipitation flux to mm/day using source time
bounds. Define thresholds and anomalies relative to a fixed historical
grid-crop-stage baseline. Store units, baseline interval, input version, and
missing-data flags. Compute nonlinear metrics before geographic aggregation.
The direct precipitation-pattern family is the primary attribution measure.
SPEI/PDSI-like climatic-water-balance and soil-moisture families are competing
drought representations, not terms automatically stacked with the underlying
precipitation and temperature variables. For every future paired climate draw,
calculate the corresponding drought-index change directly, then use a
pre-specified symmetric decomposition when a precipitation versus
temperature/PET attribution is required.

For the historical climatic-index benchmark, monthly CRU scPDSI is aligned to
the same crop-year windows by day-weighting each monthly value over its exact
overlap with a stage. Retain stage mean, minimum, days at or below the
registered threshold, the threshold itself, and covered-day count. Require
exact grid-centre correspondence after longitude normalization, complete
monthly coverage for every stage, and a covered-day count equal to stage
length. This benchmark tests historical response and coverage only; future
SCC runs must derive their drought indices from matched baseline and pulse
climate paths and must not project observed CRU scPDSI.

## S5. Estimation

Fit the primary response on crop-grid-year observations with grid/crop fixed
effects, flexible year effects, stage temperature and precipitation-pattern
terms, and temperature--precipitation interactions. Pre-register feature
selection and splines/thresholds. Pool crop seasons only with pre-specified
crop interactions or a hierarchical partial-pooling structure; a combined
panel is never authority to impose common weather slopes across maize, rice,
wheat, and soybean. Cluster or model spatial dependence. Include
irrigation/crop strata where coverage permits. The outcome file is matched to
the calendar at the crop-season level according to the locked crosswalk in
`data/provenance/crop_calendar_gdhy_crosswalk.md`; generic GDHY aggregate
directories are not substitutes for an identified season. GDHY does not
identify irrigated and rainfed yields separately, so the historical pilot uses
rainfed-calendar exposure only and does not estimate an irrigation-stratified
response or aggregate both calendar regimes. A production specification needs
a compatible irrigated outcome/area treatment before representing irrigated
production. Specifically, when both calendar regimes are available, an
independent pre-period crop-grid area-share source must weight their climate
features into one exposure vector for the single GDHY crop-season-grid-year
outcome. Shares are fixed across outcome years, cover every declared regime,
and sum to one. Missing shares or exposure rows are not renormalized, and the
same observed yield is never entered as separate rainfed and irrigated
observations. This historical exposure-allocation weight is distinct from the
regional baseline crop-value weights used later for welfare aggregation. CO2
is an explicitly provenanced scenario term; it cannot be separately added
after a response that already includes it.

## S6. Adaptation

`fixed` keeps the observed response. `trend` and `upper` apply transparent,
crop-specific time-varying loss multipliers from
`config/adaptation_scenarios.toml` before crop aggregation; they are
sensitivity scenarios, not claims of forecasted adaptation. Adaptation cost
shares default to zero pending empirical cost estimation and are reported as a
limitation. Positive crop losses are attenuated; modeled benefits are not
erased.

## S7. Model integration and SCC

The isolated `CropResponseAggregation` component retains crop/season-specific
features and coefficients through response evaluation. It accepts exactly one
declared water-stress family, applies crop-specific adaptation, and aggregates
with fixed baseline agricultural-value shares. Production runs require those
shares to cover the complete regional agricultural value pool; partial-
coverage runs are diagnostics and cannot produce an SCC. `JointAgriculture`
then retains baseline income, population, agricultural-share, and 16-FUND-
region inputs and outputs `agcost` in billion 2005 USD/year. It replaces
`MooreAg.Agriculture`; never instantiate both. Matched baseline/pulse climate
paths propagate through the crop-specific joint response and one welfare
mapping. The global SCC is calculated from the discounted difference using
GIVE's established marginal-damage method.

The executable integration gate inspects Mimi's parameter-connection graph
before each paired marginal run. It requires exactly one internal producer for
`DamageAggregator.damage_ag`, identifies that producer as
`JointAgriculture.agcost`, and rejects an instantiated component named
`Agriculture`. Synthetic tests retain missing-source, wrong-source, and
coexistence failures. The unmodified GIVE model is a negative control and is
rejected because `Agriculture.agcost` supplies `damage_ag`. This establishes a
topological accounting condition only; it does not validate response skill,
welfare calibration, crop coverage, future support, matched identifiers, or a
paired SCC result.

The executable installer preflights the legacy agriculture component, the
regional population/GDP aggregators, baseline agricultural-value inputs, crop
order, and component start year before mutation. It then deletes the MooreAg
component and its unshared parameters, adds `CropResponseAggregation` and
`JointAgriculture`, reconnects the socioeconomic inputs and `damage_ag`, and
sets the declared sector flags explicitly. An executed control applies this
procedure to the unmodified GIVE model using synthetic zero-response inputs.
All externally supplied response and adaptation arrays use GIVE's full
1750--2300 time dimension even though the installed components begin in 2020;
the pre-2020 rows are not evaluated by those components. For every active year,
the control requires complete crop and regional outputs, unit crop-value
coverage, and zero `JointAgriculture.agcost` and aggregated agriculture damage.
It is not a paired marginal experiment or an empirical damage result.

The paired component-output gate is applied after the crop response and
agriculture replacement components execute. For crop-level raw and adapted
loss arrays and regional loss and monetary agriculture arrays, it requires
matched dimensions, finite numeric values, and equality before the registered
first-divergence year. The modeled horizon must contain at least one year
before and at/after that year. A separately declared zero-pulse control must
agree for every modeled year. The gate does not require a nonzero response to
a nonzero pulse and therefore does not turn an integration check into an
implicit statistical-significance or extrapolation rule.

Before model wiring, the long-form response bundle is checked against the
frozen crop and FUND-region orders. Every draw/year contains the complete
region-by-crop product for baseline and pulse; FAIR, climate-member,
socioeconomic, calendar, response, adaptation, weight, and welfare identifiers
match within each pair; coefficients and adaptation settings match; weights
sum to one and remain fixed across scenario and time within a draw; and all
features are identical before the registered first-divergence year. Historical
support flags remain scenario-specific. This is a schema/conservation gate,
not evidence that a response clears empirical validation.

## S8. Uncertainty and sensitivity

Jointly sample climate model/member/scenario, weather product/bias adjustment,
crop calendar, response coefficients, crop-model structural benchmark,
socioeconomics, adaptation, welfare mapping, and discounting. Report
distributions and variance/decomposition diagnostics, not only means.

## S9. Validation and exclusion checks

Require held-out space, time, and extreme-year validation; calendar/date and
coordinate checks; coverage/no-infill checks; nonnegative precipitation and
integer-count checks; zero-feature/zero-loss tests; regional-weight
normalization; and matched draw IDs for pulse/base. FAOSTAT is an aggregation
check, not independent external validation of GDHY. The U.S. county extension
uses documented NASS yields and U.S. Drought Monitor county-week area shares
as an external observed validation layer, after an explicit crop-calendar and
crop-area-weighting choice; it is not a source of global future climate
features. County yield is not labeled rainfed without crop-specific irrigated
area evidence: the primary sample applies a predeclared high-rainfed-share
threshold, reports nearby thresholds, and treats mixed counties separately.
USDM county-week preparation preserves five-digit GEOIDs, rejects duplicate
keys and category shares that do not sum to 100, and requires each map date to
fall inside its declared validity interval. A documented state/crop/harvest-
year calendar then clips the weekly validity intervals to each crop season and
calculates day-weighted category shares, severity-area means, and D0+/D1+/D2+
area-equivalent days. Missing, gapped, or overlapping daily coverage fails;
planting and harvest dates are never inferred. The output remains explicitly
historical-validation-only and is not a future climate or SCC input. Before
constructing any estimation panel, a counts-only county-year coverage audit
requires an explicit NASS-commodity-to-calendar-crop mapping, a single yield
unit, unique keys, and the validation-only/SCC-ineligible exposure labels. It
retains suppressed NASS outcomes in the coverage denominator, reports overlap
for reported yields separately, and emits no yield values or response estimate.
Keep crop inundation in agriculture and exclude it from the future
infrastructure module; exclude coastal surge/SLR impacts already addressed by
CIAM.

The executable internal predictive comparison uses only outcome-independent
holdout labels. Within each crop, consecutive-year differences in log yield
are regressed on corresponding weather-feature differences, eliminating
time-invariant grid productivity. Seasonal precipitation-only, seasonal
temperature--precipitation, and three-window joint specifications are scored
on leave-one-spatial-fold-out predictions, the registered final-year block,
and pairs containing a registered climate-extreme endpoint. RMSE, MAE,
correlation, predictive R-squared, and improvement over a zero-yield-change
benchmark are reported; response coefficients are not exported. This is an
internal predictive diagnostic, not causal identification, independent
external validation, or authority to construct SCC inputs.

Multi-crop audit reporting is fail-closed. The audit validator binds the JSON
artifact to the SHA-256 of the frozen response specification; requires the
explicitly declared crop-season set and every crop-by-model-by-holdout result;
checks positive and reconciled level, observed, pair, split, and spatial-fold
row counts; requires finite metrics and design diagnostics; and independently
recomputes improvement over the common zero-change benchmark. It emits a
machine-readable diagnostic summary while labeling any lowest-RMSE model as
descriptive only. Missing crops, duplicate results, stale configurations,
inconsistent benchmark values, nonfinite metrics, and failed arithmetic stop
the reporting workflow.

## S10. Scientific integrity and independent review

Every quantitative statement is classified as observed source data, derived
empirical result, published result, synthetic test, diagnostic pilot,
assumption/scenario, or unavailable/planned. Missing or failed inputs and
analyses are reported rather than replaced by inferred values. Numerical
damage or SCC results require complete provenance, a frozen executable
configuration, machine-readable draw artifacts, holdout validation,
pulse-convergence and accounting checks, and explicit promotion in
`RESULTS_STATUS.md`. The full rules are in
`SCIENTIFIC_INTEGRITY_PROTOCOL.md`; `INDEPENDENT_REVIEW_CHECKLIST.md` defines
the adversarial replication handoff.
