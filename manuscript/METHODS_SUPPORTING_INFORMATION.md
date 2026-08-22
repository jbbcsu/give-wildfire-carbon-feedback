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

For each stage, calculate mean temperature; precipitation total; wet-day
count; maximum consecutive dry days; Rx1day and Rx5day; and, after a specified
method, water balance. Convert precipitation flux to mm/day using source time
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
production. CO2 is an explicitly
provenanced scenario term; it cannot be separately added after a response that
already includes it.

## S6. Adaptation

`fixed` keeps the observed response. `trend` and `upper` apply transparent
time-varying loss multipliers from `config/adaptation_scenarios.toml`; they are
sensitivity scenarios, not claims of forecasted adaptation. Adaptation cost
shares default to zero pending empirical cost estimation and are reported as a
limitation. Positive damages are attenuated; modeled benefits are not erased.

## S7. Model integration and SCC

The isolated `JointAgriculture` component retains baseline income,
population, agricultural-share, and 16-FUND-region inputs and outputs
`agcost` in billion 2005 USD/year. It replaces `MooreAg.Agriculture`; never
instantiate both. Matched baseline/pulse climate paths propagate through the
joint response and one welfare mapping. The global SCC is calculated from the
discounted difference using GIVE's established marginal-damage method.

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
Keep crop inundation in agriculture and exclude it from the future
infrastructure module; exclude coastal surge/SLR impacts already addressed by
CIAM.
