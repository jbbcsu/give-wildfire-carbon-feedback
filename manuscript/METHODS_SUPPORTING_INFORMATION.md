# Methods Supporting Information

## S1. Reproducibility scope

This document specifies a reproducible replacement for the temperature-indexed
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
them. The tracked ISIMIP3a record now pins all 16 historical files by name,
URL, byte length, and SHA-512; the recursive verifier checks conventional and
nested historical/projection records. Daily builders accept only explicit
precipitation-flux/mm-per-day and Kelvin/Celsius unit sets and reject blank or
unknown units and nonpositive wet-day thresholds. See `data/input_manifest.csv`.

Fixed irrigation-exposure weights use MIRCA-OS v2 (March 2026) annual
irrigated and rainfed harvested-area maps. The source archive, CC-BY-4.0
license, HydroShare resource, byte length, MD5, and SHA-512 are pinned in
`data/provenance/mirca_os_v2_irrigation_shares.toml`. Use the publisher's
30-arcminute GeoTIFFs only after verifying one 360-by-720 EPSG:4326 grid,
0.5° cell centres, finite nonnegative hectares, unique crop/system/vintage
files, and unit-summing shares. Raw rasters and derived tables remain ignored.

The U.S. validation outcome source is the dated USDA NASS Quick Stats crops
bulk snapshot `qs.crops_20260821.txt.gz`. Acquisition pins the declared byte
length, ETag, and last-modified value; downloads verified HTTP ranges and
refuses to continue a partial file if source identity changes; and records a
streaming SHA-512 only after completion. Raw records and the acquisition
sidecar are excluded from Git. Commodity, practice, geography, unit, and
suppression filters are fixed only after schema inspection and are recorded in
the processed-panel manifest.

The executable county-input status gate records that the local bulk NASS
archive is still incomplete, while bounded credential-safe API acquisition is
operational. Exact 2018--2022 all-practice corn yields are acquired. A separate
all-years, all-classes screen acquired paired `IRRIGATED` and
`NON-IRRIGATED` yield series for corn, soybean, and wheat, plus exact
2012/2017/2022 Census irrigated and total harvested-acre records. The
practice-yield support is regional rather than national. The 2017 Census share
is the pre-outcome national selector, with 2012/2022 vintages as sensitivities;
missing or suppressed irrigated acreage is excluded, never zero-filled.
All API queries, counts, checksums, and coverage appear in
`data/provenance/nass_irrigation_practice_screen.toml`. No county response is
estimated until the full county-polygon primary exposure, CDL sensitivity,
daily primary/robustness weather coverage, complete calendars, geography
crosswalks, and predeclared validation records pass.

For 1981--2019, the fail-closed direct-practice builder requires positive
numeric yields for both practices in the same crop--county--year. It retains
7,079 corn, 4,845 soybean, and 9,672 all-classes-wheat pairs (43,192 long
rows). The 807 unique GEOIDs all match 2019 TIGER. Screening against pinned
official Census county-change pages flags eight counties for historical-
boundary resolution and two name/code-only reviews; absence from these
substantial-change pages is not interpreted as proof of boundary stability.

The primary U.S. weather candidate is NOAA NCEI nClimGrid-Daily v1.0.0.
`data/provenance/nclimgrid_daily_198101.toml` pins the January 1981 object to
59,955,310 bytes; `data/provenance/nclimgrid_daily_1981_cuming_smoke.toml`
pins the six May--October objects used in a bounded crop-season smoke. Each
record preserves live HTTP identity, SHA-512, embedded product version and
license statement, increasing 596-by-1,385 grid, exact chronology, and all
four required fields (`prcp`, `tmin`, `tmax`, and `tavg`) with units. Each date
denotes the 24-hour period ending in the early morning. NCEI notes that v1
inputs can change without a version bump; every monthly object is pinned
independently. The real Cuming construction is an exposure-engineering check,
not a response estimate or precipitation trend.

A complete bounded acquisition now records all 468 canonical monthly objects
for 1981--2019, totaling exactly 27,857,685,556 bytes (25.944 GiB). Before each
object entered the atomic local manifest, the utility required the frozen HTTP
identity and exact byte length, computed a local SHA-512, and validated the
NetCDF schema, four required fields, embedded product metadata, day-label
semantics, and exact daily date coverage. Every resume invocation revalidated
all already manifested objects; a changed upstream identity, local hash,
schema, or calendar failed closed. The raw files and working manifest remain
Git-ignored. These checks establish a reproducible historical-weather input,
not a county exposure, predictive relationship, causal response, or SCC term.

The first U.S. weather-file smoke is the official NKN annual gridMET 2018
precipitation object. `data/provenance/gridmet_pr_2018.toml` pins its mutable
direct URL to 65,031,749 bytes, a complete 365-day 2018 calendar, the decoded
585-by-1,386 grid, millimetre units, ETag, Last-Modified value, and SHA-512.
The publisher states that copyright and related rights are waived to the
extent possible but does not name an SPDX license, so the record uses
`NOASSERTION`; raw data remain gitignored. Any changed HTTP identity or local
hash fails closed. Because the publisher cautions that source changes create
inhomogeneities in gridMET precipitation, gridMET is a historical robustness
product here, not a stand-alone basis for precipitation intensity/frequency
trends. Timing and extreme-response conclusions require agreement across the
declared primary and robustness weather products.

The U.S. model comparison gives climatic-water-balance indices equal standing,
not an appendix-only role. Crop-calendar PDSI/scPDSI and leakage-safe SPEI at
pre-registered accumulation windows are evaluated as alternative moisture-
stress representations under the same county, temporal, and drought-severity
outer holdouts as the direct-weather reference. SPEI calibration parameters
are estimated in training data or a fixed predeclared historical period and
are never refit on holdouts. PDSI/SPEI specifications replace the direct
precipitation-water terms unless a separate attribution design is frozen;
their effects or damages are not added to direct-precipitation effects.
Irrigation-stratified reporting is required because an index derived from
meteorological supply does not observe applied irrigation water.
[Dai (2011)](https://doi.org/10.1029/2010JD015541) documents PDSI variants,
while [Vicente-Serrano, Begueria, and Lopez-Moreno
(2010)](https://doi.org/10.1175/2009JCLI2909.1) defines the multi-scalar SPEI
framework. [Kuwayama et al.
(2019)](https://doi.org/10.1093/ajae/aay037) supplies the primary U.S.
observed-drought agricultural benchmark. These sources support definitions and
comparison design, not transport of their estimated responses into the global
model.

The primary SPEI route is computed rather than imported. U.S. construction
uses the acquired nClimGrid-Daily `prcp`, `tmin`, and `tmax`; global
construction uses source-consistent ISIMIP3a GSWP3-W5E5 `pr`, `tasmin`, and
`tasmax`. Daily Hargreaves-Samani reference ET0 uses the FAO-56
extraterrestrial-radiation equations and
`Tmean=(Tmin+Tmax)/2`; it represents climatic evaporative demand, not actual
evapotranspiration, applied irrigation, or soil moisture. Complete daily
precipitation and ET0 are summed to calendar months, and right-aligned 1-, 3-,
and 6-month `P-ET0` balances are formed. For each scale, native grid cell, and
calendar month, a three-parameter log-logistic distribution is fit by unbiased
probability-weighted moments to the 30 observations in 1982--2011. Parameters
are frozen before the 2012 terminal block. Missing calibration months,
degenerate fits, nonfinite values, or unreported tail-probability clipping fail
closed. The three scales remain separate models and are never stacked or
selected by SCC magnitude.

NOAA's current nClimGrid-Monthly SPEI uses a declared 1895--2014 calibration
and Thornthwaite PET, so it overlaps the terminal period and is retained only
as a retrospective U.S. implementation check. SPEIbase 2.11 uses CRU TS 4.09,
FAO-56 Penman-Monteith PET, and the SPEI package, but its public generation
repository still documents version 2.10 and does not expose a verified v2.11
reference subset; it is a retrospective global PET/implementation check rather
than the primary terminal-score field. Crop-window means day-weight monthly
values over overlapping calendar days and are explicitly retrospective at
partial boundary months; a month-end-inside-window sensitivity avoids
post-window boundary weather at the cost of dropping partial months. Before
any outcome fit, a master intersection must make direct precipitation,
PDSI/scPDSI, and all three SPEI scales share identical outcomes, calendars,
controls, weights, split labels, and first-difference endpoints.

The fixed-calendar source is the exact checksummed USDA NASS 2010 *Field Crops
Usual Planting and Harvesting Dates* report. NASS defines published begin/end
dates as approximately 5/95 percent completion and most-active intervals as
approximately 15/85 percent completion. The selected engineering default uses
the floor midpoint of each most-active planting/harvest boundary; the broader
published begin-to-end envelope is a sensitivity. Final causal-model calendar
selection remains validation-dependent, and annual Crop Progress timing is a
realized-timing/adaptation sensitivity. All-classes wheat is never assigned one
generic calendar: winter, spring, and durum feature bases remain separate
until independent class-area shares exist.

The deterministic parser validates the pinned PDF hash before reading pages 9,
25, 33, and 34, preserves all eight published date boundaries and 2009 acreage
context for 130 state/crop rows, and rejects unexpected row counts or date
tokens. Expansion over 1981--2022 produces 10,920 unique rows for two calendar
roles, 42 states, and five crop classes. Cross-year planting is resolved
sequentially relative to the harvest year; all 3,696 cross-year rows and all
same-year rows pass season order, duration, fixed-month/day, and harvest-year
checks. This is deterministic exposure alignment, not observed annual timing.

The selected full-period primary route intersects audited Census county
polygons with nClimGrid cells in EPSG:5070 and applies the intersection-area
weights only after cell-level feature construction. It is labeled a county-
average proxy because it does not isolate crop pixels. The separate fixed-2017
CDL sensitivity uses official 30 m class pixels selected by center inclusion
in the county and mapped to nClimGrid cells. The acquired source reports class
0 as background while nodata is unset; class 0 is therefore excluded
explicitly. Corn (1), soybean (5), durum wheat (22), spring wheat (23), and
winter wheat (24) are distinct, and double-crop classes are not silently
pooled.

Both spatial routes require exact five-digit NASS GEOIDs, audited Census
county-change status, in-grid nClimGrid indices, area/coverage reconciliation,
weights summing to one, and false response/SCC authorization flags. Nonlinear
temporal/extreme/response bases are constructed at the weather-cell and
calendar-class level before either polygon or crop-pixel weighting. National
CDL coverage begins in 2008; a later fixed mask applied to 1981--2007 is an
explicit retrospective measurement sensitivity, not observed crop location.
That limitation is binding for paired all-classes wheat, which has no post-
2007 support; pooled wheat response estimation remains blocked.

The bounded real spatial smoke uses Cuming County, Nebraska (GEOID 31039).
The polygon route reconciles its EPSG:5070 area to TIGER `ALAND+AWATER` at
relative error (3.05\times10^{-8}), covers the county with 120 positive
nClimGrid intersections, and normalizes weights to one. The 2017 CDL window
contains 706,394 corn pixels (635,754,600 m2) and 582,110 soybean pixels
(523,899,000 m2); all selected pixels map into 120 nClimGrid cells per crop,
and the pixel-center county-area approximation differs from polygon area by
(1.71\times10^{-5}). May--October 1981 daily features were built cell-first
under both routes and joined to four real paired-practice NASS support rows.
The executable comparison covers 18 weather features and two crop-year keys;
its largest absolute relative route difference is 0.00762. This is a one-
county/year spatial-measurement diagnostic only. It neither estimates a
climate--yield relationship nor establishes general equivalence of the routes.

### U.S. national corn/soy construction and predictive protocol

The registered direct-practice comparison contains 419 counties in 11 states,
11,861 unique crop--county--years (7,016 corn and 4,845 soybean), and 23,722
practice rows. One weather exposure is duplicated exactly across the distinct
irrigated and non-irrigated outcomes; applied irrigation water is not inferred
from nClimGrid. A fixed validity mask excludes cells that are nonfinite for any
of the four required fields on any day of January 1981 before county weights
are normalized. Of the 419 counties, 30 have at least one masked intersection.
The minimum valid/full-legal-polygon fraction is 0.529533 in a water-rich
county, but the minimum valid-area/TIGER-declared-land fraction is 0.983710;
all counties therefore pass the locked 0.95 declared-land gate. The 419
atomic county partitions contain 79,355 positive valid intersections.

For each cell and fixed state/crop calendar, the national builder constructs
seasonal precipitation total; 0--30%, 30--70%, and 70--100% precipitation
shares; timing centroid and concentration; wet-day frequency conditional on a
1 mm threshold; conditional wet-day intensity; maximum consecutive dry days;
Rx1day and Rx5day; and seasonal/stage temperature summaries. These nonlinear
bases are formed before county weighting. One atomic feature partition and
source-bound receipt is written per harvest year. All 39 partitions for
1981--2019 pass raw-month identity, calendar, grid, unit, key, finiteness,
practice-pair, and fixed-mask gates. Default assembly rehashes the raw weather
and exactly reconstructs 23,722 registered practice rows (table SHA-256
`205a94ae92c12810026c9c5d0ac0fa3760e46ebc39669e528ba20a125a0c46d7`);
a separate exact-recomputation receipt passes. This validator reuses the
registered implementation and is described as exact recomputation, not an
independent implementation.

The mutually exclusive moisture-family screen compares: common stage-mean
temperature controls only; controls plus seasonal precipitation total;
controls plus total and eight distribution/extreme terms; controls plus
seasonal-mean PDSI; and controls plus four preplant/stage PDSI summaries. No
model contains both direct precipitation and PDSI. Exact source validators
bind 23,722 direct-weather rows, 118,610 monthly-index window rows, and 2,808
calendar rows. Their identical common support yields 20,228 consecutive-year
changes: 5,952 per corn practice and 4,162 per soybean practice. Initial or
gapped years are not differenced, and training differences sharing either
level endpoint with a test difference are purged.

Direct-practice reporting support is strongly unbalanced over time and is
never filled. Unique corn/soy county levels are generally near 200 per crop in
the 1980s and 1990s, fall to 115/67 in 2012, 63/25 in 2018, and only 3/1 in
2019. The same-county terminal tests contain 434 corn and 262 soybean
first-difference rows per practice after endpoint purging, but are conditional
on this selected reporting support. Publication sensitivities therefore omit
the sparse 2019 endpoint and use fixed-county support windows; neither is a
model-selection input.

Models are fit separately by crop and irrigation practice. Continuous columns
and quadratic year terms are centered/scaled using training rows only. A
rank-revealing least-squares solve uses the registered relative singular-value
cutoff of (10^{-10}); numerical warnings or nonfinite singular values,
coefficients, predictions, or metrics fail closed. Aggregate RMSE, MAE,
predictive R-squared, and correlation are scored for eligible leave-one-state-
out development tests, a same-county terminal 2012--2019 test, and development-
period precipitation tails. Distribution is promoted by the frozen
development rule only when it improves RMSE in every eligible state by at
least the greater of 0.0001 and 1% of quantity-only RMSE. Terminal and extreme
tests are confirmation evidence and are not used to tune that rule. Neither
coefficients nor row predictions are emitted. The exercise is a historical,
regional predictive screen; it is not a causal yield response, nationally
representative U.S. estimate, damage function, or SCC input.

### Preliminary direct-practice fixed-effects association

A separate, coefficient-bearing diagnostic uses the same validated direct
NASS/nClimGrid levels but excludes 2019 before estimation because reported
support collapses to three corn and one soybean county levels. For crop
`c`, irrigation practice `r`, county `i`, state `s`, and harvest year `t`, the
registered association is

\[
\log Y_{icrt}=\alpha_{icr}+\lambda_{sct}+f_c(P_{ict})+
\sum_{k=1}^{3}\left(\gamma_{kcr}T_{kict}+\delta_{kcr}T_{kict}^2\right)
+\varepsilon_{icrt},
\]

where `P` is crop-calendar seasonal precipitation and `T_k` is mean
temperature in fixed 0--30%, 30--70%, and 70--100% season windows. The
quantity form uses precipitation per 100 mm and its square. The timing form
also includes early- and middle-window precipitation shares; the late share
is omitted. County fixed effects and crop-specific state-by-year fixed effects
are removed by alternating projections to a maximum-change tolerance of
`1e-10`; the within regression is solved by rank-checked least squares and
uses a finite-sample-corrected county-cluster sandwich covariance estimator.

The primary form is frozen from the preceding outer-holdout screen before
coefficient estimation: quantity for corn, quantity plus timing for soybean.
The reported quantity contrast adds 100 mm at the observed 25th, 50th, and
75th precipitation percentiles and evaluates the quadratic exactly. The timing
contrast moves 0.10 share from the omitted late window to the middle window,
holding total rain, early share, temperatures, and fixed effects constant. It
is explicitly partial and does not reconstruct co-moving dry-spell or
heavy-rain statistics. The retained sample has 7,013 observations/361 counties
per corn practice and 4,844/255 per soybean practice. No missing outcome is
filled and no row prediction is released. Because state-year absorption does
not eliminate all time-varying confounding, the resulting coefficients and
contrasts remain historical associations and are barred from causal,
national, damage, or SCC interpretation.

An independent audit rereads the hash-bound panel, reconstructs all eight
crop-by-practice-by-form samples and designs without importing production
estimation functions, reimplements the alternating fixed-effect projection,
solves by reduced QR, and separately forms the county-cluster sandwich. All
324 coefficient, standard-error, probability, contrast, fit, and cluster-count
fields agree within a maximum absolute difference of `1.04e-13` against a registered
`1e-10` tolerance.

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
emulator. Direct daily ISIMIP/CMIP fields are the reference. The primary fast
path first computes the exact crop-calendar features from version-pinned daily
ISIMIP3b historical, SSP1-2.6, SSP3-7.0, and SSP5-8.5 fields. For each retained
ESM/member and crop feature, it fits a predeclared smooth response to GMST from
the same CMIP6 realization. Matched FAIR baseline and pulse paths are then
evaluated with the same ESM/member, feature-response draw, calendar, and joint
residual realization, so weather noise is not mistaken for the one-tonne
signal. The direct response difference and centered finite-difference
derivative must converge as pulse size decreases. This is a direct-feature
emulator, not an independent climate model; scenario differences are training
information and never the marginal experiment. The complete design and
provenance contract are in `PAIRED_CLIMATE_FEATURE_DRIVER.md` and
`data/provenance/isimip3b_paired_feature_driver.toml`.

Before fitting, freeze the complete five-ESM/member by four-experiment by
four-variable catalogue product recorded in
`data/provenance/isimip3b_daily_catalog_selection.csv`. The current snapshot
contains 80 public/unrestricted CC0 version-`20210512` datasets. It is a model
selection and storage-planning record, not evidence that the 1.757 TB catalogue
has been acquired. The complete pinned MRI-ESM2-0 SSP3-7.0 precipitation and
mean-temperature blocks for 2015--2020 now match their SHA-512 values and pass
decoded-grid, units, missingness, physical-value, and exact daily-chronology
checks. Daily `tas` from the same ESM/member/scenario supplies
cos(latitude)-weighted annual GMST in the registered builder; the real
six-year projection smoke has exact 365/366-day counts and training rows must share one
explicit source and Kelvin value within each ESM/member/scenario/year. This
now extends through complete historical 2011--2014 `pr`/`tas` files that join
the projection fields at an exact 24-hour boundary. Four historical annual
GMST values use the same MRI-ESM2-0 member and have exact 365/366-day counts.
This clears one ten-year historical/projection `pr`/`tas` pair only, not
whole-ESM/scenario validation or feature-response fitting. A bounded real
maize/rainfed crop-calendar smoke over two latitude rows and harvest years
2016--2019 produces 2,744 season records and 8,232 three-window records. All
additive precipitation/day-count quantities reconcile exactly, and timing,
wet-day, dry-spell, Rx1day, and Rx5day invariants pass. ISIMIP timestamps are
normalized to calendar dates before comparison with day-of-year bounds; a
synthetic noon-timestamp regression test prevents recurrence of the maturity-
date omission found by this smoke.

Whole ESMs and whole scenarios, not random years alone, are held out. STITCHES
supplies a sequence-preserving benchmark; MESMER-M-TP plus a published daily
occurrence/amount generator is the fallback if the direct-feature response
fails distributional or convergence gates. MESMER-X remains an independent
Rx1day benchmark. RIG (Huang et al., 2026 preprint) is the closest known joint
daily global temperature--precipitation system under flexible radiative
forcing, but is not executable as of 22 August 2026 because its authors state
that code will be released upon publication. ACE2-SOM is a high-complexity
robustness model rather than the default.

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
The parsimonious direct-weather reference contains joint temperature and
crop-calendar seasonal precipitation quantity. Timing/distribution terms are
candidate extensions retained only for robust, stable incremental outer-
holdout value. SPEI and PDSI/scPDSI climatic-water-balance indices are serious
competing drought representations, as is the soil-moisture family; none is a
term automatically stacked with the underlying precipitation and temperature
variables. [Fishman
(2016)](https://doi.org/10.1088/1748-9326/11/2/024004) motivates separating
rainfall quantity from occurrence, and [Lesk, Coffel, and Horton
(2020)](https://doi.org/10.1038/s41558-020-0830-0) motivates testing rainfall-
intensity distributions; neither determines the global response form.

Predictive comparisons may give every moisture family the same predeclared
nonmoisture heat controls. Because PDSI/scPDSI and SPEI already incorporate a
temperature-dependent atmospheric-demand term, coefficients from a model that
also contains temperature or heat cannot be interpreted as an additive
precipitation-versus-temperature decomposition. A later causal attribution
design must state which drivers are held fixed and use a symmetric or other
pre-specified path decomposition; component effects are never summed across
alternative moisture families. For every future paired climate draw,
calculate the corresponding drought-index change directly, then use a
pre-specified symmetric decomposition when a precipitation versus
temperature/PET attribution is required.

For the historical climatic-index benchmark, monthly CRU scPDSI is aligned to
the same crop-year windows by day-weighting each monthly value over its exact
overlap with a stage. Retain stage mean, minimum, monthly-index day-equivalents
at or below the registered threshold, the threshold itself, and covered-day
count. These equivalents repeat a monthly index value over its overlapping
calendar days and are not observed daily drought occurrences. Require
exact grid-centre correspondence after longitude normalization, complete
monthly coverage for every stage, and a covered-day count equal to stage
length. This benchmark tests historical response and coverage only; future
SCC runs must derive their drought indices from matched baseline and pulse
climate paths and must not project observed CRU scPDSI.

The global historical implementation runs in resumable latitude partitions
with `scripts/build_stage_scpdsi_partitions.sh`, validates every partition,
and refuses to combine anything other than the declared complete partition
count. `scripts/allocate_irrigation_scpdsi_basis.py` joins complete stage
records to the rainfed and fully irrigated calendar panels, drops an entire
crop-grid-year key if either regime lacks index coverage, and records observed
and unobserved exclusions separately. Within each regime it constructs stage
and seasonal day-weighted means, minima, monthly-index threshold
day-equivalents, and threshold fractions. Only then does it apply fixed MIRCA-2000 area shares to the
single aggregate GDHY outcome. The 16-column candidate contains no raw
precipitation, temperature, CDD, or wet-extreme term and is labeled as a
non-stacked climatic-water-balance family.

Each partition manifest binds its output hash to the current raw CRU and crop-
calendar hashes, crop, regime, years, latitude slice, stage fractions, and
calendar fields. The combiner requires gap-free latitude coverage.
`scripts/validate_irrigation_scpdsi_basis.py` verifies that manifest chain plus
source-panel, derived scPDSI, weight, and audit SHA-256 values and fully
recomputes the output from the derived stage tables. This is not described as
an independent recomputation of every monthly metric from raw CRU. It requires
exact false flags for fitting, causal interpretation, future projection, and
SCC use. The convenience wrapper
`scripts/run_scpdsi_candidate_chunk.sh` composes partitioning, combination,
regime-first basis construction, weighting, and validation. The 1982--1989 run
validates 240,784 maize rows with 115,758 positive outcomes and 176,537 soybean
rows with 47,653 outcomes; the 2012--2016 run validates 150,490/59,772 and
110,336/26,601. The -2 threshold used in these runs is
a diagnostic construction setting, not a selected response threshold. These
panels permit a common-support predictive comparison under the separate,
coefficient-suppressing drought-family diagnostic contract. That design is
specified and its downstream historical predictive comparison has now been
run and validated; the panels themselves do not estimate a relationship.

`scripts/build_direct_scpdsi_common_support.py` implements that support
assembly without fitting. It takes the validated candidate tables, intersects
whole `harvest_year, lat, lon_360, crop` keys, and emits two deterministically
ordered tables rather than one stacked predictor matrix: a 54-feature
direct-weather view and a 16-feature scPDSI view with identical keys and
outcomes. The four current bundles have the following common rows/observed
outcomes and direct-only dropped rows/observed outcomes: maize 1982--1989,
240,784/115,758 and 24,744/1,921; soybean 1982--1989,
176,537/47,653 and 14,935/269; maize 2012--2016,
150,490/59,772 and 15,465/1,046; and soybean 2012--2016,
110,336/26,601 and 9,334/147. scPDSI-only drops are zero rows and zero observed
outcomes in each case.

`scripts/validate_direct_scpdsi_common_support.py` verifies input and output
SHA-256 values, validates each view independently, rereads the two immediate
candidate inputs, and exactly recomputes the views and support audit. It does
not rerun the upstream allocators from raw climate, crop-calendar, yield, or
irrigation-share sources, and it does not bind upstream validation receipts.
Running those upstream validators and retaining their receipts is therefore
an explicit external prerequisite. Boolean gates prohibit stacking, fitting,
coefficient output, causal interpretation, future projection, damage, and SCC
use. The resulting files are data-only comparison inputs, not estimates or
results. Seasonal quantity remains the parsimonious direct-weather reference;
distribution requires robust stable incremental outer-holdout value, and
direct weather, scPDSI/PDSI, SPEI, and soil-moisture families compete
mutually exclusively.

The registered direct-weather--scPDSI diagnostic binds its configuration,
four common-support view pairs, heat-control bases, upstream allocation
audits, validation receipts, and source hashes before fitting. It checks exact
common keys and outcomes, irrigation weights, the 1 mm wet-day threshold used
in direct weather, the -2 scPDSI threshold, and equality of stage-temperature
controls across families. It forms only consecutive-year log-yield
differences and never bridges a missing year. This yields 209,036
crop-grid-year pairs: 101,157 early-period and 45,633 later-period maize pairs,
and 41,678 early-period and 20,568 later-period soybean pairs.

Five mutually exclusive predictor sets are compared: nonmoisture controls;
controls plus seasonal log precipitation; controls plus seasonal mean scPDSI;
controls plus a seasonal scPDSI summary; and controls plus crop-stage scPDSI
means. Each fit standardizes continuous predictors using the training sample
and estimates ordinary least squares separately by crop. Evaluation reports
RMSE, MAE, and R-squared for five deterministic hashed, unbuffered 5-degree
spatial folds; one retrospective early-to-later split; and five crop-specific,
endpoint-purged stress subsets. Crop-grid-year pairs receive equal weight. The
protocol has no model-selection rule and emits neither coefficients nor
row-level predictions.

Across the five spatial folds, seasonal quantity has the lowest mean RMSE for
maize (0.288589, versus 0.290401 for controls and 0.288697 for the best scPDSI
specification) and soybean (0.209670, versus 0.211282 and 0.210183). It lowers
RMSE in every crop-fold comparison, but gains are below 1% and MAE results are
less uniform. The seasonal scPDSI summary is lowest-RMSE in all five maize
stress subsets; it is not the stable general winner. The validator exactly
recomputes the declared inputs, splits, refits, and aggregate metrics, and a
separate clean-room implementation reproduces all 110 metrics with zero
numerical discrepancy.

This comparison remains a nonproduction historical predictive diagnostic.
Spatial folds are unbuffered and equal-pair weighting is not a
production-weighted welfare estimand. A separate registered sensitivity pools
the five spatial-fold OOF errors and resamples crop-specific 10-degree cells
5,000 times, keeping all years and both episodes within a cell together. Maize
has 126 occupied cells (inverse-Herfindahl effective count 65.26) and soybean
56 (26.66). It reports paired percentile intervals for candidate-minus-
reference RMSE and MAE while emitting no row scores or draws. All 12
scPDSI-versus-direct intervals include zero. The sensitivity is conditional on
the fixed OOF fits: it does not refit training samples, define a random target
population, account for model selection, or model dependence beyond the cell
boundary. Because the CRU product calibrates scPDSI using the complete
1901--2025 record, the early-to-later score is retrospective rather than
prospective. Buffered or leave-region-out validation, common heat thresholds,
SPEI and soil-moisture competitors, production weighting, frozen drought-index
calibration, and causal response identification remain open gates. No result
in this diagnostic is a climate-to-drought projection, damage estimate, or SCC
input.

## S5. Estimation

Fit the candidate responses on crop-grid-year observations with grid/crop
fixed effects and flexible year effects. The reference uses joint temperature
and crop-calendar seasonal quantity; direct-pattern extensions and separate
PDSI/scPDSI, SPEI, and soil-moisture families use identical outer splits.
Pre-register feature selection, splines, and thresholds. Report null, unstable,
and worse performance, permit the parsimonious reference or a drought-index
family to lead, and never select by SCC magnitude. Pool crop seasons only with pre-specified
crop interactions or a hierarchical partial-pooling structure; a combined
panel is never authority to impose common weather slopes across maize, rice,
wheat, and soybean. Cluster or model spatial dependence. Include
irrigation-specific response-basis exposure only through the one-outcome
aggregation contract; do not create irrigation outcome strata from aggregate
GDHY yield. The outcome file is matched to the calendar at the crop-season level according to the locked crosswalk in
`data/provenance/crop_calendar_gdhy_crosswalk.md`; generic GDHY aggregate
directories are not substitutes for an identified season. GDHY does not
identify irrigated and rainfed yields separately. Early historical pilots
therefore used rainfed-calendar exposure only. Corrected minimal maize and
soybean diagnostics now construct response-basis columns within each calendar
regime and combine them with fixed MIRCA-2000 area shares into one exposure row
for the aggregate GDHY outcome. This does not estimate irrigation-stratified
yields or regime-specific response slopes, and the full production basis
remains unfitted. When both calendar regimes are available, an
independent, outcome-blind fixed-vintage crop-grid area-share source must weight their climate
features into one exposure vector for the single GDHY crop-season-grid-year
outcome. Shares are fixed across outcome years, cover every declared regime,
and sum to one. Missing shares or exposure rows are not renormalized, and the
same observed yield is never entered as separate rainfed and irrigated
observations. This historical exposure-allocation weight is distinct from the
regional baseline crop-value weights used later for welfare aggregation. CO2
is an explicitly provenanced scenario term; it cannot be separately added
after a response that already includes it.

The allocation order is part of the estimand. For regime-specific weather
history `W_r`, construct every nonlinear response-basis column `B(W_r)` first,
including log/spline/threshold terms, CDD, Rx1day/Rx5day, drought indices, and
temperature--water interactions. Then construct the one-outcome exposure
`Z = sum_r s_r B(W_r)` with fixed MIRCA area shares. Averaging primitive
weather and then applying `B` is prohibited: nonlinear transforms do not
commute with weighting, and post-aggregation interactions introduce
cross-regime products. The proposed common-slope log-yield equation is an
aggregate reduced form, not an identified decomposition of latent rainfed and
irrigated yields. Area shares are observable exposure weights; exact
log-change production weights would require independent regime-specific
baseline yields, which GDHY and MIRCA do not supply. Revenue weights enter only
the later welfare aggregation. The full equation, identification restrictions,
and sensitivity benchmarks are specified in
`IRRIGATION_AGGREGATE_ESTIMAND.md` and
`config/irrigation_aggregate_estimand.toml`. The first primitive-weighted
primitive-weather-weighted aggregate-regime diagnostic outputs violate this
order and are withdrawn. A corrected
minimal predictive rerun uses an explicit contract-aware prebuilt-basis mode;
that diagnostic mode does not freeze or fit the complete production response.
The separate direct-pattern candidate builder extends the same allocation
order to 54 basis columns covering seasonal and three-window rainfall amount,
normalized stage shares/timing/concentration, wet-day occurrence and
conditional intensity, CDD, Rx1day, Rx5day, mean temperature, and
temperature-by-log-amount terms. It rechecks stage-to-season days,
precipitation, wet-day counts, and extreme bounds before allocation. The 1 mm
wet-day definition is carried as an explicit candidate/QA setting, and the
output remains `fit_authorized=false`; heat and alternative drought families
are joined only as separately validated candidate families.

Support is audited with welfare-relevant denominators before aggregation.
`scripts/audit_mirca_welfare_support.py` reports positive MIRCA harvested area
inside cells with any observed outcome and with a consecutive-yield pair,
separately for irrigated and rainfed area. It also reports an explicitly
conditional MIRCA-area-times-same-vintage-GDHY-yield proxy and the MIRCA area
over which that proxy is undefined. Revenue coverage is not inferred without
a pinned spatial price/value source, and crops are never pooled using cell
counts or a fabricated common price. For the current 1982--1989 pair support,
area coverage is 79.017% for maize and 89.288% for soybean; this partial support
must be revisited on the complete historical panel before welfare calibration.

The machine-readable production design registry is
`config/primary_response_spec.toml`. It is explicitly not frozen and does not
authorize fitting. Every production design exercise must compare the
parsimonious seasonal-amount reference against pre-registered candidates for
crop-window amount; normalized stage distribution/timing; wet-day frequency;
conditional wet-day intensity; CDD; Rx1day; Rx5day; mean temperature;
crop-specific heat extremes; and registered temperature--precipitation
interactions. “Retain” means that each concept enters a pre-registered
candidate comparison; it does not require placing collinear encodings or
alternative drought representations in one unrestricted regression. Added
distribution terms are retained only for robust incremental held-out value.
The direct precipitation-pattern family is compared separately with serious
PDSI/scPDSI and SPEI climatic-water-balance candidates and with soil-moisture
families. The threshold registry is
empty until primary evidence or a documented training-only procedure supports
crop/specification choices.

The registered primary source is the earliest MIRCA-OS v2 vintage (2000),
held fixed across the 1981--2016 outcome panel; 2005, 2010, 2015, and 2020 are
separate fixed-vintage sensitivities, not time-varying adaptation. The 2000
maize and soybean weights match 97.79% and 97.99% of observed-yield cells in
the current 1982--1989 panels. Unmatched cells are disclosed and excluded
before estimation, never assigned a national mean or renormalized. MIRCA's
annual rice and wheat maps do not identify GDHY's two rice seasons or its
spring/winter wheat outcomes. The builder exports those provisional mappings
with `production_eligible=false`, and the allocator fails if they are supplied
to a production panel. A season-resolved crosswalk is therefore an open input
gate for rice and wheat. For rice, the only current candidate is the
publisher's 5′ monthly `Rice1`/`Rice2`/`Rice3` product, aggregated by summing
hectares and reconciled to the annual Rice map under the protocol in
`MIRCA_SEASON_CROSSWALK_GATE.md`. The archive contains all 30 expected names,
but nine 2005--2015 rainfed files incorrectly declare source year 2020 and are
blocked. The six-file 2000 implementation passes metadata, grid, month,
nonnegativity, and aggregation checks, but the seasonal
maxima exceed the released annual Rice areas by 64,247.23 irrigated ha and
5,302.04 rainfed ha. Because both predeclared reconciliations fail, no rice
weight table is promoted while publisher generation logic is investigated.
MIRCA's numeric wheat subcrops do not provide a documented spring/winter
identity, so no timing-based inference is allowed.

GDHY's aligned construction can clip a negative aligned estimate to zero.
The join preserves the original value in `gdhy_yield_raw_t_ha`, flags it in
`yield_nonpositive`, and sets the log-response outcome to missing. Negative
source values fail, and no arbitrary positive offset is introduced.

Annual source support is audited before estimation with
`scripts/audit_gdhy_annual_support.py`. A fresh official archive download and
the local archive have identical SHA-256 values, every ZIP member passes CRC,
and extracted members match independently calculated hashes. The verified
source nevertheless loses 1,791 maize-major and 596 soybean positive cells in
2015 and restores all of them in 2016. These values are neither imputed nor
relabeled. The unbalanced consecutive-positive-pair panel is primary. A
separate complete-positive-support sensitivity retains cells positive in every
declared year, records the resulting sample loss, and warns that this
conditioning can select a nonrepresentative subset. Excluding transitions that
touch the unexplained support-loss endpoints is a separate publication
sensitivity pending clarification from the data producer.

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

We executed this control using the archived GIVE environment: Julia 1.6.4
x86_64 under Rosetta and the repository-level `.julia_depot_1_6`. A separate
native Apple-silicon Julia 1.8.5 attempt failed before executing the harness
because the archived dependency lock requested an Electron artifact that is
not available for `aarch64-apple-darwin`. We therefore claim successful
execution only for the archived x86_64 environment and report native-ARM
portability as an unresolved reproducibility limitation.

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
as an external observed validation layer, after an explicit crop calendar and
spatial-measurement route; it is not a source of global future climate
features. County yield is not labeled rainfed without crop-specific irrigated
area evidence: the primary sample applies a predeclared high-rainfed-share
threshold to the 2017 Census crop share, reports 2012/2022 vintages and
10/20/30 percent thresholds, and treats mixed counties separately. A distinct
regional validation uses only crop--county--years with positive numeric yields
reported under both production practices; it does not substitute for the
national aggregate panel or identify a global irrigation response.
For direct daily weather, CDD, Rx1day/Rx5day, wet-day occurrence/intensity,
timing concentration, heat, and nonlinear response terms are built within
weather-grid cell and crop-calendar class before county-polygon primary or CDL
crop-pixel sensitivity averaging. All-classes wheat is combined across winter,
spring, and durum only after independent class shares pass their gate.
Calculating these nonlinear metrics after county-mean weather aggregation is
an explicit invalid-order failure, not an alternate specification.
The competing PDSI/scPDSI and SPEI panels use the same crop calendars,
irrigation classifications, outcomes, and outer folds so their predictive
performance is directly comparable; they are not appended to the direct-
weather model by default.

The drought pathway contains two separately validated estimands. The
historical response estimand compares crop outcomes with a declared drought
exposure; the climate estimand compares that same exposure under matched
baseline and CO2-pulse climate paths. The current CRU scPDSI panels and their
direct-weather common-support views prepare only a historical predictive
comparison. They do not estimate either a causal drought--yield response or a
climate-induced drought increment. A future SCC pathway requires both links,
plus the single welfare mapping, to pass independently. It may not substitute
observed CRU scPDSI or USDM histories for the matched future drought path.

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

The diagnostic feature list is not the production registry. It omits
wet-day frequency, conditional intensity, Rx5day, heat, and the climatic-index
and soil-moisture alternatives; its three window totals only partially encode
the normalized timing/distribution estimand. In the response audits reported
before the split revision, temporal and climate-extreme labels were applied to
adjacent first-difference pairs without an endpoint purge. A test pair could
therefore share one underlying level-yield endpoint with a training pair even
though its climate labels were outcome-blind. Those numerical outputs are
legacy dependent stress tests and are stale after the hashed specification
changes. Before production model selection, purge from training every pair
containing either crop/grid/year endpoint used in the temporal or extreme test
set, document the resulting support loss, verify endpoint disjointness
mechanically, and rerun all panels. Spatial grid-block splits remain disjoint
by construction. A purged predictive pass remains noncausal and SCC-ineligible.
The revised evaluator and audit validator now enforce zero endpoint overlap
and pass synthetic tests. Corrected 1982--1989 and 2012--2016 MIRCA-2000 maize
and soybean minimal diagnostics pass under the new hash; other crop-period
panels remain stale or pending. The production cell fixed effect is
latitude--longitude--crop/season, not irrigation, because the outcome is
aggregate. The level fixed-effects versus first-difference design and the
appropriate common, crop-specific, or regional year-shock controls remain
unfrozen identification choices.

A distinct version-1 precipitation-distribution screening contract operates
on the validated 54-column basis-before-weighting tables. Every nested model
contains the same three crop-window mean-temperature controls. The reference
adds seasonal `log(1 + precipitation)` quantity; comparison models then add,
separately and jointly, (i) precipitation timing centroid and concentration
HHI, (ii) stage wet-day frequency and conditional wet-day intensity, (iii)
stage maximum-dry-spell fractions, and (iv) stage Rx1day and Rx5day. The three
stage precipitation shares are omitted when centroid and HHI are present to
avoid exact share-sum/timing redundancy. The 1 mm wet-day threshold and
0--30/30--70/70--100 percent windows are locked diagnostic QA choices, not
selected production thresholds or observed phenological stages. The source
tables remain `fit_authorized=false`; a separate contract permits transient
held-out prediction while suppressing coefficients and forbidding causal,
production-model, response-draw, damage, and SCC use. The independent
validator verifies source and specification hashes, reruns the complete
diagnostic from those locked tables, and recursively compares every reported
field with the fresh result. In the eight-year panels, the union of within-cell
95th-percentile CDD and Rx1day endpoint labels marks approximately 47% of
consecutive pairs, so it is reported as a retrospective high-tail stress split
rather than rare-event validation. Five-degree blocks are hash-assigned
without a geographic buffer and therefore do not constitute leave-region-out
extrapolation.

The later-period diagnostic is pinned separately by
`config/precipitation_distribution_diagnostic_2012_2016.lock.toml`, which
records both panel and allocation-audit SHA-256 hashes, crop, years, row counts,
and positive-outcome counts. Independent validation recomputes all model
predictions and metrics from the locked Parquet sources. The screen contains
46,434 maize and 20,682 soybean consecutive pairs. No distribution extension
improves seasonal quantity in all three holdouts for either crop: all maize
extensions worsen spatial and temporal RMSE; every soybean extension worsens
temporal RMSE. The only maize improvement is 0.000044 RMSE for timing/HHI in
the high-tail split. Soybean gains are split-specific (0.001516 for dry spells
spatially and 0.001366 for occurrence/intensity in the high-tail split). The
all-distribution model worsens temporal RMSE by 0.004826 and 0.003491 for maize
and soybean. Because the maize temporal zero-change RMSE is lower than every
fitted candidate, that adverse benchmark comparison is retained.

The 2012--2016 high-tail labels contain 66.15% of maize pairs and 66.39% of
soybean pairs and leave only 4,563 and 1,774 training pairs; they are not
rare-event validation. These short-panel screens also have no paired
confidence intervals or multiple-comparison adjustment. A separate
three-model minimal-basis complete-positive-support sensitivity retains
91.23% of maize pairs and 94.23% of soybean pairs and ranks seasonal joint
temperature--quantity first in all six crop-by-holdout comparisons. The
seven-family distribution diagnostic has not been rerun on that selected
subset. GDHY is a modeled, observation-aligned gridded yield product rather
than direct farm observations, and both later temporal transitions touch its
unexplained 2015 support discontinuity. The two panels are therefore reported
as predictive screening and sample-composition evidence only.

When daily climate coverage crosses source-file boundaries, the builders take
an ordered list of NetCDF inputs, require identical latitude/longitude grids and units,
and verify one strictly increasing daily time axis with neither duplicated nor
missing boundary dates. They retain only the years that can enter the requested
harvest-year seasons. Period panels must have an identical schema, nonoverlap
on crop-grid-year keys, and the exact declared contiguous harvest-year set.
The response audit records that set, and the validator checks it whenever an
expected start and end year are supplied. These are coverage and reproducibility
gates; they do not strengthen causal identification.

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

### S10.1 Citation and evidence gaps retained at this stage

The cited primary literature supports the definitions of PDSI/SPEI and the
decision to compare rainfall quantity, occurrence, intensity, and observed
drought severity. It does not validate a universal global crop coefficient,
the diagnostic scPDSI threshold of -2, or transport of a historical CRU
scPDSI association to future ISIMIP climate. No completed, validated global
SPEI or soil-moisture candidate is yet available. The climate-to-drought
mapping, causal response design, global welfare calibration, and empirical
cost basis for the `trend` and `upper` adaptation schedules therefore remain
evidence gaps rather than quantities to fill by assumption. The deferred
noncoastal infrastructure-flood component likewise requires its own primary
hazard, exposure, vulnerability, and overlap evidence before implementation.
