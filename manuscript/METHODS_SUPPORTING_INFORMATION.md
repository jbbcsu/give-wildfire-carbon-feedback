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

The isolated all-practice route was also exercised for Acadia Parish,
Louisiana (GEOID 22001) in 2019. The hash-bound receipt retains 119 positive
polygon/grid intersections, five monthly weather inputs, and one supported
soybean crop-county-year feature row. This geographically distinct check
validates plumbing and lineage only; it is not a national sample or a climate--
yield estimate.

For the partial national weight checkpoint, a separate audit rereads every
completed receipt, verifies all 932 corresponding Parquet hashes and frozen
contract identities, and summarizes land-relative weather-valid coverage
without resuming construction. Completed receipts cover 35.46% of the 2,628
registered counties across 16 states; 60 have positive masked area. The
minimum completed ratio is 0.960832366, one is below 0.97, and seven are below
1.0. The partial set reflects FIPS-ordered execution plus earlier bounded
smokes and is not a representative national sample. Consequently, Trigg's
lower 0.907267979 ratio remains a fail-closed source-geometry question rather
than grounds for a post-result threshold change or silent county exclusion.
The follow-up source audit pins the official 2019 Census TIGER/Line Trigg
County area-water archive (625,481 bytes; SHA-512 recorded in provenance).
Its 2,123 features' `AWATER` values sum exactly to the county's 102,999,105 m2.
Within each polygon, the audit applies its published
`AWATER/(ALAND+AWATER)` fraction to exact EPSG:5070 county/grid intersections.
The 16 masked cells contain an estimated 81,538,947 m2 water and 127,512,062
m2 land; weather-valid fractional-land coverage is 0.888503097 and remains
below the unchanged 0.95 gate. No output partition is emitted.
For an outcome-free source sensitivity, we separately hash-bind NOAA's four
January 1981, July 2000, and January 2019 county area-average files,
product-version receipts, and official numeric NCEI-to-FIPS state crosswalk.
Every sampled variable/month contains the same 3,107 county rows. Numeric code
15221 maps to Trigg FIPS 21221; all sampled Trigg real-day values are finite,
satisfy `TMIN <= TAVG <= TMAX`, and reproduce the rounded temperature midpoint
within 0.005 C. July 2000 also validates Adair County, Iowa (19001), under the
same mapping and value gates. These samples validate a source-computed county
route but do not replace the
registered polygon estimator; boundary
vintage, full-period identity, and feature-equivalence gates remain open.
We then compare the official county averages directly with the fixed 2019
TIGER polygon-weight proxy for two preregistered counties (Cuming County,
Nebraska, and Fresno County, California) in April 1990, February and July 2000,
July 2012, and January, June, and December 2019. Each month requires
exact common 3,107-county support, complete daily
chronology, finite values, declared units and physical bounds, fixed positive
unit-sum polygon weights, and identical county identities. Hash-bound inputs
and daily difference metrics are recorded for every county-variable cell.
The largest monthly precipitation-total difference is 0.9926 mm; a near-zero
Fresno precipitation series in July 2012 has the lowest correlation (0.98533),
while temperature correlations otherwise remain above 0.99999 apart from an
April minimum of 0.999993. A hash-bound series gate requires all 56 selected
county-variable-month cells. Fifty-five have nonzero maximum differences; the
remaining dry Fresno July-2000 rainfall pair is an exact constant match with
undefined correlation. These are measurement-route sensitivities, not an
equivalence test, estimator selection, response estimate, or SCC input.

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

The positive log-yield construction separately exposes the 499 reported corn
zeroes in its source table. A source/hash-bound support audit counts 150
counties, 217 consecutive spells, and a maximum 10-year spell; 419 zero rows
pass the fixed geography gate, 45 have a usable fixed-2017 irrigation share,
and 7/8/8 meet the 10/20/30% high-rainfed selectors. It also records that all
zeroes lie in 1998--2009, the five leading states contain 73.55% of zero rows,
and only 15 adjacent-positive rows have an eligible irrigation share (4/5/5
meet the three high-rainfed selectors). No zero is replaced or log-
transformed, and the audit emits no coefficient. A zero-retaining outcome
model remains a required, separately preregistered sensitivity; temporal and
state concentration prohibit interpreting reported zeroes as a generic crop-
failure signal.

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
has been acquired. Bounded complete-file `pr`/`tas` coverage now includes
historical plus all three SSPs for all five frozen ESM realizations. Every
available file matches its
version-`20210512` API identity, bytes, and SHA-512 and passes decoded-grid,
units, missingness, physical-value, exact daily-chronology, and historical-
boundary checks. Daily `tas` from the same ESM/member/scenario supplies
cos(latitude)-weighted annual GMST with exact 365/366-day counts, and training
rows share one explicit source and Kelvin value within each cell. Bounded
maize/rainfed smokes over two latitude rows produce 2,744 season records and
8,232 three-window records per future scenario. Additive precipitation/day-
count quantities reconcile exactly, and timing, wet-day, dry-spell, Rx1day,
and Rx5day invariants pass. MRI's exact four-scenario holdout improves 24/44
folds but has a 1.09903 worst RMSE ratio, so it is not promoted. UKESM improves
23/44 folds (median ratio 0.99985; worst 1.03248). The five-ESM joint product
has 565,950 rows and passes 55 whole-ESM and 44 whole-scenario folds; 41 and 36
improve over the cell-mean benchmark, with median ratios 0.99760 and 0.99744
and worst ratios 1.05145 and 1.01605. Independent validation passes, but it
remains only seven nonoverlapping years, one
crop/regime, and two latitude rows. ISIMIP timestamps are normalized
to dates only after complete daily-sequence validation.

Before using FAIR, a bounded numerical pairing smoke aggregates the two-
latitude feature cells, fits one linear feature-on-GMST surface for each of 55
ESM-feature combinations, and reuses the same empirical residual identifier
for baseline and pulse levels. Across 880 rows, zero-pulse and pre-divergence
identity, separate support flags, direct-versus-centered agreement, and
convergence for 0.01, 0.005, and 0.0025 K perturbations pass. Pulse support is
within the bounded aggregate training range for 851 rows, above for 19, and
below for 10. This is an artificial-Kelvin software gate, not a FAIR path or a
selected production emulator.

The actual temperature-delta input is validated separately using the pinned
core GIVE/FAIR manifest and source hashes. Deterministic marginal models for a
2020 CO2 pulse generate 2,204 matched rows spanning 1750--2300 for pulse sizes
0, 0.0001, 0.00005, and 0.000025 GtC. The baseline temperature path is
bit-identical across runs; the zero-pulse and through-2020 paths are identical;
the first nonzero response is in 2021; and normalized responses at the two
smallest pulse sizes agree within the registered tolerance. The largest
0.0001-GtC temperature response is 1.8368e-7 K.

The first alignment sensitivity is fixed in
`config/fair_esm_alignment_sensitivity_v1.toml`. It uses the exact pinned
five-ESM feature product and FAIR paths, defines a 2012--2014 historical
overlap mean separately for each ESM, and evaluates 2012--2300 under both
absolute anomaly mapping and centered-coordinate mapping. With an affine
feature surface, these are algebraic reparameterizations; 127,160 rows pass
common zero-residual, zero-pulse, pre-divergence, direct/centered, support, and
decreasing-pulse gates, with a maximum method disagreement of `4.55e-12`.
Per formulation, mapped temperature support is below/within/above for
44/3,784/59,752 rows, while feature support is below/within/above for
17,764/22,824/22,992 rows. Thus only 5.95% of temperature rows and 35.90% of
feature rows are inside the bounded seven-year training range. This sensitivity
also records model-specific support horizons: the first above-support baseline
year is 2021 for GFDL, 2027 for MPI, and 2033 for IPSL, UKESM, and MRI. It
does not select the overlap window, validate a non-affine response, supply a
stochastic residual path, or authorize production damages or SCC.

The next acquisition is preregistered in
`config/isimip3b_later_century_expansion_v1.toml`: the complete five-ESM by
three-SSP by `pr`/`tas` matrix for exactly 2041--2050 and 2091--2100. The live
version-`20210512` API snapshot pins 60 public/unrestricted CC0 files totaling
124,935,312,957 bytes. Harvest years 2042--2049 and 2092--2099 keep every
cross-year season inside one block. Metadata passage does not substitute for
full checksum/content, same-realization GMST, crop-feature reconciliation, or
whole-ESM/scenario validation; post-2100 FAIR years remain out of support.
The first registered GFDL SSP1-2.6 `pr`/`tas` pair for 2041--2050 has now
passed exact byte, SHA-512, and decoded global 0.5-degree, 3,652-day content
gates. `pr` has zero missing or negative values; `tas` has zero missing values
and produces ten annual same-realization GMST rows. The bounded two-latitude-
row maize/rainfed feature smoke yields 5,488 seasonal and 16,464 stage rows for
2042--2049 and passes exact additive reconciliation. The matching 2091--2100
pair and 2092--2099 bounded feature block pass the same gates. The GFDL
SSP3-7.0 2041--2050 pair and 2042--2049 feature block pass the identical
checks. Their exact-key comparison with SSP1-2.6 uses 5,488 seasonal rows and
finds mean SSP3-7.0-minus-SSP1-2.6 differences of +0.574 C, -18.33 mm
seasonal precipitation, -1.11 wet days, +3.20 maximum dry-spell days, -1.99 mm
Rx1day, and -4.07 mm Rx5day. The registered SSP5-8.5 2041--2050 pair and
bounded feature block pass the same content, GMST, and reconciliation gates.
The SSP3-7.0 and SSP5-8.5 2091--2100 pairs and bounded 2092--2099 feature
blocks also pass. The IPSL-CM6A-LR SSP1-2.6 2041--2050 and 2091--2100 pairs
then pass the same gates under their exact model-specific 12:00 daily timestamp
contract. The IPSL SSP3-7.0 2041--2050 and 2091--2100 pairs and bounded feature
blocks also pass. Both IPSL SSP5-8.5 pairs and bounded feature blocks also
pass, bringing the expansion to 24 of 60 file gates and twelve bounded feature
blocks. The MPI-ESM1-2-HR SSP1-2.6 2041--2050 and 2091--2100 pairs also pass
exact bytes, SHA-512, the model-specific 12:00 3,652-day content contract,
same-realization GMST, and 5,488-season/16,464-stage feature reconciliation.
This raises the registered expansion to 28 of 60 file gates and fourteen
bounded feature blocks. The MPI SSP5-8.5 2041--2050 pair then passes the same
gates. Together with the separately registered MRI SSP1-2.6 2041--2050 block,
the expansion reaches 32 of 60 file gates and sixteen bounded feature blocks
without rerunning a whole-scenario or whole-ESM response. Its exact-key
comparison with MPI SSP1-2.6 finds mean differences of +0.237 C, +17.88 mm
seasonal precipitation, +1.37 wet days, -1.00 maximum dry-spell days, +1.71 mm
Rx1day, and +6.75 mm Rx5day. The MRI SSP3-7.0 2041--2050 pair passes the same
exact-byte, checksum, noon
chronology, decoded-content, same-realization GMST, feature, and reconciliation
gates. Its exact-key SSP3-7.0-minus-SSP1-2.6 means are +0.369 C, -11.02 mm
seasonal precipitation, -1.07 wet days, +0.23 maximum dry-spell days, -0.32 mm
Rx1day, and +0.26 mm Rx5day. This raises tracked progress to 34 of 60 file
gates and seventeen bounded blocks, without completing the MRI scenario or
period matrix. The MRI SSP5-8.5 midcentury pair passes the same frozen-file, content,
same-realization GMST, feature, and reconciliation gates. Its exact-key
SSP5-8.5-minus-SSP1-2.6 means are +0.777 C, -8.81 mm seasonal precipitation,
+0.28 wet days, -2.83 maximum-dry-spell days, -1.50 mm Rx1day, and -2.68 mm
Rx5day. The generic leave-one-scenario-out audit is extended with an explicit
MRI contract and exact two-scenario support flags. Across 181,104 long feature
rows it improves 15/33 comparisons (median RMSE ratio 1.00027; maximum
1.04233), including 4/11 for held-out SSP5-8.5, while 21,236 values (11.73%)
are outside support. These gates raise tracked progress to 36/60 files and
eighteen blocks but remain engineering evidence only. MRI SSP1-2.6 and
SSP3-7.0 end-century pairs subsequently pass exact frozen-file identity, full
decoded-content, same-realization GMST, bounded feature, and stage/season
reconciliation gates. The exact-key SSP3-7.0-minus-SSP1-2.6 comparison
averages +2.928 C, +2.24 mm seasonal precipitation, -0.97 wet days, +2.41
maximum-dry-spell days, +0.25 mm Rx1day, and +1.15 mm Rx5day across 5,488
rows. The MRI SSP5-8.5 end-century pair and bounded block also pass these
gates, raising tracked progress to 42/60 files and twenty-one blocks. The
exact-key SSP5-8.5-minus-SSP1-2.6 comparison averages +4.591 C, -13.23 mm
seasonal precipitation, -2.62 wet days, +5.44 maximum-dry-spell days, +0.75
mm Rx1day, and +0.56 mm Rx5day. Its 181,104-row whole-scenario audit improves
16/33 comparisons (median RMSE ratio 1.00006; maximum 1.06514), including 9/11
for held-out SSP5-8.5, while 27,090 values (14.96%) lie outside exact support.
This mixed, adverse result leaves response, damage, SCC, whole-ESM, and FAIR
feature-support authorization false. The remaining frozen MPI-ESM1-2-HR
SSP3-7.0 mid- and end-century pairs and SSP5-8.5 end-century pair pass the
same exact file/content, same-realization GMST, bounded feature, and
reconciliation gates. The resulting tracked coverage is 48/60 files and
twenty-four blocks. Exact-key SSP3-7.0 minus SSP1-2.6 rain differences are
-4.38 mm at midcentury and -17.02 mm at end century; end-century SSP5-8.5
minus SSP1-2.6 is -13.20 mm. These are support diagnostics only; whole-ESM,
FAIR feature-support, response, damage, and SCC authorization remain false.
The deterministic MPI whole-scenario audits improve 14/33 comparisons at
midcentury (median/maximum RMSE ratios 1.00163/1.05542; 11.65% outside
support) and 15/33 at end century (1.00028/1.09814; 15.24% outside support).
These adverse holdouts do not promote the emulator.
The four-ESM whole-ESM evaluator binds exact GFDL, IPSL, MPI, and MRI source
audits and training hashes. Each period contains 724,416 rows and 44 holdouts.
Midcentury improves 27/44 comparisons (median/maximum RMSE ratios
0.99954/1.00969) with 8.34% outside three-ESM support; end century improves
12/44 (1.00040/1.06362) with 9.47% outside support. UKESM remains absent, so
the five-ESM and FAIR feature-support gates remain false.
The first later-century UKESM1-0-LL pair (SSP1-2.6, 2041--2050) uses the same
version-pinned content validators with an explicit expected hour of 00:00 UTC,
matching UKESM's catalogued daily coordinate; the validators' default noon
contract rejects this pair. Exact bytes/SHA-512, all 3,652 daily timestamps,
946,598,400 finite values per field, same-realization GMST, and the bounded
5,488-season/16,464-stage feature and zero-error reconciliation gates pass.
Coverage is 50/60 files and twenty-five blocks; the remaining UKESM cells and
complete five-ESM holdout remain required before FAIR feature support or any
response, damage, welfare, or SCC use.
The matching 2091--2100 UKESM SSP1-2.6 pair passes the same midnight,
checksum, decoded-content, same-realization GMST, bounded feature, and exact
reconciliation gates. A full rebuild reproduces the GMST and feature Parquet
files byte-for-byte. Separate fixed-slice end-century-minus-midcentury means
are reported only as descriptive climate diagnostics. Coverage is 52/60 files
and twenty-six blocks; four UKESM pairs and the complete five-ESM holdout
remain required before any production use.
The UKESM SSP3-7.0 2041--2050 pair then passes the same exact catalogue,
midnight chronology, decoded-content, same-realization GMST, bounded feature,
and reconciliation gates. Its exact-key comparison with SSP1-2.6 retains
5,488 rows and records quantity, within-season timing/concentration, wet-day,
dry-spell, Rx1day, Rx5day, and mean-temperature differences. Coverage is
54/60 files and twenty-seven blocks; the comparison is not a response or
damage estimate and does not open the five-ESM, FAIR, or SCC gates.
The corresponding UKESM SSP3-7.0 2091--2100 pair passes the identical gates
and exact-key comparison. Coverage is 56/60 files and twenty-eight blocks;
the remaining two SSP5-8.5 pairs are required before the five-ESM rerun, and
no response, damage, welfare, or SCC use is authorized.
The UKESM SSP5-8.5 2041--2050 pair passes the same exact file, explicit-
midnight, decoded-content, same-realization GMST, bounded-feature, exact-key
comparison, and reconciliation gates. Coverage is 58/60 files and twenty-nine
blocks. The 2091--2100 UKESM SSP5-8.5 pair and the complete five-ESM reruns
remain required; no response, damage, welfare, or SCC use is authorized.
The UKESM midcentury three-scenario holdout then applies the same fixed
leave-one-whole-scenario-out estimator and exact support flags to 181,104
rows. It improves 13/33 comparisons over the cell-mean benchmark, with a
maximum RMSE ratio of 1.22120 and 12.21% of held-out values outside support.
This engineering audit does not authorize the emulator or any downstream use.
The complete five-ESM midcentury join then applies the identical frozen whole-
ESM estimator to 905,520 rows and 55 comparisons. It improves 32/55 against
the cell-mean benchmark, with 6.47% of held-out values outside exact four-ESM
support. The UKESM SSP5-8.5 2091--2100 pair completes 60/60 registered file
gates and thirty bounded feature blocks. The same frozen whole-scenario audit
on the 181,104-row UKESM end-century product improves 17/33 comparisons and
places 16.51% of values outside exact two-scenario support. The complete
905,520-row five-ESM end-century join improves 30/55 comparisons; its
median/maximum RMSE ratios are 0.99982/1.01357 and 7.14% of held-out values
are outside exact four-ESM support. FAIR baseline/pulse feature-support
validation remains required before any response or damage use.
We then concatenate the exact-hash early, midcentury, and end-century bounded
products after normalizing only ESM identifier case, yielding 2,376,990 rows
over 23 training years. The previously registered FAIR alignment sensitivity
is rerun without changing its 2012--2014 reference window or pulse paths. Its
127,160 paired rows retain common residual identifiers and pass zero-pulse,
pre-divergence, direct/centered, and decreasing-pulse checks. All feature
levels are within the enlarged bounded envelope; 44 mapped temperature rows
for MPI in 2012 are below its envelope. These checks establish bounded
aggregate numerical support only, not a selected production emulator or any
response, damage, welfare, or SCC estimate.
For IPSL, the exact-key
SSP3-7.0-minus-SSP1-2.6 midcentury comparison finds
mean differences of +0.365 C, +13.22 mm seasonal precipitation, +0.93 wet days,
-1.36 maximum dry-spell days, +2.18 mm Rx1day, and +3.84 mm Rx5day. The matching
end-century differences are +4.146 C, +25.70 mm seasonal precipitation, +2.85
wet days, -2.26 maximum dry-spell days, +3.12 mm Rx1day, and +4.47 mm Rx5day.
These are climate-support diagnostics, not a response estimate. The
matched IPSL SSP5-8.5-minus-SSP1-2.6 midcentury means are +0.607 C, +19.88 mm
seasonal precipitation, +2.07 wet days, -0.77 maximum dry-spell days, +2.01
mm Rx1day, and +3.13 mm Rx5day. The IPSL three-SSP midcentury join contains
181,104 rows. Leave-one-scenario-out GMST adjustment improves 15/33
comparisons (median RMSE ratio 1.00028; maximum 1.02568), including 3/11 for
held-out SSP5-8.5; 20,529/181,104 values (11.34%) are outside the exact two-
scenario envelope. The matching IPSL end-century join improves only 10/33
comparisons (median RMSE ratio 1.00275; maximum 1.27466), including 2/11 for
held-out SSP5-8.5; 30,619/181,104 values (16.91%) are outside the exact
two-scenario envelope. The preregistered GFDL three-SSP midcentury join contains
181,104 rows across 11 feature families. Leave-one-scenario-out GMST adjustment
improves 14/33 comparisons versus the cell-mean benchmark; its median RMSE
ratio is 1.00036, maximum is 1.06410, and the SSP5-8.5 holdout improves only
1/11. Per-cell/family support flags classify 20,562/181,104 held-out values
(11.35%) outside the exact two-scenario envelope. The matching end-century
join has 181,104 rows; GMST adjustment improves 13/33 comparisons (median RMSE
ratio 1.00110; maximum 1.23350), with 27,260/181,104 values (15.05%) outside
the corresponding support envelope. These flags describe climate holdouts,
not FAIR baseline/pulse feature support. A separate audit revalidates
the existing paired FAIR paths and reclassifies temperature support against
the expanded GFDL GMST range (287.659--291.189 K). The mapped baseline is
within that temperature envelope for every year from 2012 through 2300 rather
than only 2012--2020. Whole-ESM and FAIR feature-support gates remain
open, and the adverse scenario result prohibits promotion.

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

The future-feature multi-crop support audit is separately frozen in
`config/isimip3b_ukesm_multicrop_midcentury_support_v1.toml`. It binds the
exact UKESM SSP1-2.6 and SSP5-8.5 source-provenance receipts and six crop-
calendar files by SHA-256. For each declared crop/regime it requires the exact
2042--2049 year set, declared row counts, crop and irrigation labels, three
stage IDs, finite/nonnegative precipitation features, bounded wet-day and
maximum-dry-spell counts, Rx1day/Rx5day ordering, identical scenario keys, and
independent stage-to-season reconciliation. The receipt reports paired
quantity, timing, dry-spell, and extreme-rain summaries and an exact-key
soybean calendar sensitivity. It explicitly sets whole-scenario, whole-ESM,
causal-yield, irrigation-treatment, damage, and SCC gates to false.

Before inspecting a real fit, the next feature-response family is fixed as a
ridge-regularized continuous pathway basis. It contains same-realization GMST
anomaly and one-year change, years since 2020, a quadratic GMST term, and
GMST-by-change and GMST-by-time interactions, with partially pooled ESM
intercept/slope deviations. Scenario identity is not a predictor. Penalty
selection and standardization occur only inside training folds; outer whole-
ESM and whole-scenario holdouts remain untouched. The preregistered promotion
rule requires every feature family to pass both holdout types, maximum and
median RMSE ratios no greater than 1.0 and 0.995, respectively, complete actual
FAIR baseline/pulse support, exact zero/pre-divergence identity, decreasing-
pulse convergence, and human review. The validated contract is not a fitted or
promoted response.

In the first real run, lambda selection is nested within each outer holdout and
shared across grid cells separately by feature family. First years of each
discontinuous climate block are excluded from one-year GMST changes. The 88
outer comparisons improve on the cell-mean benchmark 71 times; median and
maximum RMSE ratios are 0.99443 and 1.00703. Eighty-five predictions violate
nonnegative feature bounds. Because the locked maximum, every-feature, and
physical-bounds rules fail, actual FAIR pulse evaluation and promotion are not
performed.

Before examining a successor fit, we froze positive log links for rainfall,
count, dry-spell, and extreme features; bounded logits for timing metrics; and
a centered-log-ratio link with shared regularization for the three stage
shares. Nested selection and holdout scoring are performed after inverse
transformation on the original scale. The locked run improves 34/88
comparisons, with median/maximum RMSE ratios 1.00775/1.13855. It has zero
negative or above-one predictions and maximum stage-sum error `3.33e-16`, but
the maximum, median, and every-feature predictive criteria fail. Actual FAIR
pulse evaluation and promotion are not performed.
An exact-key comparison against the rejected identity-link candidate finds
only 9/88 lower physical-link RMSE ratios, zero rescued benchmark failures, and
37 lost identity-link successes. The comparison is diagnostic only and does
not select a third candidate.

The subsequent literature-constrained review selects RIME-X v1.0 (Schwind et
al., 2026) as a published direct-indicator benchmark, not as a promoted third
fit. The method represents indicator distributions on 0.1 K warming-level and
101-quantile maps and interpolates them onto simple-climate-model temperature
paths. Its exact paper archive and the project contract are version-pinned.
Only independently implemented synthetic interpolation mechanics were tested:
within-feature common random numbers, separate support flags, zero-pulse and
pre-divergence identity, rejection of extrapolation, and three decreasing
pulse sizes pass. A real fit is withheld because the current daily-derived
feature artifact contains three discontinuous short blocks rather than the
published 21-year smoothing support, and univariate quantile maps do not
preserve the joint rainfall, timing, persistence, extremes, heat, and drought
dependence required by the crop response. Whole-ESM, whole-scenario, actual
FAIR, crop-response, damage, and SCC gates therefore remain closed.
The first preregistered contiguous-support pilot fixes GFDL-ESM4 `r1i1p1f1`
under SSP1-2.6 and daily `pr`/`tas` for 2031--2060. Cross-year crop seasons
then yield 28 consecutive feature years (2032--2059), of which 2042--2049 have
ten real feature years on each side for a centered 21-year mean. Endpoint
padding and cross-gap smoothing are forbidden. This pilot remains insufficient
for whole-ESM, whole-scenario, multi-crop, joint-dependence, FAIR, response,
damage, welfare, or SCC promotion.
For the first bracketing decade, both 2031--2040 files match their official
byte counts and SHA-512 values and contain 3,653 complete midnight daily steps
with 946,857,600 finite values per variable, no missing values, and no negative
precipitation. Ten same-realization GMST rows and 5,488 seasonal plus 16,464
stage rows for harvest years 2032--2039 pass exact reconciliation. This does
not establish the still-incomplete 2031--2060 window.

A separately preregistered U.S. spatial sensitivity uses June 2019 because the
official NOAA county-average and registered gridded inputs were already locally
validated, and fixes nine production counties across nine state FIPS codes
before comparison. Exact official 3,107-county support and 30-day chronology
are required for PRCP/TAVG/TMIN/TMAX. The resulting 36 cells have minimum
defined daily correlation 0.999812; polygon-minus-official monthly rainfall
totals range from -0.830529 to +0.413524 mm. No equivalence threshold was
defined, yield outcomes were not read, and the polygon route was not replaced.
The subsequent temporal expansion holds the county sample fixed and adds
January and December 2019 to the preregistered June comparison. It requires
the same nine counties, four variables, official national support, exact month
lengths, and registered polygon weights in all three months. The resulting 108
cells all have nonzero maximum differences; minimum defined correlation is
0.999758, and polygon-minus-official monthly rainfall differences range from
-0.830529 to +0.619192 mm. No yield outcome or equivalence threshold enters
the selection or audit.

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
