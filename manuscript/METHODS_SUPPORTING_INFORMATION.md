# Methods Supporting Information

The dated methodological audit trail is preserved separately in [the Methods development log](METHODS_DEVELOPMENT_LOG.md). The main text and this SI retain only validated numerical claims; files under `data/raw`, `data/interim`, `data/processed`, and `outputs` are not part of the Git release.

## S1. Reproducibility scope

This document specifies a reproducible replacement for the temperature-indexed
agriculture pathway in GIVE. Raw data are excluded from Git; exact records are
stored in `data/provenance/`. The project has no wildfire inputs or code
dependencies.

### September 17 UKESM full-grid eight-year weather-window protocol

For UKESM1-0-LL `r1i1p1f2`, the source-locked ISIMIP3b 2041--2050 and
2091--2100 daily `pr`/`tas` blocks support crop-calendar-aligned rainfed
maize harvest years 2042--2049 and 2092--2099. Each scenario/year is
materialized as 36 ten-latitude-row tiles; the original source SHA-512,
tile hashes, calendar support, 21 raw daily-cell recomputations per year,
and a separate eight-year cross-year audit must all pass before any
summary is calculated. The three scenarios are SSP1-2.6, SSP3-7.0 and
SSP5-8.5. Season and three growth-stage rainfall totals, wet days,
maximum consecutive dry days, one- and five-day extreme rain, and mean
temperature are derived from the paired daily files. The season rain
must equal the sum of stage rain on every cell-year.

The six-window comparison was frozen in
`UKESM_SIX_WINDOW_WEATHER_DIAGNOSTIC_PROTOCOL_20260917.md` before its
cross-scenario statistics were calculated. It averages each feature
across eight harvest years within a calendar cell, then reports
equal-cell (not area- or production-weighted) differences between
scenarios within a window and between windows within a scenario.
Reported summaries are mean, median, 5th/95th percentile, and fraction
positive. Annual same-realization GMST is read only from the
SHA-256-pinned source receipt; its eight-year average is recorded
separately. A separate grouped-table recomputation checks the saved
contrast arithmetic. All work uses one worker at a time, <=512 MiB
sampled RSS, <=64 MiB new output, and >=130 GiB free disk. These short,
noncontiguous one-ESM weather windows cannot by themselves identify
forced precipitation per degree of global warming, global yield
effects or an incremental SCC.

All six eight-year cross-year audits subsequently passed. The full-grid
summary used `scripts/diagnose_ukesm_six_weather_windows.py`; an
independent grouped-table implementation in
`scripts/audit_ukesm_six_weather_window_arithmetic.py` reproduced all
315 saved statistics (seven contrasts, nine features, five summaries)
on the exact 67,420-cell support. The initial weather-summary and
arithmetic-audit runs encountered script handling errors for an older
audit schema, empty calendar tiles, and Pandas numeric dtypes. Their
resource receipts and logs were preserved; only these scripts were
corrected, with no daily-source or feature-file changes. The corrected
weather summary and arithmetic audit sampled 209.7 and 182.0 MB group
RSS, respectively. The result table, descriptive spatial spread,
checks and claim limits are in
`GLOBAL_DIRECT_DAILY_UKESM_SIX_WINDOW_WEATHER_RESULTS_20260917.md`.

### September 17 second-ESM late-window robustness

Before inspecting a multiyear IPSL weather contrast, we registered
IPSL-CM6A-LR `r1i1p1f1` as the alphabetical ESM with three already
resident and pinned 2091--2100 SSP `pr`/`tas` pairs and independently
checked 2092 rainfed-maize anchors. The same one-year tile builder and
21-cell daily-source auditor extended all three SSPs through
2093--2099, one worker at a time. Each scenario's eight-year
hash/calendar audit passed. Its weather summary used the identical
67,420 grid cells, nine season/stage features, and five per-feature
spatial summaries; an independent grouped-table audit reproduced
90/90 values. The pre-registered two-ESM merger compared 2092--2099
SSP3-7.0/5-8.5 with SSP1-2.6 **within** each ESM, then reported
two-ESM means, min--max, and sign agreement. A separately implemented
audit reproduced 112/112 merger values. Parent output and audit
SHA-256s are recorded in the ignored machine-readable reports.
The two-model range is not a confidence interval, scenario differences
are not small CO2 pulses, and an observed weather contrast is not an
identified crop response. Full findings and the opposite-sign
wet-day/early-stage results are retained in
`GLOBAL_DIRECT_DAILY_TWO_ESM_LATE_WEATHER_RESULTS_20260917.md`.

### September 17 third-ESM sign-stability check

The next alphabetically eligible already-resident ESM,
MPI-ESM1-2-HR `r1i1p1f1`, was registered before its multi-year
weather summary. Its three 2092--2099 SSP windows used the same
daily-source, 36-tile, 21 raw-cell/year and cross-year audits as
IPSL, with identical 67,420 rainfed-maize calendar cells. The
independent MPI grouped-table audit reproduced 90/90 summary
statistics. The frozen three-ESM merger stored each within-ESM
SSP-minus-SSP1-2.6 contrast, the simple model mean/range and sign
counts; a separate SHA-bound arithmetic implementation reproduced
114/114 comparisons. MPI has *negative* seasonal-rainfall contrasts
for both higher SSPs, reversing the two-ESM positive-total pattern,
while Rx1day/Rx5day remain positive in all three ESMs. The full
opposing signs are in
`GLOBAL_DIRECT_DAILY_THREE_ESM_LATE_WEATHER_RESULTS_20260917.md`.
The three-model range is not a confidence interval and cannot
replace held-out estimation of a forced GMT-to-feature response.

### September 21 five-ESM fixed-area late-window comparison

The source-bound late-century matrix was completed for five ESMs, three SSPs,
and harvest years 2092--2099. The 28 previously missing GFDL-ESM4 and
MRI-ESM2-0 annual panels used the same sequential 36-tile constructor and
independent 21-cell raw-daily validator as the existing UKESM, IPSL and MPI
panels. Each annual panel contains 67,420 calendar cells and 202,260 stage
rows. Separate eight-year source/hash/calendar audits passed for every newly
completed ESM-scenario series.

The agricultural summary fixes MIRCA-OS v2 year-2000 rainfed-maize area before
examining the five-model contrasts. Exact key intersection retains 30,654 of
30,821 positive-area crop cells and 99.9559% of mapped area identically across
all 120 ESM-scenario-year panels; missing cells are not imputed. Within each
ESM, the primary contrasts are the eight-year SSP3-7.0 and SSP5-8.5 means minus
the SSP1-2.6 mean. Area-weighted and equal-cell results are both retained.
Models remain named and unweighted and are not treated as probability draws.

An independent implementation rebound all 120 annual manifest/validation
pairs, reconstructed 2,160 annual ledger values and 180 scenario contrasts,
and performed 210 fixed source-tile checks. The primary aggregation and audit
sampled peak process-group RSS of 212,336,640 and 112,902,144 bytes. The exact
result and audit SHA-256 values, all model-specific contrasts, and
interpretation limits are in
`FIVE_ESM_MAIZE_AREA_WEATHER_RESULTS_20260921.md`. The comparison is a
late-century scenario/weather diagnostic, not a forced response per degree,
crop-yield response, damage estimate, or SCC input.

### September 22 five-ESM crop-calendar SPEI comparison

A separate bounded pipeline converts the same registered 2091--2100 daily
precipitation and mean temperature sources plus newly frozen daily minimum and
maximum temperature into crop-calendar climatic-water-balance exposure. The
extrema registry contains 30 exact ISIMIP3b objects (five ESMs by three SSPs
by two variables), with catalogue byte counts, SHA-512 identities, source
URLs, version, access and license metadata. The worker reads one global day at
a time, retains only the frozen 31,208-cell support, calculates daily
Hargreaves--Samani reference evapotranspiration, and aggregates monthly
precipitation minus ET0. It then applies the previously validated
observational 1982--2011 generalized-logistic parameters for SPEI-1/3/6;
future parameters are never refitted.

The crop-window step uses GGCMI calendars and fixed MIRCA-OS v2 hectares for
maize and soybean, harvest years 2092--2099, season, three stages, and a
90-day preplant window. Rainfed, irrigated and combined area summaries remain
parallel exposure bases, not irrigation treatment effects. Every case passes
an independent 24-cell monthly/scalar climate recomputation and a full 5,760-
comparison crop-window recomputation before its two newly acquired extrema
files are deleted. Exact source identities and reacquisition instructions are
retained in case-specific eviction receipts. The builders and validators use
one worker under a 512 MiB sampled process-group cap; the final MRI/UKESM
builder peaks remain below 399 MB.

The complete matrix contains 1,350 ESM--scenario--crop--window--scale--area
case means, 900 within-ESM scenario contrasts, and 180 named-model summaries.
A separate implementation reproduced them in 7,065 checks with zero
saved-precision disagreement. In the primary rainfed season SPEI-3 diagnostic,
SSP3-7.0 minus SSP1-2.6 differences are -0.617, -0.374, -0.380, -0.321 and
-0.552 for maize and -0.536, -0.276, -0.306, -0.138 and -0.374 for soybean
in GFDL, IPSL, MPI, MRI and UKESM. SSP5-8.5 differences are -0.885, -0.828,
-0.458, -0.438 and -0.701 for maize and -0.883, -0.786, -0.442, -0.098 and
-0.500 for soybean. Across the 45 window--scale--area cells per crop and
contrast, all five models are negative in 45/45 and 45/45 maize cells and
42/45 and 44/45 soybean cells; at least four are negative in every cell.

The exact validated evidence and hashes are in
`FIVE_ESM_LATE_DROUGHT_EXPOSURE_RESULTS_20260922.md` and
`data/provenance/five_esm_late_drought_public_evidence_20260922.json`.
These are scenario-exposure contrasts containing multiple forcing differences
and internal variability, not probabilities, confidence intervals,
anthropogenic attribution, per-kelvin or marginal-pulse responses, yield
effects, damages, or SCC inputs. The registered global predictive gate has not
promoted a drought response coefficient, so no SPEI contrast is monetized.

### September 22 drought--GMST endpoint diagnostic

Before inspecting any per-kelvin result, we froze an origin-constrained
endpoint response and two transport tests. For each of 90
crop--window--SPEI-scale--area cells, ten observations pair the SSP3-7.0 and
SSP5-8.5 SPEI differences from SSP1-2.6 with the corresponding
same-realization 2092--2099 mean-GMST differences. Named endpoints receive
equal weight. The fitted slope is `sum(deltaT*deltaSPEI)/sum(deltaT^2)`; a
zero intercept enforces zero scenario difference at zero temperature
difference. Whole-ESM folds fit eight endpoints and score the omitted two;
whole-scenario folds fit five and score five. A cell passes only if every
whole-ESM and both whole-scenario RMSEs are strictly below their zero-change
counterparts. No fold, tolerance, response form or weight changes after
results are allowed.

For primary rainfed crop-season SPEI-3, maize has a -0.187585 SPEI K-1 slope
and fitted/zero-change RMSE of 0.166923/0.586084. All five ESM holdouts and
both scenario holdouts improve, so maize passes the frozen internal rule.
Soybean has a -0.146942 SPEI K-1 slope and RMSE 0.230483/0.496789. It passes
both scenario holdouts but fails the whole-ESM rule: withholding MRI worsens
RMSE by 0.185471. Across all cells, 37/45 maize and 13/45 soybean records pass
the combined rule; all 90 pass both scenario holdouts. A separate
implementation recomputed every input mean, slope, point prediction,
residual, fold score and pass flag in 6,893 numeric checks, with maximum
disagreement `1.11e-16`.

The frozen protocol and complete result are in
`FIVE_ESM_DROUGHT_GMST_LINK_PROTOCOL_20260922.md` and
`FIVE_ESM_DROUGHT_GMST_LINK_RESULTS_20260922.md`. SSP contrasts contain
multiple forcing differences and internal variability. The five-model
holdouts reuse the same ensemble. The slope is therefore a descriptive
endpoint link, not attribution, a CO2-only or transient response, a FAIR
marginal-pulse mapping, yield effect, damage or SCC input.

### September 22 conditional GIVE/FAIR pulse sensitivity

We next froze a numerical interface test that uses only the primary maize
endpoint slope because soybean failed its whole-ESM rule. The full maize slope
and five leave-one-ESM-out training slopes are multiplied by each matched
core-GIVE FAIR pulse-minus-baseline temperature difference over 1750--2300.
No intercept, absolute-baseline application, clipping, weather generation or
yield response is permitted. The 0.0001, 0.00005 and 0.000025 GtC test pulses
share an identical baseline; the zero pulse and years through 2020 must remain
exactly zero, and the two smallest pulse-normalized signals must converge under
the existing FAIR tolerance.

For the full -0.187585 SPEI K-1 slope, the maximum absolute conditional
signals are `3.44564e-8`, `1.72284e-8` and `8.61420e-9` SPEI across the three
decreasing pulses. The maximum normalized signal is `3.44568e-4` SPEI per
GtC. The five leave-one-ESM slopes span -0.198124 to -0.168442 SPEI K-1.
An independent implementation recomputed all 13,224 row--slope products and
summaries in 52,933 numeric checks, with `8.88e-16` maximum disagreement.
The first audit caught that the evaluator used the stored FAIR difference
instead of recomputing pulse minus baseline; that failed record is retained,
and the corrected evaluator follows the frozen formula.

This is a deterministic conditional sensitivity, not a validated transient,
CO2-only or marginal climate-feature response. The source slope still contains
multi-forcing SSP differences, and no global drought-yield response is
promoted. Accordingly the interface opens no yield, damage, welfare or SCC
gate. Protocol and full limitations are in
`FIVE_ESM_DROUGHT_FAIR_SENSITIVITY_PROTOCOL_20260922.md` and
`FIVE_ESM_DROUGHT_FAIR_SENSITIVITY_RESULTS_20260922.md`.

### September 22 published global water-stress spatial validation

Before inspecting the published rasters, we froze a validation-only comparison
to Tuninetti and Davis (2026). Four official Zenodo outputs—maize and soybean,
each rainfed and irrigated—were acquired sequentially and verified against the
record's exact byte counts and MD5 hashes. Each 4320-by-2160 ESRI ASCII grid
was streamed six rows at a time and reduced to the ISIMIP 0.5-degree grid by
the mean of finite values in each 6-by-6 block. No expanded derived raster was
written. The source release contains code and outputs but is not turnkey: its
MATLAB scripts retain machine-specific paths and reference unbundled inputs
and helpers; the Zenodo metadata declares no license.

For each ESM and crop-regime cell, the existing GGCMI calendar constructs the
2092--2099 crop-season SPEI3 mean. SSP3-7.0 and SSP5-8.5 are differenced from
the same-ESM SSP1-2.6 value and then averaged across the five named ESMs.
Published loss severity is the negative historical median-to-tenth-percentile
ETa yield change; projected drying severity is the negative SPEI3 contrast.
Primary diagnostics are unweighted and MIRCA-hectare-weighted correlations of
midranks. The descriptive interval is a fixed-rank bootstrap with 2,000
resamples within four latitude strata; it does not remove spatial dependence
or incorporate climate-model and response uncertainty.

Common support ranges from 3,908 irrigated soybean cells to 18,574 rainfed
maize cells. Area-weighted mean SPEI3 is lower under both higher SSPs in all
four crop-regime combinations, but weighted spatial rank correlations span
-0.267 to +0.225 and change sign across irrigation regimes. An independent
implementation recomputed 450,966 numerical quantities and directly reread
twelve selected raw 6-by-6 raster blocks. The primary run peaked at 584 MB RSS
under a 640 MiB guard; the audit peaked at 190 MB. This passes an external
spatial-process-validation gate only. It supplies no empirical response,
damage, or SCC parameter.

Protocol, source audit, results and machine-readable evidence are in
`TUNINETTI_2026_SPATIAL_VALIDATION_PROTOCOL_20260922.md`,
`TUNINETTI_2026_GLOBAL_DROUGHT_BENCHMARK_AUDIT_20260922.md`,
`TUNINETTI_2026_SPATIAL_VALIDATION_RESULTS_20260922.md`, and
`data/provenance/tuninetti_2026_spatial_validation_public_evidence_20260922.json`.

### September 4 regional robustness additions

The source-hash-validated regional panel was fitted under original controls,
additional stage-average daily maximum-temperature linear/quadratic controls,
and a 2000–2018 period restriction. Both rainfall forms and both irrigation
practices were retained for corn/soybeans (24 fits). Protocol and scripts:
`us_county_validation/US_REPORTING_HEAT_SENSITIVITY_20260904.md` and
`us_county_validation/scripts/run_reporting_heat_sensitivity.py`.
An independent QR coefficient/covariance audit checked these 24 fits using
the same residualized design; it was not an independent sample replication.

For non-irrigated crops, a subsequent exploratory state-influence check
retained the previously selected crop-specific forms and omitted each state
under original and added Tmax controls (30 omissions plus four references).
Quantity contrasts use the unchanged full-sample median rainfall. This is
coefficient influence analysis, not held-out prediction or spatial inference.
See `us_county_validation/US_STATE_INFLUENCE_PROTOCOL_20260904.md` and
`us_county_validation/scripts/run_state_influence.py`. No omission-fit
uncertainty claims are made. Every omission and failure status is preserved.
Both analyses use existing inputs, sequential fits and the sampled job-group
memory monitor described in `LOW_MEMORY_WORKFLOW.md`.

### September 5 competing-moisture predictive sensitivity

The hash-verified common first-difference panel and original validation splits
were reused for an exploratory maximum-temperature sensitivity. Differences
of stage-average Tmax levels and of their squared levels were added to every
model family; no direct rainfall and PDSI features were stacked. Training-only
scaling and purging of shared outcome endpoints were retained. The 240
aggregate metrics cover both original and modified controls. These previously
examined splits are not independent confirmation. See
`us_county_validation/US_MOISTURE_TMAX_PROTOCOL_20260905.md` and
`us_county_validation/scripts/evaluate_moisture_tmax_sensitivity.py`.
The verified result weakens the earlier soybean distribution-promotion claim;
all split outcomes, including failed materiality criteria, are retained.
A preregistered pure-standard-library follow-up independently validates the
tracked aggregate JSON and its written claims without reopening raw/interim
panels or refitting. It requires exact 240-row metric support, eight summaries,
full-rank retained designs, endpoint-purge and sample-count reconciliation,
source hashes, and direct recomputation of every promotion comparison. The
saved reconciliation error is zero at artifact precision. This checks internal
aggregate-result integrity, not sample construction, exposure construction,
model fitting, or causal identification.

### September 6 continuous temporal benchmark

The retained assembly-hash-verified global maize/soy tables were read in
8,192-row batches and joined in ten-degree latitude bands on exact
crop/grid/year keys. Matched positive yields and consecutive years define
the common first-difference support. Training ends in 2010; terminal test
differences start in 2012, avoiding a shared 2011 outcome endpoint. Test
cells must have training differences. All models include stage mean
temperatures, crop-specific stage Tmax degree days, and deterministic year
terms; moisture families remain separate. Scale-normalized accumulated
cross-products yield aggregate test loss without storing global predictions.
See `GLOBAL_CONTINUOUS_TEMPORAL_PROTOCOL_20260906.md` and
`scripts/global_continuous_temporal_benchmark.py`. Full-record scPDSI
calibration makes this retrospective. No spatial inference or causal
interpretation is authorized by this diagnostic.

### September 7 geographic/source-cluster audit

Before evaluation, we froze five outcome-blind folds defined from 10-degree
latitude/longitude source blocks. Each fold is trained on 1983--2010
consecutive differences outside its blocks and scored on 2012--2016
differences inside them; 2011 endpoints remain purged, and terminal cells must
have at least one earlier consecutive difference. The five feature
specifications and exact three-family common support are unchanged. We read
one derived Parquet file at a time in separate historical and terminal blocks,
accumulate scale-normalized training cross-products, and suppress coefficients
and row predictions. Paired 5,000-draw PCG64 resampling retains all losses
within each selected 10-degree block and resamples blocks within folds. The
resulting percentile ranges are descriptive uncertainty conditional on the
five fixed fits, not causal confidence intervals or a full spatial-dependence
model. The aggregate result is byte-reproducible and used 394,936,320 bytes
peak sampled process-group RSS. See
`GLOBAL_CONTINUOUS_GEOGRAPHIC_CLUSTER_PROTOCOL_20260907.md` and
`scripts/global_continuous_geographic_cluster_audit.py`.

### September 7 U.S. daily heat-control construction

A single-county/year pilot first constructed daily Tmax exceedance in
Celsius-days and above-threshold days at 29 and 30 C, applying thresholds
cell-first before county-polygon weighting. All original stage Tmax means
and stage/season totals reconcile. The basis was then expanded to all 11,861
corn/soy county/crop/year keys in the 1981--2019 direct-practice support. The
1 GiB monitor stopped the full-year route in 1984; a frozen amendment used 149
disjoint groups of at most 64 counties, with a 453.1 MiB maximum peak. Exact
keys, calendars, hashes, weights and all 64 pilot values reconcile. An
exploratory sensitivity added stage heat sums and counts at 29 and 30 C
separately to every moisture model on the unchanged 20,228 differences.
Neither threshold retains the original soybean distribution promotion. See
`us_county_validation/US_DAILY_HEAT_EXPANSION_RESULTS_20260907.md`. These are
not hourly degree days, crop-pixel exposures or estimated damage responses.

## S2. Data acquisition and provenance

**September 7 daily-heat association update:** a separate exploratory
24-cell matrix preserves the original regional 1981–2018 county/state-year
fixed-effect model, adds stage heat-exceedance sums/counts with linear and
quadratic terms at either 29 or 30 C, and retains both crop/practice and
rainfall forms. Identical support is enforced. QR/triangular-solve covariance
reproduces baseline coefficients/SEs; county-cluster normal intervals remain
conditional, not full spatial/causal uncertainty. A subsequent 34-cell
non-irrigated state-influence matrix evaluates at unchanged full-sample
median rainfall. Protocols, aggregate outputs and tests are documented in
`us_county_validation/US_DAILY_HEAT_ASSOCIATION_RESULTS_20260907.md`.

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
For counties with numeric shares in all three vintages, a descriptive
outcome-free audit reports 2017--2022 10%-selector agreement of 92.28% for
corn, 92.64% for soybeans, and 84.16% for wheat. The corresponding correlations
are 0.938, 0.954, and 0.834. The primary 2017 selector is unchanged, while
wheat requires explicit vintage sensitivity; no irrigation effect, response,
damage, or SCC claim follows from this diagnostic.
A counts-only selector audit then reads only crop, county, year, fixed-share,
and eligibility fields from the locked 1981--2019 national panel. The
10/20/30% thresholds retain 20.80%/26.15%/29.30% of reported corn county-years
and 23.65%/27.97%/30.16% of reported soybean county-years. At 10%, annual
retained support spans 296--424 corn and 283--391 soybean counties. The audit
does not read yield magnitudes, change the primary 2017 selector, identify an
irrigation effect, or authorize response, damage, welfare, or SCC use.
A key-only companion audit intersects the two crop panels without reading
yield magnitudes. At the primary 10% selector it retains 9,715 common
corn/soybean county-years across 264 counties, or 66.30% of the smaller
selected crop panel. Annual overlap ranges from 161 to 263 counties and the
county-set Jaccard index is 0.475. The 20% and 30% sensitivities retain 12,968
and 14,559 common county-years. These counts define feasible joint-crop support
only; they do not identify an irrigation effect or response.
The companion outcome-blind state-FIPS audit retains 28 of 41 reported corn
states and 28 of 31 reported soybean states at the 10% selector. Top-five-state
county-year shares are 42.96% and 42.15%, respectively. This result fixes
state/region-blocked holdouts as a necessary national validation gate without
reading yield magnitudes or altering the selector.
We also preregistered a count-only feasibility audit for a distinct
practice-specific **state** terminal panel. Fifty-six exact Quick Stats count
queries cross corn/soybean, irrigated/non-irrigated practice, and 2012--2025.
The frozen 2020--2025 gate requires at least eight state rows each year and 60
state-years per crop/practice. Corn returns one row per terminal year for each
practice and soybean returns none, so all four series fail before values are
downloaded. The credential-safe query builder and separate structural auditor
verify the 56-query matrix and key exclusion; no yield value, response, or
weather alignment is produced. Protocol and full counts are in
`US_STATE_DIRECT_PRACTICE_TERMINAL_SUPPORT_PROTOCOL_20260921.md` and
`US_STATE_DIRECT_PRACTICE_TERMINAL_SUPPORT_RESULTS_20260921.md`.
A distinct 24-query Census feasibility audit tests whether 2012, 2017, and
2022 county production and harvested area can be matched within crop and
reported practice. Irrigated corn area has 1,591--1,852 rows by wave, but the
corresponding production queries have none; every tested non-irrigated corn
and soybean practice cell also lacks matched quantities. Zero of 12 cells
passes the fixed count gate, so no values or yield ratios are constructed.
See `US_CENSUS_DIRECT_PRACTICE_OUTCOME_SUPPORT_PROTOCOL_20260921.md` and
`US_CENSUS_DIRECT_PRACTICE_OUTCOME_SUPPORT_RESULTS_20260921.md`.
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

A complete bounded acquisition recorded all 468 canonical monthly objects
for 1981--2019, totaling exactly 27,857,685,556 bytes (25.944 GiB). Before each
object entered the atomic local manifest, the utility required the frozen HTTP
identity and exact byte length, computed a local SHA-512, and validated the
NetCDF schema, four required fields, embedded product metadata, day-label
semantics, and exact daily date coverage. Every resume invocation revalidated
all already manifested objects; a changed upstream identity, local hash,
schema, or calendar failed closed. On 21 September 2026, after the complete
content receipt and HTTP inventory had been frozen, the 468 raw grid files were
deleted to recover 25.944 GiB of local storage. The acquisition utility can
recreate them from the retained URLs and verifies every replacement against
the retained SHA-512 checksums. The official daily county-average source,
derived panels, validation receipts, and student-share extract were not
deleted. Raw and interim data remain Git-ignored. These checks establish a
reproducible historical-weather input, not a county exposure, predictive
relationship, causal response, or SCC term.

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

A parallel literature-based climate input does **not** require that we
re-estimate a new GMT--rainfall relationship. Published PEEPS monthly
grid-cell patterns may be applied to matched FAIR temperature paths for
crop-season rainfall amount and monthly shares, subject to exact version,
grid, unit, reference-temperature, positivity, out-of-scenario and
small-pulse checks. The source archive packages the patterns in a single
3,244,457,764-byte file, which is not locally staged under the current
resource rules. Our two-ESM PEEPS-style regressions below are a separate
methodological test, **not** the published author coefficients. MESMER-M-TP
is a published positive monthly alternative, but the MESMER v1.0.0 public
pre-calibrated parameter set excludes precipitation and the TP component is
not yet integrated in that software release. A separately published
MESMER-X Rx1day emulator covers annual maximum one-day precipitation,
not daily rainfall sequences. Neither monthly system can identify daily
dry spells or rainfall tails from monthly means; Rx1day alone cannot
identify the missing daily sequence either. The precise import and
non-overlap gates are recorded in
`PUBLISHED_GMT_RAINFALL_IMPORT_ROUTE_20260917.md` (Kravitz and Snyder,
2023, doi:10.1371/journal.pclm.0000159; Schöngart et al., 2024,
doi:10.5194/gmd-17-8283-2024; Bauer et al., 2026,
doi:10.5194/gmd-19-5669-2026; Pierini et al., 2026,
doi:10.1088/1748-9326/ae5fad). The later literature and usable-input
screen is `PUBLISHED_POSITIVE_AND_EXTREME_RAIN_EMULATOR_REVIEW_20260918.md`.

We separately evaluated the author-released EPA country-level annual
precipitation patterns at repository commit
`dac5503549d5158e0257894012293acff45c0cb4`. The source contains five repeated
socioeconomic labels for each country/model slope. We require exact identity
across those labels before deduplicating; 4,703 of 4,784 country/model pairs
are finite and 81 pairs are unavailable under every label. Unavailable slopes
remain missing. The resulting support covers all 184 GIVE countries, with
19--26 available climate models per country. A second standard-library
implementation reconstructs the country distributions and passes 2,433
support and numeric checks. Exact source/code hashes and results are recorded
in `EPA_ANNUAL_COUNTRY_PATTERN_PROTOCOL_20260921.md` and
`EPA_ANNUAL_COUNTRY_PATTERN_RESULTS_20260921.md`.

For country `c`, climate model `m`, year `t`, and carbon-pulse size `p`, the
annual pulse benchmark is

`delta_precip[c,m,t,p] = beta[c,m] * (T_pulse[t,p] - T_baseline[t])`,

where `beta` is the published area-weighted annual slope in
mm yr-1 K-1. The implementation adds no intercept and invents no baseline
precipitation. It requires the exact validated 1750--2300 core-GIVE FAIR
temperature product, identical baseline temperatures across pulse cases,
zero-pulse identity, no path divergence through 2020, and three positive pulse
sizes. It reports the country/model distribution for six selected years and
tests convergence after normalizing the two smallest positive pulses by pulse
size. A separately coded csv/math implementation reproduces every selected
scalar and convergence diagnostic (256 checks). This is an annual-quantity
climate-input benchmark only; no baseline rainfall, daily sequence, crop
response, monetary loss, discounting, or SCC is calculated. The registered
contract and validated result are in
`EPA_FAIR_ANNUAL_PRECIPITATION_PULSE_PROTOCOL_20260921.md` and
`EPA_FAIR_ANNUAL_PRECIPITATION_PULSE_RESULTS_20260921.md`.

The initial author-released MPI-ESM1-2-HR/SSP5-8.5/December `pr`
coefficient NetCDF was extracted by bounded streaming and structurally
validated (1,196,250 bytes, 192 by 384 finite native-grid coefficients).
Subsequently, all 3,244,457,764 bytes of the release archive were
streamed without retaining the archive and its outer MD5 matched the
Zenodo record. All twelve MPI monthly coefficient files (14,355,000
bytes total) were retained and individually validated. These are source
integrity steps, not crop-year projections; FAIR predictor alignment,
positive rainfall, and held-out performance remain separate gates. See
`PUBLISHED_PEEPS_FULL_MONTH_INPUT_RESULTS_20260917.md`.
The matching 86-year author GMST series was then source-matched and the
author's own December pattern formula evaluated at four years. It yielded
109, 13, 0 and 782 negative predictions among 73,728 native global cells
(including ocean) in 2015, 2030, 2050 and 2100, respectively; a 50-digit
Decimal sentinel audit passed. This fails an unqualified global positivity
claim, not a crop-area test, and does not establish predictive skill or
justify clipping. The source/physicality diagnostic and its limits are
documented in the same pilot report.
A preregistered follow-on nearest-center MIRCA2000 rainfed-maize support
screen maps the same published December predictions to 30,821 positive-area
0.5-degree crop cells. The author formula is negative on the source cell
nearest to 0.9038%, 0.1222%, 0% and 0.7355% of mapped rainfed-maize
hectares in those four years. The point-center mapping is not conservative
area overlap or a crop-calendar exposure; no crop effect follows from
this result. See `PUBLISHED_PEEPS_CROP_SUPPORT_POSITIVITY_RESULTS_20260917.md`.
The all-month screen then found that raw published linear levels predict
at least one negative month on 2.856%, 0.322%, 0%, and 9.879% of mapped
rainfed-maize area in 2015, 2030, 2050, and 2100, respectively. The
source-matched reconstruction diagnostic compared all twelve PEEPS
months in 2015 and 2100 with the two-member arithmetic mean of direct
MPI SSP5-8.5 precipitation. Its four source-chunk workers passed the
frozen checksums and 512 MiB cap; independent saved-array arithmetic
then passed 214 scalar comparisons. Area-weighted annual-total RMSE
was 131.843 and 147.021 mm in 2015 and 2100, respectively, with
month-share TV errors 0.126917 and 0.142917 on within-year physically
valid area. For a *post-result* temporal diagnostic, one fixed
cross-year valid area (88.266% of mapped area) gives a +34.172 mm direct
rainfall change versus a +43.612 mm published-pattern change between
2015 and 2100. This same-SSP comparison is **in-sample**, not a
held-out climate emulator evaluation, and neither the invalid raw
rainfall levels nor these crop-center metrics are promoted to yields,
damages, or SCC. Exact sources, full monthly accounting, failed memory
attempts, and audit scope are in
`PEEPS_MPI_SSP585_RECONSTRUCTION_RESULTS_20260918.md`.
In a frozen *post-level-result* extension, we retain all mapped crop
centers, including those with negative published monthly levels, and
compare 2100-minus-2015 monthly changes. Summing months gives annual
amount change. Subtracting one-twelfth of each cell's annual change from
each monthly change isolates within-year redistribution in calendar-month
amounts. The area-weighted squared monthly-change error decomposes
orthogonally into the squared annual-error-per-month component and the
squared redistribution component. The 72-value scalar independent audit
passes; exact inputs, equations, source hashes, results and physicality
limitations are in `PEEPS_MPI_CHANGE_DECOMPOSITION_PROTOCOL_20260918.md`
and `PEEPS_MPI_CHANGE_DECOMPOSITION_RESULTS_20260918.md`. It is not a
crop-calendar, held-out emulator, yield, damage or SCC calculation.
An additional source-matched anomaly test anchors each month to the
direct two-member 2015 rainfall and adds the published 2100--2015
monthly change, without clipping. The no-change predictor retains
direct 2015. On all 30,821 mapped centers, the anchored calculation
still generates 29,529 negative month-center values, affecting
33.962% of mapped area, so it is rejected as a physical forcing even
though its all-area mean-square errors beat no change. Month-share
comparison is restricted to the common valid 66.038% area. The
pre-analysis formula, failed initial share-index attempt, corrected
run, 14-value independent scalar audit, and source hashes are retained
in `PEEPS_MPI_BASELINE_ANOMALY_PROTOCOL_20260918.md` and
`PEEPS_MPI_BASELINE_ANOMALY_RESULTS_20260918.md`.
For a twenty-year source-bound climatological check, we stream only the
six source time chunks needed for 2015--2034 and 2081--2100, with two
MPI SSP5-8.5 members. Each chunk is checksum-verified, decoded under
the 512 MiB worker gate, and reduced to twelve crop-center monthly
sums and counts; exactly twenty years per month/member/period must
reconcile. Published monthly predictions are calculated **per year**
from the author absolute-GMST series and that year's actual month length,
then averaged, not evaluated at a mean year. The original v1 share
scores used different period-specific positive supports; v2 preserves
that receipt and adds a fixed intersection of 92.814% mapped area for
both period-share scores. An independent audit reconstructs six input
partials, four full matrices, 14 physicality values and 72 change
statistics. The exact extraction, sources, formulas, resource limits,
results and invalid-negative-rainfall gate are in
`PEEPS_MPI_20YR_CLIMATOLOGY_PROTOCOL_20260918.md` and
`PEEPS_MPI_20YR_CLIMATOLOGY_RESULTS_20260918.md`. These are monthly
calendar-year climatologies, not a daily or crop-year forcing.
For the direct-daily crop-relevant climate route, we fix MIRCA-OS v2
2000 rainfed-maize harvested-area weights at exact `(lat,lon_360)`
keys and demand a stable 30,654-cell intersection across UKESM/IPSL/MPI,
three SSPs and harvest years 2092--2099. The retained area is
99.9559% of the original positive-area crop map; unmatched cells are
reported, never imputed. Each of 72 independently validated global
source panels contributes 36 hash-checked tiles, unique season rows
and three stage rows with additive precipitation. For season amount,
stage rainfall, wet days, longest dry spell, Rx1day, Rx5day and mean
temperature, we divide area-weighted tile numerators by one fixed
matched-area denominator, average the eight annual means equally,
and difference each higher SSP from SSP1-2.6 within ESM. An equal-cell
mean on **the same matched support** isolates the role of area weights.
The separate auditor recomputes 1,296 annual and 108 contrast scalars,
plus 147 fixed source-tile checks, with 72 manifest/validation bindings.
Exact support, source hashes, assumptions and no-causal-claim boundary:
`GLOBAL_THREE_ESM_MAIZE_AREA_WEATHER_PROTOCOL_20260918.md` and
`GLOBAL_THREE_ESM_MAIZE_AREA_WEATHER_RESULTS_20260918.md`.

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
An external source/period-matched sign diagnostic for wet-day frequency and
conditional wet-day intensity is Feldman et al. (2026,
doi:10.1029/2025GL120745): their four observation-based 1980--2020 products
and 27 CMIP6 SSP5-8.5 2020--2099 projections use >1 mm/day wet days over
land from 60 S to 60 N. Their prevalence result is not an anthropogenic
attribution or numerical GMT response, and all-sign and jointly significant
trend shares must not be conflated. We do not tune a climate driver to match
this study or extrapolate its land-area shares to crop-harvested area.
Aggregate growing-season precipitation results are additionally benchmarked
against OSCAR-crop v1.0; that published model does not validate daily timing
or extreme-weather effects.

Annual precipitation totals receive a second external check against the
USEPA `pattern-scaled-climate-variables` repository at reviewed commit
`dac5503549d5158e0257894012293acff45c0cb4`. Its scripts read precomputed PEEPS
annual precipitation--GMST slopes and aggregate them to 184 GIVE countries
with area, GDP, or population weights. Our exact comparison first reproduces
area-weighted annual country slopes on common units, then checks the three
overlapping primary ESMs (MPI-ESM1-2-HR, MRI-ESM2-0, and UKESM1-0-LL) and the
broader EPA ensemble distribution. Crop harvested-area/value weights remain
the agricultural default. A separate outcome-blind sensitivity may pair FAIR
draws and spatial patterns by 2100 GMST rank, following the logic of the EPA
temperature workflow; same-realization ESM/member construction remains
primary. Neither benchmark supplies daily timing, drought, crop response,
welfare, or SCC evidence.

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

The aggregate evidence decision is applied after the country-held-out yield,
future-support, and GMST-normalized climate diagnostics. Production promotion
requires a new independent untouched holdout, five valid country folds for
both crops, improvement on pooled and equal-country RMSE, and paired 95% upper
bounds below zero. Quantity must beat heat controls and zero change;
distribution and drought families must beat quantity. No family passes. The
six-endpoint physical sign agreement for wet days, maximum dry spell, Rx1day,
and Rx5day retains those climate diagnostics but cannot override the failed
yield-response gate. Exact rules, source hashes, the retained first-pass fold-
label error, and the independent audit are in
`GLOBAL_RESPONSE_EVIDENCE_DECISION_RESULTS_20260919.md`.

The U.S. synthesis separately binds source-matched common-range associations,
paired county-bootstrap predictive losses, and the stage-Tmax control
sensitivity. It preserves the different sign conventions: negative candidate-
minus-reference loss favors the candidate, while positive summary improvement
does so. The aggregate-only independent audit repeats 136 checks without reading
county outcomes, coefficients, predictions, or raw weather. Results prioritize
non-irrigated corn PDSI and retain distribution as a sensitivity, but prohibit
causal interpretation or global transfer. See
`US_NASS_EVIDENCE_SYNTHESIS_RESULTS_20260919.md`.

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

As of September 16, 2026, the isolated Julia 1.8.5 suite
`test/runtests.jl` passes 60/60 tests using this project's local depot
(`JULIA_DEPOT_PATH=.julia_depot julia --project=. test/runtests.jl`). The
guarded execution sampled 791,134,208 bytes maximum process-group RSS;
the log and receipt remain in ignored `data/interim/`. These are component
and interface tests, not an empirical GIVE marginal-damage run.

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

### S7 additional engineering boundary: already-monetized annual damages

The existing fractional-loss adapter multiplies its input by agricultural
income. Already-valued monetary welfare losses must instead use a separate
pass-through interface. The synthetic-only Python contract accepts annual,
undiscounted USD2005, normalizes dollars to billions and an explicitly declared
welfare-positive sign to damage-positive exactly once. It preserves negative
net damages, rejects incomplete or reordered axes, and requires path/draw
identities. No deflator, adaptation, GDP scaling or discounting is implemented.

A separate native Mimi adapter has passed27 synthetic assertions against the
read-only original GIVE DamageAggregator source after verifying its SHA256.
Positive regional money contributes positively to global damage after the
aggregator's multiplication by1e9. GDP doubling leaves absolute damage
unchanged. Excluding agriculture removes its contribution to total damage,
and the structural audit rejects a surviving legacy Agriculture component.
The Python contract passed seven test groups. These are minimal-model software
tests, not an executed full-model replacement, empirical welfare calibration,
or SCC result. Exact scope, reproducible scripts and bounded resource receipts
are in `MONETARY_ADAPTER_ENGINEERING_RESULTS_20260908.md`. The prototype accepts
only explicitly synthetic inputs. A separate cross-language transport test
passed14Julia assertions plus Python overwrite and axis-rejection checks.
Versioned TOML carries normalized money and source/draw/path identities together.
The Julia loader records the exact input SHA256 and rejects incompatible
fields, units and axes. These tests use artificial arrays throughout and do
not establish that matched path identities represent a causal CO2 experiment.

The final synthetic topology control executes the adapter in a copied full GIVE
model under the archived Julia environment. Twenty assertions verify fail-closed
replacement, exact original source hashes, preservation of all nonagricultural
connections and sector flags, regional/global/domestic monetary identities, and
invariance of mortality and energy outputs to a zero-money rerun. The original
caller model retains its legacy Agriculture component. These tests establish
software wiring only; all monetary inputs are artificial and the run contains
no marginal CO2 experiment, welfare calibration, discounting or SCC estimate.

## S8. Uncertainty and sensitivity

### S7 baseline value proxy ledger

For maize, we form a baseline value only when all1999--2001 FAOSTAT constant
2014--2016USD observations are present. The national three-year arithmetic mean
is allocated across rainfed and irrigated systems in proportion to fixed
MapSPAM full production. Common-response value support is the national mean
multiplied by common system production divided by total country production.
This production-proportional construction conserves national value but does not
observe regime-specific prices or revenue. Missing countries and unsupported
production remain separate; no renormalization, zero fill or deflation occurs.

The resulting150-country/231-regime ledger has143.163billion source-basis value,
of which130.471billion (91.135%) is represented on common physical-response
support. Five country codes lack an archived GIVE FUND mapping and remain
unmapped. Three synthetic tests and2,118 independent checks pass. These totals
are baseline value proxies, not damages. Empirical export remains disabled until
the market, surplus, adaptation and USD2005 conversion rules are registered.
Full methods and corrected failure history are reported in
`WELFARE_BASELINE_LEDGER_RESULTS_20260914.md`.

We separately register27 prospective welfare scenario identities from three
market geographies, three published elasticity assumption pairs and all three
adaptation cases. Country markets and the0.10/−0.04 pair are proposed central
settings; broader markets and the other pairs remain sensitivities. This
registry performs no economic calculation. Its loader rejects empirical use
until the expectation, realized surplus, USD2005 conversion and adaptation
accounting gates are resolved. Three test groups verify complete identities and
fail-closed behavior; see `WELFARE_SCENARIO_REGISTRY_RESULTS_20260914.md`.

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

### S9.18 September 22 published-structure U.S. drought benchmark

The design was frozen before national USDM acquisition. It uses positive
all-production-practices NASS corn and soybean yield during 2001--2013; county
and harvest-year fixed effects; state-specific linear trends; and separate
dryland/irrigated county-support fits. The irrigation classifier follows the
published all-cropland rule rather than the project's crop-specific selector:
for each county, compute irrigated harvested cropland divided by all harvested
cropland in each available 1997, 2002, 2007, and 2012 Census, take the maximum,
and label values greater than 0.15 irrigated. Suppressed/absent numerators are
missing, never zero. Exact-equality cases do not occur. The resulting 2,913
eligible counties differ by four from the paper's 2,909 summary count.

The official USDM county-statistics endpoint is acquired as 533 bounded
state-year responses with URL, retrieval time, byte count, and SHA-512. A
streaming builder assigns each map to its map-date year while retaining the
pre-2001 map needed to cover 1 January 2001. It writes 2,055,640 unique
county-weeks in 533 Parquet row groups at 173 MiB peak RSS. Among all inputs,
only Chippewa County, Michigan on 22 June 2010 violates the 0.15-point category-
sum tolerance (102.55%). A config-bound correction proportionally renormalizes
that one working row; the raw source remains unchanged and checksummed, and any
additional or changed anomaly fails.

Calendar-year exposures integrate each mutually exclusive category fraction
over exact validity-interval days and divide by seven. Coverage must begin 1
January, end 31 December, and be gap/overlap free for every county-year. The
annual six-category reconciliation tolerance is 0.08 week, conservatively
derived from the already enforced weekly rounding tolerance; observed maximum
error is 0.0028 week. The resulting 78,598 crop-county-years explicitly carry
`source_area_basis=county_area`, because the REST product does not reproduce the
paper's agricultural-area intersection.

For each crop/support class, log yield is regressed on D0--D4 equivalent weeks.
Fixed effects and trends are absorbed with a sparse nuisance design and LSMR;
the five residualized slopes are solved by Frisch--Waugh. Provisional CR1
covariance clusters by county. A separate validator solves one joint sparse
design containing nuisance and drought columns, reproducing the 20 slopes to a
maximum absolute difference of `1.55e-11`; it also checks covariance symmetry,
positive semidefiniteness, standard-error diagonals, hashes, sample counts, and
claim boundaries. Peak fit and validation RSS are 362 and 358 MiB.

All category estimates are negative and every dryland coefficient is more
negative than its same-crop/same-category irrigated counterpart. This supports
the external qualitative drought/irrigation ordering, but it does not identify
causality or authorize global transport. The subsequent April--September
weather hierarchy is reported below; agricultural-area USDM weights, the
paper's degree-day construction, and spatial-correlation-robust inference
remain advancement gates. Reproduction is bound by
`US_USDM_KUWAYAMA_REPLICATION_PROTOCOL_20260922.md`,
`US_USDM_DROUGHT_ONLY_RESULTS_20260922.md`, and the corresponding
`download/prepare/aggregate/estimate/validate` scripts.

The pre-result weather hierarchy uses the identical 41,000 common rows. NOAA
daily county-average precipitation, mean temperature, and Tmax are reduced over
1 April--30 September. Weather-only and drought-plus-weather models include
rainfall/100 mm, its square, mean temperature/10 C, and crop-threshold Tmax
exceedance/100 C-days (29 C corn; 30 C soybean). These controls are compatible
with the project weather route but are not the paper's agricultural-area
moderate/extreme degree-day reconstruction. Neither family is selected by
significance or implied damages.

Weather raises within-fit explained variation and attenuates most drought
coefficients. Negative D1--D4 associations remain for both dryland crops; D0
does not. Irrigated corn retains only a negative D4 association, while irrigated
soybean is mixed and retains a negative D3 term. The quantity-only rainfall
polynomial is concave for both dryland crops: +100 mm contrasts decline across
the observed rainfall quartiles and turn negative at the upper corn quartile.
Eight independent joint sparse-design solutions agree with the absorbed
estimator within `1.22e-08`. These results support the competing-moisture and
non-stacking rule: composite drought mostly overlaps direct weather but can
retain residual information; neither representation creates an additive SCC
sector.
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
padding and cross-gap smoothing are forbidden. All six files pass complete
source/content validation; the eight centered outputs retain same-realization
GMST and reconcile additive stage/season precipitation and wet-day means to
numerical precision. This pilot remains insufficient
for whole-ESM, whole-scenario, multi-crop, joint-dependence, FAIR, response,
damage, welfare, or SCC promotion.
The complete 2031--2060 input has 10,958 complete midnight daily steps per
variable. The bounded panel contains 19,208 seasonal plus 57,624 stage rows
for every harvest year 2032--2059 and passes exact unsmoothed reconciliation.
The centered operation emits only the eight complete registered windows.

The joint-dependence extension is registered before fitting. It uses ECC-Q
(Schefzik et al., 2013) to reorder 51 separately mapped marginal samples by
the empirical ranks of complete climate-model templates. A template is one
indivisible ESM--member--scenario--center-year field across cells, crops,
irrigation regimes, stages, and linked features; held-out ESM or scenario
templates never enter training. Physical coordinates use log seasonal rain,
epsilon-open logits for wet frequency, dry-spell fraction, Rx5/total, and
Rx1/Rx5, identity temperature, and two reversible additive-log-ratios for
stage-rain composition. Derived timing and concentration are reconstructed,
not sampled independently. The synthetic gate reproduces marginal multisets
and rank correlations exactly and preserves the rainfall ordering and unit-sum
composition. The current eight-template pilot is below the fixed 51-template
minimum; no empirical coupling, FAIR feature response, or SCC use is opened.

Before constructing additional contiguous features, a separate contract fixes
the complete Cartesian product of maize, soybean, first- and second-season
rice, spring wheat, and winter wheat with `noirr` and `firr` calendars on the
same bounded GFDL realization. All 12 calendar hashes, valid-cell counts,
2032--2059 annual support, 2042--2049 centered support, and same-realization
GMST identity are required. The audit passes 214,928 seasonal and 644,784
stage rows before centering and 61,408 seasonal and 184,224 stage rows after
centering. It also handles leap-year changes in cross-year season/stage
durations by averaging that geometry within the registered window. The paired
calendar comparisons are descriptive calendar sensitivity only and do not
identify irrigation treatment effects.
The preregistered replications replace only the scenario label with SSP3-7.0
or SSP5-8.5 while retaining GFDL-ESM4 `r1i1p1f1`, the six crop/calendar
definitions, and the same 2031--2060 and 2042--2049 support rules. All twelve
additional daily files pass catalogue byte/SHA-512 and decoded-content checks.
Each deterministic scenario audit again passes 214,928 seasonal and 644,784
stage rows before centering and 61,408 seasonal and 184,224 stage rows after
centering, with one common same-realization GMST identity across all 12 cells.
Byte-identical audit reruns pass. The three completed GFDL scenarios therefore
supply 24 centered templates, still below the 51-template dependence threshold
and with no held-out ESM; response, damage, welfare, and SCC gates remain
closed.
The first cross-ESM replication binds IPSL-CM6A-LR `r1i1p1f1` SSP1-2.6 to
six version-`20210512` daily files covering 2031--2060. All six pass exact
catalogue byte/SHA-512 and full decoded-content checks. A 30-row annual GMST
series is computed from those same temperature files. The preregistered
12-cell feature build passes 214,928 seasonal and 644,784 stage rows before
centering and 61,408 seasonal and 184,224 stage rows after 21-year centering;
every cell shares the same centered GMST identity and the aggregate audit is
byte-identical on rerun. With 24 GFDL and eight IPSL centered templates, the
available 32-template design remains below the 51-template dependence minimum
and cannot support a balanced whole-ESM or whole-scenario exclusion.
The corresponding IPSL-CM6A-LR `r1i1p1f1` SSP3-7.0 cell binds six more exact
version-`20210512` daily files covering 2031--2060. Full checksum, decoded
content, chronology, 30-row same-realization GMST, and every preregistered
12-cell feature and reconciliation gate pass. The build adds 214,928 seasonal
and 644,784 stage rows before centering and 61,408 seasonal and 184,224 stage
rows after 21-year centering; its aggregate audit reproduces byte-identically.
The matching SSP5-8.5 cell then binds and validates six additional files and
passes the same GMST, row-count, reconciliation, and deterministic-audit gates.
Its `firr` minus `noirr` centered seasonal-rain differences range from -25.94
to +12.50 mm across crops, with both rice pairs identical; these remain
calendar-date sensitivities rather than irrigation effects. Together the two
complete three-scenario ESMs provide 48 centered templates. An exact-key
2032--2059 SSP5-8.5-minus-SSP1-2.6 comparison passes for all 12 cells; mean
temperature changes range from +0.580 to +0.836 C and seasonal-precipitation
changes from -5.07 to +12.62 mm. These are climate-feature comparisons, not
response estimates. The matrix is below the 51-template dependence minimum;
holding out either ESM retains only 24 training templates, and holding out one
scenario retains 32, so whole-ESM and whole-scenario response validation remain
closed.
The next preregistered cell adds MPI-ESM1-2-HR `r1i1p1f1` SSP1-2.6. Its six
version-`20210512` files pass exact bytes/SHA-512, full decoded daily-content,
and model-specific noon-chronology checks; the same temperature realization
yields 30 annual GMST rows. The deterministic 12-cell build passes 214,928
seasonal, 644,784 stage, 61,408 centered-seasonal, and 184,224 centered-stage
rows, exact reconciliation, and a byte-identical aggregate-audit rerun.
Calendar-only `firr` minus `noirr` seasonal-rain differences range from -22.48
to +14.72 mm, with identical rice pairs. This brings the partial matrix to 56
templates but does not satisfy the registered holdout design: an MPI exclusion
retains 48 templates, a GFDL or IPSL exclusion retains 32, and an SSP1-2.6
exclusion retains 32. Joint-dependence fitting and all response, damage,
welfare, and SCC uses remain closed.
The matched MPI SSP3-7.0 replication passes the same six-file checksum and
decoded-content gates, 30-row same-realization GMST, 12-cell raw/centered
feature reconciliation, and byte-identical aggregate-audit rerun. Its
214,928/644,784 raw and 61,408/184,224 centered rows add eight templates;
calendar-only `firr` minus `noirr` seasonal-rain differences range from -21.76
to +11.22 mm, with identical rice pairs. Across 64 templates, every whole-ESM
or whole-scenario exclusion retains only 40--48, below the locked 51-template
minimum, so joint dependence and all response, damage, welfare, and SCC gates
remain closed.
The preregistered MPI SSP5-8.5 cell then passes all six exact checksum and
decoded-content gates, a 30-row same-realization GMST, the same 12-cell
raw/centered feature and exact-reconciliation gates, and a byte-identical
aggregate-audit rerun. It contributes the same 214,928/644,784 raw and
61,408/184,224 centered row counts. Calendar-only `firr` minus `noirr`
centered seasonal-rain differences are +0.85 mm for maize, -14.35 mm for
soybean, zero for both rice seasons, +12.62 mm for spring wheat, and -23.99 mm
for winter wheat. The partial matrix contains 72 templates, but every
whole-ESM or whole-scenario exclusion retains 48, below the locked 51-template
minimum. Joint dependence and all response, damage, welfare, and SCC gates
therefore remain closed.
The MRI-ESM2-0 `r1i1p1f1` SSP1-2.6 cell subsequently passes the same six-file
checksum/content, 30-row same-realization GMST, 12-cell raw/centered,
exact-reconciliation, and byte-identical aggregate-audit gates. It contributes
the same row counts. Calendar-only `firr` minus `noirr` centered seasonal-rain
differences are +0.84 mm for maize, -15.19 mm for soybean, zero for both rice
seasons, +13.80 mm for spring wheat, and -28.16 mm for winter wheat. The 80
templates leave 56--72 after whole-ESM exclusions and 56 after SSP3-7.0 or
SSP5-8.5 exclusion, but only 48 after SSP1-2.6 exclusion. The balanced matrix
remains incomplete, so joint dependence and all response, damage, welfare, and
SCC gates remain closed.
The MRI-ESM2-0 `r1i1p1f1` SSP3-7.0 cell subsequently passes the frozen
six-file checksum/content, 30-row same-realization GMST, 12-cell raw/centered,
exact-reconciliation, and byte-identical aggregate-audit gates. It contributes
214,928 seasonal, 644,784 stage, 61,408 centered-seasonal, and 184,224
centered-stage rows. Calendar-only `firr` minus `noirr` centered seasonal-rain
differences are +0.92 mm for maize, -15.78 mm for soybean, zero for both rice
seasons, +13.08 mm for spring wheat, and -22.93 mm for winter wheat; they do
not identify irrigation effects. The 88 available templates leave 64--72
training templates after excluding a represented ESM and 56--64 after
excluding a scenario, above the locked 51-template minimum in every currently
represented exclusion. UKESM1-0-LL nevertheless has no contiguous feature
templates, so the balanced five-ESM matrix is incomplete and joint dependence,
holdout promotion, response, damage, welfare, and SCC gates remain closed.
We next preregistered a represented-template dependence-stability diagnostic
before reading its outputs. Each of the 88 ESM--scenario--center-year templates
contains 7,676 aligned crop-calendar cells. Seasonal rain, wet frequency,
maximum dry-spell fraction, Rx5/total, Rx1/Rx5, temperature, and two stage-rain
additive-log-ratio coordinates are constructed from the centered derived
files. The implementation reads one season/stage file pair at a time in
explicit center-year blocks, forms one within-template Spearman matrix, and
compares the median matrix in training templates with the held-out median for
four represented whole-ESM and three whole-scenario exclusions. Locked
tolerances are 0.05 for mean absolute difference, 0.15 for maximum absolute
difference, and zero sign reversals when the absolute training median is at
least 0.20.

The MRI-ESM2-0 exclusion is the only failure. Its mean absolute difference is
0.043330, but the wet-frequency--Rx1-given-Rx5 pair differs by 0.192318 and
exceeds the maximum gate. The other three ESM and all three scenario exclusions
pass; no strong pair reverses sign. The computation reads 264 checksum-bound
derived Parquet files sequentially; maximum observed peak RSS across two
deterministic runs is 187,662,336 bytes, well below the registered 2 GiB
ceiling. The failed gate is not retuned. The
diagnostic is not an ECC-Q fit, does not validate missing UKESM or MRI SSP5-8.5
support, and does not authorize FAIR, response, damage, welfare, or SCC use.

We preregistered the MRI failure decomposition before reading its outputs. The
focal pair, original 0.15 maximum-difference gate, two common scenarios, eight
center years, six crops, and two calendar regimes were fixed. The primary test
recomputed held-out versus comparison medians after restricting both sides to
SSP1-2.6 and SSP3-7.0. Its absolute difference is 0.173654 versus 0.192318 in
the original unbalanced comparison, so the locked failure persists. The
scenario-specific differences are 0.163224 and 0.204990, and each of the eight
center-year differences exceeds 0.15. A second descriptive layer calculates
the focal correlation separately within all 1,056 complete
crop/regime/ESM/scenario/center-year fields. Ten of twelve scenario-matched
crop/regime differences exceed 0.15; irrigated- and rainfed-calendar winter
wheat are 0.070128 and 0.084917, while second-season rice is largest at
0.239124 for both calendars. No p-values, tolerance updates, model fitting, or
promotion decisions are permitted by the contract. All 264 inputs are derived
Parquet files read as sequential season/stage pairs; observed peak RSS remained
below 174 MiB across verification runs.
We then preregistered a receipt-only sample-sufficiency decision before
generating its output. It evaluates exactly two pool types: all ESMs pooled and
one ESM at a time. A pool must have at least 51 distinct templates, full
required scenario coverage, and resolved stability evidence; the pooled pool
also requires the complete five-ESM matrix. The current pooled count is 88 but
the matrix and MRI gates fail. A complete conditional pool has only 24
templates under the frozen three-scenario by eight-center-year design, so each
has a 27-template shortfall even after matrix completion. The audit reads three
JSON receipts, no derived Parquet or daily climate file, and performs no fit.
Overlapping 21-year windows are not counted as independent new support without
a separately registered design.
An initial receipt-only temporal count is withdrawn in a checksum-bound
sidecar because it assigned 21-year intervals to legacy annual one-crop/regime
holdout rows. Those rows are not registered as centered linked
multicrop/regime dependence templates, so their exact year labels cannot be
counted toward this gate. A corrected compatibility-first contract was then
preregistered before evaluation. It verifies the 11 current RIME-X cell
receipts and requires all six crops, both calendar regimes, the centered
21-year product identity, and eight center years. A greedy closed-interval
schedule retains at most one of the eight overlapping windows in each
ESM--member--scenario cell. The current 88 nominal templates therefore have an
upper bound of 11 pairwise-nonoverlapping templates; a complete 120-template,
15-cell matrix has an upper bound of only 15. Complete-design whole-ESM and
whole-scenario holdout bounds are 12 and 10. The four legacy receipts contain
2,376,990 rows but contribute zero compatible templates. The corrected audit
reads 17 JSON receipts, no Parquet or daily data, and performs no fit.
Pairwise nonoverlap remains only an upper bound, not evidence of independence;
every FAIR, response, damage, welfare, and SCC gate remains closed.
A subsequent preregistration fixes a purely arithmetic expansion-feasibility
test. It requires the same centered 21-year linked multicrop/regime unit, four
pairwise-nonoverlapping windows within every ESM-member--scenario track, three
SSPs, at least seven member tracks from at least four ESM families, and no more
than two members from one family. The resulting 84-template balanced design
retains 72 training templates after a whole-member holdout, 60 after the
worst-case whole-family holdout, and 56 after a whole-scenario holdout, all
strictly above 51. The corresponding six-member design retains 48 after the
limiting family and scenario exclusions and therefore fails. The evaluator
reads two checksum-bound JSON receipts, no Parquet or daily climate file, and
performs no fit. It does not select members, query new catalogue availability,
estimate bytes, approve storage or acquisition, establish member independence,
or resolve the adverse MRI stability result.
A following contract preregisters an official-catalogue-only candidate screen.
Six queries cover the Cartesian product of SSP1-2.6, SSP3-7.0, and SSP5-8.5
with daily `pr` and `tas`; neither climate forcing nor ensemble member is a
query filter. A track is eligible only when one ESM-member identity is present
in all six cells, every dataset is public, unrestricted, CC0, and version
`20210512`, every required source file exposes a positive byte count and
SHA-512, and continuous daily metadata cover 2015--2035, 2036--2056,
2057--2077, and 2078--2098. The live catalogue contains five eligible tracks
from five families, 30 datasets, and 270 unique source files totaling
536,861,000,440 bytes. Because the contract requires at least seven tracks,
the catalogue gate fails. The audit reads API metadata only, selects no final
ensemble, downloads zero climate bytes, and leaves storage, independence, MRI
stability, fitting, FAIR, response, damage, welfare, and SCC gates closed.
The national joint-crop temporal-support audit reads only county, crop, year,
eligibility, and the already fixed 2017 10% selector flag from the checksum-
bound national panel. After exact corn/soy county-year intersection, it reports
per-county year counts and longest consecutive runs without reading yield
magnitudes. Of 264 common counties, 105 have all 39 years from 1981--2019;
median count and longest run are 38, and the minimum count is eight. This is a
support diagnostic, not a requirement to analyze only balanced counties.
The subsequent metadata-only acquisition contract pins all 90 official
version-`20210512` files required for five ESMs, three SSPs, `pr`/`tas`, and
2031--2060. They total 187,138,935,135 catalogue bytes and are public,
unrestricted CC0 inputs. If all content and feature gates pass, the design
contains 120 centered templates; whole-ESM and whole-scenario exclusions retain
96 and 80 nominal training templates, respectively. The corrected audit does
not treat the overlapping centers as distinct support. These counts do not
imply that files were acquired or that holdout
performance passed.

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
The next fixed expansion adds April and September before acquiring their
official county series. Across the resulting 180 cells, minimum defined daily
correlation is 0.999425 and polygon-minus-official monthly rainfall differences
range from -2.706813 to +1.286771 mm. No outcome is read, the polygon route is
not replaced, and no relationship or SCC gate is opened.

### S9.11 Published fallback-chain readiness

The fallback source screen was preregistered before the primary-source
metadata snapshot. It fixes four named components: MESMER-M-TP as the monthly
temperature--precipitation backbone, Kemsley et al.'s first-order Markov--gamma
method as the daily precipitation generator, MESMER-X Rx1day as the heavy-rain
benchmark, and STITCHES as the sequence-preserving multivariable benchmark.
Substitution after registration is prohibited. Each executable component must
have peer-reviewed method support, a public or archived implementation, a
license identity, and a pinned code identity before any fit.

The audit records public pinned implementations for MESMER-M-TP and both
benchmarks, but no repository or software archive for the fixed Kemsley daily
method. It separately requires exact monthly precipitation conservation,
joint daily temperature--precipitation innovations, spatially coherent daily
rainfall, wet-day frequency, consecutive dry days, Rx1day, Rx5day, crop-stage
timing, whole-ESM and whole-scenario holdouts, direct-daily comparison, and
common-random-number FAIR pulse convergence. Fourteen of fifteen end-to-end
requirements remain unestablished, so the audit exits with
`fallback_not_executable_no_fit`. It reads only metadata and authorizes no
software or climate-payload acquisition, fitting, FAIR evaluation, response,
damage, welfare, or SCC calculation.

A subsequent literature audit added Bassetti et al.'s published DiffESM
(2024, doi:10.1029/2023MS004194; MIT-licensed study code at
doi:10.5281/zenodo.11403197) to the *separate benchmark inventory* without
retroactively substituting the preregistered Kemsley component. It generates
28-day global daily precipitation or temperature fields conditional on monthly
fields and evaluates within-block rainfall frequency, rainy streaks and
intensity using two CMIP5-era ESMs. The peer-reviewed version handles the
variables separately; the authors explicitly leave continuity between
generated 28-day blocks for future work. Its reported diagnostics therefore
do not establish planting-to-harvest dry-spell continuity, calendar-month
amount conservation after the stated <1 mm/day zeroing, joint daily
heat--rain covariance, ISIMIP3b/CMIP6 transfer, or matched marginal pulse
convergence. No training, inference, source acquisition or adaptation is
authorized by this literature addition under the current memory cap.

### S9.12 Conservative common-innovation daily-pair interface

Before any daily-generator implementation, we preregistered an
algorithm-independent interface for matched FAIR baseline and pulse paths.
The pair identity fixes climate draw, ESM, member, grid, calendar, month, and
pulse size; path role distinguishes the two monthly and daily records. A
counter-based or equivalently keyed random-access stream supplies separate
wet-state, wet-amount, and spatial-dependence innovations. Its key includes
the seed namespace, generator and parameter-bundle identities, climate draw,
ESM/member/grid/calendar/day, innovation family, and slot. It excludes path
role, pulse size, monthly climate values, and path-specific parameters. Thus
baseline and every pulse size can have different thresholds and distributions
without consuming a different subsequent random stream. Matching monthly
innovation digests are required across path roles and pulse sizes.

For each path separately, provisional daily precipitation must be finite and
nonnegative. A zero monthly target requires all daily values to be zero. For a
positive target, the provisional monthly sum must be positive; every positive
provisional amount is multiplied by the target-to-provisional-sum ratio, which
preserves the wet/dry sequence. Any floating-point residual is assigned to the
last positive wet day in calendar order and the corrected amount must remain
nonnegative. The final monthly error cannot exceed the larger of `1e-9` mm or
`1e-12` times the monthly target. Each path must pass this gate independently.

The interface also requires exact zero-pulse and pre-divergence daily identity,
separate support flags, at least three decreasing positive pulse sizes,
direct-daily and crop-stage feature comparisons, whole-ESM and whole-scenario
holdouts, and convergence of pulse-normalized feature differences. A future
receipt must bind code, paper, parameters, monthly inputs, RNG identity and
namespace, innovation digests, output hash, maximum mass error, and peak
resident memory. The current status is
`interface_preregistered_no_generator_implementation`: schema validation is
not scientific validation or permission to implement, and the absent pinned
Kemsley source remains a hard no-fit blocker.

### S9.13 Future daily-pair output schema gate

Before any generator output exists, we separately preregistered its exact JSON
boundary. A bundle contains only a schema tag, receipt, and nonempty monthly
records. The receipt binds the parent interface, generator/paper/parameter and
monthly-input identities, RNG identity and namespace, canonical daily-output
hash, observed maximum monthly mass error, and peak resident memory. The
monthly-input digest is the SHA-256 of UTF-8 JSON with sorted object keys,
compact separators, and nonfinite values forbidden after projecting every
record to climate draw, ESM, member, grid, calendar, year, month, pulse scale,
path role, divergence key, monthly precipitation and temperature targets,
parameter-bundle identity, and support flag, then sorting by the exact monthly
record key. Record order, monthly innovation digests, and daily values are
excluded. Blank, missing, or additional receipt fields fail; memory above 2
GiB fails.

Each monthly record is keyed by climate draw, ESM, member, grid, calendar,
year, month, pulse scale, and path role. Each pair must contain exactly one
baseline and one pulse record. Each climate-month group must contain exactly
one zero scale and at least three distinct positive scales. Daily rows must
contain only the date/model-day and nonnegative precipitation, cover the exact
calendar month in increasing order, and sum to the path-specific monthly target
within `max(1e-9 mm, 1e-12 * target)`. The validator also requires matching
baseline/pulse and cross-scale innovation digests, an invariant baseline daily
path across scales, exact zero-pulse identity, and exact equality on every day
before the registered divergence date.

The in-memory synthetic fixture uses leap Gregorian, noleap, 360-day, and
all-zero calendar months, four pulse scales per month, and 32 monthly records.
It passes with zero maximum mass error. Invariance checks confirm that record
order, innovation digests, and daily values do not change the monthly-input
digest; monthly-target and support-flag changes fail. Fourteen single-purpose
corruptions verify fail-closed behavior for receipt, key, digest, conservation,
identity, day coverage, field, resource, and both hashes. Synthetic test values
are not persisted as climate output. This gate does not implement or substitute
the unavailable generator, validate its science, or authorize software/climate
acquisition, fitting, FAIR evaluation, response estimation, damages, welfare,
or SCC use.

### S9.14 Canonical daily-generator parameter boundary

Before allowing `parameter_bundle_sha256` to identify future parameters, we
separately preregistered its exact object and canonicalization. The object binds
the generator, paper, code, and parameterization identities plus one record for
every monthly output key. Each record contains dry-to-wet and wet-to-wet
transition probabilities on the closed unit interval; strictly positive gamma
shape and millimetre-scale parameters for wet amounts; SHA-256 identities for
the spatial-dependence and joint temperature--precipitation components; and the
support flag. Records are sorted by climate draw, ESM, member, grid, calendar,
year, month, pulse scale, and path role before compact UTF-8 JSON hashing with
sorted object keys and nonfinite values forbidden.

The validator requires unique parameter keys that exactly equal the monthly
output keys, identical support flags, matching generator code identity, and the
canonical parameter hash in both the output receipt and every monthly record.
It rejects missing or extra records, out-of-domain probabilities, nonpositive
gamma values, invalid component hashes, identity mismatches, and parameter
changes hidden behind a stale digest. Record order leaves the hash unchanged.
A two-record synthetic unit fixture rejects ten targeted corruptions, and the
existing 32-record four-calendar output fixture links to 32 parameter records.
These are schema and identity checks only: no parameter is fitted or presented
as empirical, and the missing pinned generator still blocks implementation,
FAIR evaluation, response estimation, damages, welfare, and SCC use.

## S9.15 Source-matched U.S. response diagnostic registered September 8

`US_SOURCE_MATCHED_RESPONSE_PROTOCOL_20260908.md` freezes a new exploratory
comparison before regional climate completion and response fitting. The two
factual weather products are fitted separately on identical 1982–2010 NASS
county/crop/practice/year observations. Quantity is primary; stage shares are
an incremental candidate with matched samples and nonlinear heat controls.
The protocol fixes model complexity, thresholds, sample and numerical gates,
zero-rain handling, source-binding steps and failure reporting. No counterclim
weather enters training; no coefficient transport or damage calculation is
authorized. In-sample fit is not out-of-sample validation, and previously
inspected historical years are not described as untouched. Formal source-
difference uncertainty requires a paired procedure, not independence of the
two fitted estimates. At registration, the input chain is still running and
no fit under this new contract has been executed.

## S9.16 Published polynomial implementation check

The source-pinned benchmark protocol is
`GGCMI_REFERENCE_INTERFACE_PROTOCOL_20260908.md`. An isolated evaluator
represents Eq. 1 of Franke et al. with 34 rainfed terms and the 19 terms
remaining when water is omitted. Input normalization and term ordering were
checked against osiris commit `1c4d5015d4ffd658fc6cedee023e175d2fe93f08`.
All 660 deterministic synthetic reference comparisons passed at a scaled
absolute tolerance of 1e-12; the maximum difference was 2.22e-16. Six unit
tests additionally cover derivative checks, multiplier baseline, invalid
coefficients, restricted-domain rejection and unsupported layouts. Only
strictly parsed reference arithmetic was evaluated in base R; the full
downloaded pipeline and its whole-array loading were not run.

This does not validate global agricultural damages. In particular, the
resident CARAIB file has raw 20/10 rainfed/irrigated coefficient dimensions,
not 34/19. Its no-nitrogen ordering is not yet source-bound by the inspected
implementation, so that layout is rejected and no real coefficient has
been evaluated. The numerical fixtures are synthetic software tests, never
observations or process-model impacts. The published assumption that full
irrigation removes direct rainfall dependence is structural, not an
empirically estimated treatment effect. CO2, baseline/calendar alignment,
adaptation and economic conversion remain separate evidence requirements.
[Franke et al.](https://gmd.copernicus.org/articles/13/3995/2020/),
[osiris reference](https://github.com/JGCRI/osiris/blob/1c4d5015d4ffd658fc6cedee023e175d2fe93f08/R/grid_to_basin_yield.R).

### S9.16.1 Subsequent author-bound no-nitrogen point check

The preceding no-nitrogen interface blocker was subsequently resolved using
the author's recovered archive (Zenodo 4321276), whose `emulator` function
explicitly orders 20 rainfed/10 irrigated coefficients. No ordering was chosen
by observing plausible yields. The separate protocol
`GGCMI_CARAIB_POINT_PROTOCOL_20260908.md` was registered before coefficient
reading. Its 384 synthetic reference comparisons pass (maximum scaled error
2.22e-16); explicit nitrogen-response selection is required, with nine unit
tests covering incorrect mappings as well as the original checks.

Only then were the resident CARAIB maize A0 coefficients read at the fixed
coordinate 39.25 N, -100.25 E. Six W={0.9,1,1.1} rainfed/irrigated evaluations
at C=360 ppm and T=0 reproduce the author arithmetic (error 1.88e-16).
Six water-derivative checks pass. The -10% uniform-precipitation perturbation
gives a -1.1664% rainfed change at this point. This is a published process-model
engineering test, not an observed effect or climate scenario. No negative
yield clipping or global extrapolation was applied. The fully irrigated
polynomial omits W by construction. See the separate results document for
complete values, provenance and interpretation limits.

Climate alignment is a separate unfinished step. The author's Phase 2
calendar concept DOI maps explicitly to version 3773827. Its two maize files
were acquired and compared, with verified hashes and coordinate orientation,
to our resident Phase 3 calendars. At this point planting dates are 122.5
versus 122, while harvest/maturity is 260. The author climate preprocessing
uses monthly growing-season weights and a 1980–2010 baseline with moving
31-year means. Our previous stage features, calendar, and shorter selected
historical window cannot be silently substituted. No actual projected weather
was passed through the new polynomial in this step.
[Author code](https://zenodo.org/records/4321276),
[Phase 2 calendar](https://zenodo.org/records/3773827).

### S9.16.2 Actual climate point coupling, with explicit period limitation

`GGCMI_CLIMATE_POINT_ALIGNMENT_PROTOCOL_20260908.md` was registered before
reading point weather. Existing GFDL-ESM4 r1i1p1f1 historical/SSP126 daily
inputs at 39.25 N, -100.25 E were stream-hashed, then sampled one point/month
at a time. The 1981–2010 and 2031–2060 windows each have thirty complete
years; they do not replicate the published 31-year baseline/moving windows.
Historical subset checksums do not independently verify global parent files.

The author's monthly weighting at planting DOY 122.5/harvest DOY 260 gives
May–September day counts (29.5,30,31,31,17), normalized by 138.5 inclusive
days rather than the calendar's 137.5-day endpoint difference. Monthly means
use all actual Gregorian days, including leap years. Equal-weight years
define period means; W is future/historical growing-season mean rain rate,
T the temperature difference. A Phase 3 calendar is a named sensitivity.
Annual precipitation totals are retained separately from seasonal rates.

W=1.1123837 and T=+1.6742049°C. Only W enters the initial crop contribution,
holding C=360, T=0 and unused N=200. The source-defined application interval
W∈[0.5,1.3] was registered before seeing values; no clipping was applied.
The rainfed quantity-only contribution is +1.14358% at this point, not net
climate change or an empirical/global estimate. Four author-R comparisons
pass at 3.72e-16 scaled error; eight independently read monthly means agree
exactly and all period aggregates within 3.55e-15. Full reproduction and
provenance are in `GGCMI_CLIMATE_POINT_ALIGNMENT_RESULTS_20260908.md`.
Timing effects, warming, CO2, adaptation, welfare and SCC remain excluded.

### S9.16.3 Registered two-model/two-scenario quantity matrix

The same coordinate was extended to GFDL/IPSL × SSP126/SSP585 before new
point data were acquired. Twenty single-cell files (eighteen missing future
inputs plus two GFDL accuracy sentinels) were obtained in a 5,372,091-byte
archive. Catalogue identities were checked against the frozen source-metadata
plan; no new full-global climate payload was downloaded. The sentinels agree
exactly on all 7,306 daily values against their resident parent files.
IPSL's documented noon timestamp convention is handled explicitly, while
GFDL retains midnight; both require exact dates and 24-hour spacing.

The completed GFDL SSP126 case and historical cache were reused, not refitted.
At this point the Phase 2 quantity-only contributions are +1.1436%, -0.9911%,
+0.5580% and +0.7748% in GFDL126/GFDL585/IPSL126/IPSL585 order. No scenario
probabilities or ensemble interval are assigned. Phase 3 calendar sensitivity
does not reverse signs here. W remains inside the registered application
domain; no clipping occurs. Warming and CO2 are held fixed in crop evaluation.
Sixteen author-R comparisons pass within 3.74e-16 scaled error. Independent
raw checks cover all 3,600 new/shared historical monthly inputs exactly;
48 period aggregates agree within 7.11e-15. These tests establish numerical
consistency, not empirical validation or global damage transport.

The continuation script automatically advances available acquisition,
sentinel, aggregation and validation stages while preserving failures and
avoiding duplicate submissions. The controller run used 166.47MiB sampled
process-group RSS. Full protocol and sources:
`GGCMI_POINT_CLIMATE_MATRIX_{PROTOCOL,RESULTS}_20260908.md`.

### S9.17 September 16 U.S. crop-year and irrigation-robustness extensions

The national county-average weather route uses NOAA nClimGrid-Daily published
county averages, acquired as 90 six-month source batches spanning 1981--2025.
Each source object's identity, checksum, schema, date coverage, and county
keys is recorded before one county/crop/year stage-feature partition is
constructed. The 45 annual partitions contain 254,205 crop-year rows and
passed 608 independent source-to-feature checks. Raw files and resulting
large panels are ignored by Git; the data manifests and bounded scripts are
in this repository. This route differs from the earlier cell-first TIGER
polygon aggregation. An exact-key, outcome-free comparison on all 11,861
older regional crop/county/year weather keys checks calendar alignment and
feature discrepancies without assuming either estimator is truth. See
`US_COUNTY_WEATHER_ESTIMATOR_COMPARISON_{PROTOCOL,RESULTS}_20260916.md` and
`scripts/{compare,validate}_us_county_weather_estimators.py`.

The primary prediction cohort is defined by the 2017 Census county/crop
irrigated-acreage share <=10%, without looking at the terminal yield
outcomes. All-practice NASS county yield is modeled in log units with county
fixed effects and a common linear year term. Models are fit through 2019 and
scored on 2020--2025. Each moisture specification shares the same
temperature controls and terminal rows: seasonal rainfall total; total plus
registered wet-day, dry-spell, heavy-rain and stage-share basis; or seasonal
NOAA nClimDiv PDSI in place of raw-rainfall terms. PDSI is not stacked with
rainfall and temperature as an extra effect. A state-specific linear-trend
sensitivity and historical blocked splits test stability. The daily-weather
feature build, PDSI join and fit each have source-bound and independent
reconstruction checks, but predictive skill does not identify a structural
precipitation effect.

The post-result irrigation-screen sensitivity repeats the unchanged fit and
score pipeline under fixed-2017 <=20% and <=30% screens, and separately
under 2022-vintage <=10/20/30% composition screens. The latter use
information from within the terminal interval and cannot be counted as
prospective validation. All outcomes remain all-practice yields, so the
screen is only a proxy for rainfed-dominated counties; no comparison across
screen RMSEs is interpreted as an irrigation effect. The original 2017
<=10% sample and scores are reproduced exactly. A separately coded
source-panel and within-estimator check verifies 498 sample, coefficient
and score identities; fit, rank and finite-value checks are retained.
Reproduction: `US_COUNTY_AVERAGE_IRRIGATION_SCREEN_SENSITIVITY_20260916.md`,
`US_COUNTY_AVERAGE_IRRIGATION_SCREEN_RESULTS_20260916.md`,
`scripts/evaluate_us_county_average_irrigation_screens.py`, and
`scripts/validate_us_county_average_irrigation_screens.py`.

A separate post-result state-composition diagnostic refits only the two
unchanged historical models to reconstruct the original terminal forecasts,
requiring `1e-12` aggregate-score parity first. All 2020--2025 state rows
then receive paired quantity and pattern squared-error sums, pooled and
equal-state RMSEs, and fixed-forecast leave-one-state-out pooled differences.
No state is removed from training, so this is not spatial transfer. States
with fewer than 30 rows or three years are flagged, never suppressed.
Independent grouped normal equations and scalar state aggregation passed
498 numerical checks. The estimator's NumPy matrix-operation warnings are
retained in the ignored log; finite values, parent-score parity and
independent reconstruction pass. The registered contract, aggregate report
and scripts are
`US_COUNTY_AVERAGE_STATE_COMPOSITION_{DIAGNOSTIC,RESULTS}_20260916.md`
and `scripts/{evaluate,validate}_us_county_average_state_composition.py`.

For a direct-practice sensitivity, the 1981--2018 paired reported irrigated
and nonirrigated regional sample is held to the identical 11,857 keys and
original county plus state-year fixed-effects design. Only the weather
estimator changes from cell-first gridded aggregation to NOAA county
averages. The registered +100-mm irrigated/nonirrigated yield-ratio
contrasts and an independent Arrow/QR/cluster-sandwich reconstruction are
reported in `US_PAIRED_PRACTICE_WEATHER_ROUTE_{PROTOCOL,RESULTS}_20260916.md`.
This is a historical conditional association, not an irrigation treatment
effect, climate-change counterfactual or GIVE input.

## S10. Scientific integrity and independent review

### Original-simulation member recovery (September16)

Sixty strict64KiB-or-smaller ranges reassemble the3,916,602-byte original
EPIC-TAMU C360/T0/W0/N200/A0 maize NetCDF member. Every request is bound to
exact206, Content-Range, Content-Length, local hash and contiguous source
offset. An independent pass checks all chunk evidence before assembly.
HDF5 header inspection—not yield-array inspection—finds31 growing-season
records, a360×720 grid and compressed `[31,360,720]` yield data in
`t ha-1 yr-1` with fill1e20. The full tar's advertised MD5 and the emulator
fitting-window convention remain unverified. The failed large-range request
and wrong-interpreter assembly attempt are retained. Member checksum,
resource receipts and limitations:
`EPIC_RAW_BASELINE_MEMBER_RESULTS_20260916.md`.

### Matched raw-output and Morocco support audit (September16 continuation)

The exact C360/T+3/W−50%/N200/A0 companion member was recovered in44
verified64KiB-or-smaller ranges (2,832,811 bytes). Independent assembly and
header inspection show the same31×360×720 axes and yield schema as baseline.
The coordinate-only audit reads no yield array and records time indices1–31,
descending latitude89.75 to−89.75 and ascending longitude−179.75 to179.75.
The actual latitude direction differs from the protocol's general ascending
description. Following the [GGCMI Phase2 protocol](https://gmd.copernicus.org/articles/13/2315/2020/),
time is a sequence of growing periods, not a universal calendar-harvest-year
label; the file's31 records versus published30-year output description remain
unresolved. A protocol was hash-pinned before yield inspection, fixing all75
Morocco cells, the last30 positional records as primary, and first30/all31 as
visible sensitivities.

The bounded extraction reads only75 two-state cell series, not global cubes.
An independent reread verifies all4,650 values and6,450 checks. Eight cells,
carrying19.316% of the fixed baseline production weight, are source-fill
missing for all31 records in both states; all eight had negative polynomial
future yields in the earlier projected-input trace and also at the exact
T+3/W−50% corner. The source model does not supply yield outcomes there at
these states. On67 paired-valid cells, last30 raw/polynomial relative changes
contribute−52.157/−47.511 percentage points on the unchanged75-cell weight.
Independent coefficient-basis evaluation and aggregate audit pass. This is
a source-model fidelity and spatial-support diagnostic under an imposed
uniform perturbation, not observed causality, within-season rainfall-pattern
response, full-Morocco crop loss, welfare, or SCC. Source hashes, fixed design,
three-window results and resource receipts are in
`EPIC_RAW_MOROCCO_COMPARISON_PROTOCOL_20260916.md` and
`EPIC_RAW_MOROCCO_COMPARISON_RESULTS_20260916.md`.

### Original-yield access constraint (September16)

The first entire NetCDF member-range request returned a gateway504; no file
was accepted. A separate, hard-capped4KiB request from the exact baseline
member offset returned exact206/Content-Range and an HDF5 signature. This
supports exploring a bounded chunked transfer, not claiming a verified member
or original simulation outcome. Failed and successful receipts are retained;
details in `EPIC_RAW_MEMBER_TRANSFER_STATUS_20260916.md`. No yield arrays,
empirical response, damage or SCC were calculated.

### Header-only source index (September15)

A bounded first batch indexes128 raw-simulation tar headers using127 new
512-byte range bodies, skipping member bodies by verified aligned offsets.
It locates a C360/N200/A0 baseline and registered T+3/W−50% member. Each
request requires exact206/Content-Range; each header requires checksum and
archive-boundary checks. Six parser/output-scope synthetic groups pass. An
initial relative-output-path bug and its failed attempt are preserved; the
corrected batch resumes only validated prefix evidence. No file body, yield
comparison, fitted-window assumption or complete archive checksum claim is
made. Result, source identities, limits and reproducibility:
`GGCMI_TAR_HEADER_INDEX_RESULTS_20260915.md`.

### Original-simulation access feasibility (September15)

The official protocol XML's Table4 and exact archive metadata bind EPIC-TAMU
maize raw simulations to [Zenodo2582349](https://doi.org/10.5281/zenodo.2582349),
distinct from coefficient assets. A strictly512-byte range probe of its
2,708,899,840-byte A0 yield tar returns exact206/Content-Range and a valid tar
header checksum. This establishes only header-access feasibility, not
verification of the full archive checksum or an inspected yield array.
No training-state output or averaging-window definition has been inferred.
Bounded header indexing and separately qualified member extraction are the
next source steps. Sources, caps, retained TLS/web errors, registry and
receipts: `GGCMI_RAW_OUTPUT_ACCESS_RESULTS_20260915.md`.

### Remediation/source distinction (September15)

Negative polynomial outputs are not assumed to be negative raw crop-model
simulations. The inspected coefficient archive does not provide the training
yield tensor; raw simulation records are advertised separately in the
[GGCMI protocol's Table4](https://gmd.copernicus.org/articles/13/2315/2020/).
Exact EPIC-TAMU release identities, licensing and subset feasibility remain
unverified. Clipping defines a different response model, whereas a constrained
refit requires source training and held-out simulations. Neither has been
performed. `CROP_BENCHMARK_REMEDIATION_MEMO_20260915.md` records the distinction,
alternatives and bounded metadata-first next step. No data gap was filled by
guessing and no monetary gate was opened.

### Negative-yield trace qualification (September15)

The two flagged Morocco entries were traced to75 common-support cells per
calendar label. Six hundred direct evaluations of the source coefficients
exactly reproduce saved corners;608 independent accounting checks pass.
Eight cells predict negative future joint yield while all inputs are within
the registered T/W rectangular application bounds. No arithmetic/join
discrepancy was found. Rectangular-domain membership and replication accuracy
therefore do not establish positivity or empirical validity. The resulting
nonpositive country multiplier is blocked from valuation; no clipping,
outcome-based sample selection or refit was performed. Both calendar labels
have identical inputs here and are not independent realizations. Reproduction,
source hashes and small bounded receipts:
`MOROCCO_NEGATIVE_CORNER_TRACE_RESULTS_20260915.md`.

### Welfare input-readiness audit (September15)

A hash-pinned resident-schema audit reconciles32 maize benchmark cases and
3,360 country-case-regime rows to baseline value/production support. Three
synthetic tests and364 independent source-row checks pass. Annual-year and
paired emissions-pulse axes and calibrated trend/upper adaptation costs are
not present in the saved country summaries. Order-averaged precipitation
yield contributions are not standalone productivity multipliers for nonlinear
welfare; appropriate climate-corner valuation must precede decomposition.
Two saved Morocco EPIC/IPSL/SSP585 rainfed calendar entries imply nonpositive
joint production and are retained as unusable benchmark outcomes, not real
crop-loss estimates. No clipping, country removal or monetary conversion.
Source bindings, scripts, failures/qualification limits and small bounded
receipts are in `WELFARE_INPUT_READINESS_RESULTS_20260915.md`.

### Proposed independent welfare benchmark (not adopted)

`FULLY_ANTICIPATED_WELFARE_SPECIFICATION_20260915.md` specifies a closed,
fully anticipated constant-elasticity sensitivity benchmark, not a replication
of the partially anticipated storage/welfare procedure. Normalized supply is
exp(s)p^e, demand p^(-d), and inverse supply is interpreted as marginal cost.
For baseline s0 and increment h, define V=V0 exp(-(1-d)s0/(e+d)),
L=-h/(e+d), z=(1-d)L, and exprel(z)=expm1(z)/z with limit1. Finite paired
changes are DeltaCS=-VL exprel(z), DeltaPS=V expm1(z)/(1+e), and
DeltaTS=Vh exprel(z)/(1+e); positive damage is -DeltaTS. These are mathematical
consequences of declared assumptions, not estimated crop damages.

Two yield-to-supply mappings, s=logA and s=(1+e)logA, remain explicit
alternatives. Irrigation regimes aggregate supply within a commodity market
before welfare calculation; averaging log shifts or valuing separate regime
demand markets is not equivalent. No expectation, storage-price reduction or
additional flexibility factor is silently imported. User adoption, response
qualification, adaptation costs, coverage, units and matched pulse gates remain
required before empirical money. The specification includes those interfaces
and distinguishes precipitation decomposition from total-sector replacement.

### Price-basis convention validation (September15 amendment)

The maize value proxy remains in source constant2014--2016USD; no empirical
welfare calculation has been performed. A separate source-pinned registry
specifies a GDP-wide conversion to GIVE's USD2005 convention as
87.504/mean(103.654,104.691,105.740)=0.8357992263240843, with87.504/104.691 as
midpoint sensitivity. The values come from the U.S. column of
[Hawaii Data Book2021 Table14.01](https://files.hawaii.gov/dbedt/economic/databook/2021-individual/14/140121.pdf),
whose note identifies BEA's31March2022 release. It is not labeled an exact
archived2021 BEA extract. The PDF hash, bytes, dates, series/base and formulas
are pinned in `config/price_basis_registry.toml`; the PDF is ignored and its
redistribution license has not been asserted. This is an explicit GDP/farm-
gate price-concept approximation, not an empirical calibration.

Six price-contract groups and three affected scenario-registry groups pass,
including corrupted-source, index/unit/formula mismatch and unauthorized-gate
promotion rejections. Only the deflator convention gate is resolved;
expectations, realized surplus and adaptation accounting remain unresolved.
All empirical welfare and damage exports remain disabled. Report, acquisition
restoration instructions and bounded receipts:
`PRICE_BASIS_REGISTRY_RESULTS_20260915.md`.

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

### S10.2 Source-only global daily feature engineering check

Under the preregistered `GLOBAL_DIRECT_DAILY_GFDL_FULL_2032_MAIZE_PROTOCOL_20260917.md`,
the SHA-512-matched ISIMIP3b GFDL-ESM4 `r1i1p1f1` SSP1-2.6 `pr` and `tas`
2031--2040 source pair was streamed through 36 sequential, ten-latitude-row
tiles with the registered GGCMI Phase 3 `mai_noirr` calendar. Only harvest
year 2032 was retained. The builders emitted 67,420 unique valid calendar
cell-year records and 202,260 stage records, exactly three per season.
Per-tile tests checked unique keys, coordinate/calendar identity, valid-cell
count, and season/stage days, rainfall, wet days and Rx1day reconciliation.
Independent validation rehashed all partitions, reproduced the previously
validated `[100,110)` tile exactly, and recomputed 21 fixed raw daily cells
across seven latitude rows. The highest sampled builder RSS was 242,319,360
bytes, within the 512 MiB guard. Files and machine-readable receipts are
ignored under `data/interim/gfdl_ssp126_global_2032_maize_full_20260917/`.
The two earlier pilot-validator failures caused by undeclared `float64`
conversion/reduction are preserved in their original receipts, with the
corrected source-dtype and high-precision-roundoff checks documented in the
pilot protocol. The output contains no outcome, warming response, crop loss,
or welfare estimate; it is not used in any SCC calculation. Full counts,
limitations and receipt paths are in
`GLOBAL_DIRECT_DAILY_GFDL_FULL_2032_MAIZE_RESULTS_20260917.md`.

Under separately registered extension protocols, the same SHA-512-verified
source pair, crop calendar and fixed feature builders then processed harvest
years 2033--2039 in sequential 36-tile passes. Each year's independent
validator recomputed the 21 prespecified raw source cells; only 2032 was
eligible for exact earlier-pilot parity. A separate preregistered cross-year
audit verified all manifest/file hashes, year identities, the *exact* crop
calendar `(lat,lon)` mask (not only cell counts), source/calendar coordinate
arrays, physical feature bounds and year-receipt links. Across 2032--2039
the input-only panel has 539,360 cell-years and 1,618,080 stage rows. Maximum
sampled builder RSS was 255,983,616 bytes under the 512 MiB limit, while
free disk remained 137 GiB. In the seven later years, 471,839 of 471,940
rainfall entries and all 471,940 temperature entries differ from the same
cell's 2032 entry: an output-reuse check, not a trend or attribution result.
The complete source-only report and ignored receipt paths are in
`GLOBAL_DIRECT_DAILY_GFDL_2032_2039_MAIZE_PANEL_RESULTS_20260917.md`.
No model/scenario ensemble, yield, climate response or SCC follows from this
eight-year engineering pass.

Under the later-window preregistration, the same crop-feature code processed
one additional harvest year from each of the 2041--2050 and 2091--2100
GFDL-ESM4 SSP1-2.6 daily `pr`/`tas` source pairs (2042 and 2092). Each
source pair was renewed against the receipt's SHA-512, size, decoded audit
identity, units, full coordinate and paired-time axes. The two later-window
receipt files lack an SHA-256 for the audit JSON itself, so the JSON's
decoded fields were compared with the source receipt and this weaker
audit-file binding is disclosed; source-file SHA-512 binding is unchanged.
Each year passed 36 tile checks, 21 prespecified independent raw-cell
checks, and a separate exact-calendar-mask/physical-bounds audit. The two
anchors add 134,840 season and 404,520 stage input records. The ignored
receipts and hard limits are listed in
`GLOBAL_DIRECT_DAILY_GFDL_THREE_WINDOW_ANCHOR_RESULTS_20260917.md`.
Neither anchor provides a reliable climate response estimate in isolation.

The registered UKESM1-0-LL `r1i1p1f2` 2091--2100 daily-source continuation
used the same weather-feature definitions and GGCMI `mai_noirr` calendar
for the three available SSPs at harvest year 2092. Each source pair passed
SHA-512 and pinned decoded-audit checks, matching time/coordinates/units,
36-tile exact calendar support, all-row physical bounds and 21 independent
fixed-cell raw-daily reconstructions. The exact `(year,lat,lon,crop,regime)`
panel was joined across scenarios without row loss. The diagnostic reports
unweighted cell-level mean, median, 5th/95th quantiles and positive-cell
fraction for seasonal rain total, wet days, maximum dry spell, Rx1day,
Rx5day, mean temperature and each of three stage rain totals. A separate
keyed-merge implementation reproduced all 92 saved-statistic and
stage/season mean-conservation checks. Complete results, receipt paths,
resource limits and the non-attribution boundary are in
`GLOBAL_DIRECT_DAILY_UKESM_2092_THREE_SCENARIO_RESULTS_20260917.md`.
These contrasts are not a fitted climate emulator or a causal GMT slope.

The separately registered five-ESM × three-SSP 2092 source-engineering
queue then processed the remaining local daily pairs serially without
new raw downloads. Each panel passed current SHA-512 and decoded-audit
checks, 36 memory-bounded tiles, exact calendar keys/physical bounds and
21 independent raw-cell recomputations. A cohort audit rehashed all 30
source files and all tile outputs and reconciled independent receipts,
yielding 1,011,300 seasonal and 3,033,900 stage records at sampled
builder peak 247,218,176 bytes. The existing GFDL SSP1-2.6 panel kept
its original format; it was independently checked, not overwritten.
MPI and MRI provenance files use different placements for decoded units
and chronology, producing two fail-closed queue stops. Both were
handled by source-only metadata normalization against hash-pinned
audits and direct physical/unit/period checks, never by changing
climate features or silently omitting a model. Full gates, limitations
and ignored receipts are in
`GLOBAL_DIRECT_DAILY_FIVE_ESM_2092_COHORT_RESULTS_20260917.md`.
One 2092 weather year per panel does not satisfy multiyear climate-response
identification or held-out model/scenario validation.

The UKESM SSP1-2.6 2092--2099 multiyear extension initially tested an
eight-year `[100,110)` latitude tile. Its season worker was stopped
at 567,279,616 bytes by the preregistered 512 MiB sampled-RSS guard
before output, so no eight-year batch result was promoted. A separate
four-year 2092--2095 tile, under the same source and limits, passed
at 401,440,768 bytes; an independent audit confirmed exact 2092
single-year tile parity, four identical calendar masks and nine new
fixed raw-daily cells. Because one tile's memory performance is not
global evidence, the continuation used one-year ten-row tiles. All
eight UKESM SSP1-2.6 years 2092--2099 passed 36 tile receipts and
21 fixed independent raw-cell recomputations per year. A separate
cross-year audit rehashed all year/feature manifests, checked the
67,420-cell mask in each year, compared eight season/stage 2092--2095
pilot frames exactly, and confirmed distinct daily weather values.
Its receipt reports 539,360 seasonal and 1,618,080 stage records and
189,825,024 bytes peak sampled audit RSS. The lost eight-year attempt
and its receipt remain disclosed in
`GLOBAL_DIRECT_DAILY_UKESM_MULTYEAR_ENGINEERING_STATUS_20260917.md`.

The registered 2042 UKESM SSP1-2.6/3-7.0/5-8.5 anchors use already
local, separately pinned 2041--2050 daily `pr`/`tas` pairs. For each,
source SHA-512, decoded audit SHA-256, unit/grid/time agreement,
36 bounded full-grid tiles, exact calendar keys, feature constraints
and 21 independently reconstructed daily cells pass. An exact-cell
equal-grid-weight comparison, using the same feature set as the
earlier 2092 comparison, reports season and three within-season rain totals, wet-day
count, maximum dry spell, Rx1day, Rx5day and mean temperature. An
independent keyed-join computation reproduced 92 saved-statistic and
stage/season rain-conservation checks. Separately, each of the six
source receipts SHA-256-pins same-realization annual GMST output;
an alignment audit checks the archived per-year values, daily counts,
ESM/member/scenario/source keys and feature-manifest bindings. This
does not independently reconstruct annual GMST from raw global daily
tas; its absolute Kelvin differences are not a GIVE/FAIR anomaly
calibration. The complete receipt and claim boundaries are in
`GLOBAL_DIRECT_DAILY_UKESM_TWO_WINDOW_ANCHOR_RESULTS_20260917.md`.
Neither two single-year anchors nor one ESM's eight-year late-century
panel identifies a forced GMT response or agricultural damages.

The separate UKESM SSP1-2.6 2042--2049 continuation then applies
the same one-year 36-tile, independent 21-raw-cell protocol to each
additional harvest year 2043--2049 from the same pinned 2041--2050
daily pair. A cross-year audit verifies annual source/manifest hashes,
raw-cell/resource receipts, exact invariant 67,420-cell calendar
support, and distinct within-cell rain/temperature values; it passes
at 173,228,032 bytes sampled RSS. Its first execution failed without
result because an audit-local DataFrame variable shadowed the integer
first-year key; a corrected retry under the same cap passed, with
both logs retained. The two independently checked eight-year UKESM
SSP1-2.6 windows contain 1,078,720 seasons and 3,236,160 stage
features. These are discontinuous and remain only one ESM/scenario;
the production climate response, crop yield and SCC gates are closed.
See `GLOBAL_DIRECT_DAILY_UKESM_TWO_EIGHT_YEAR_WINDOWS_RESULTS_20260917.md`.

### Multimodel late-window and within-scenario diagnostics (September 17)

The later globally complete rainfed-maize weather comparison keeps 67,420
calendar cells fixed and compares SSP1-2.6, SSP3-7.0, and SSP5-8.5 over
harvest years 2092--2099 for UKESM1-0-LL, IPSL-CM6A-LR, and
MPI-ESM1-2-HR. Each year is built from the pinned same-model daily
`pr`/`tas` pair in 36 serial latitude tiles, with 21 independent
raw-daily cell reconstructions. Per-scenario eight-year audits rehash
source and feature receipts and check identical calendar keys, units,
physical bounds, stage-to-season rainfall conservation, and distinct
weather years. ESM-specific independent grouped-table arithmetic
checks reproduce UKESM 315, IPSL 90, and MPI 90 stored statistics;
a separate exact-key three-ESM merge audit reproduces 114/114
cross-ESM statistics. The predeclared season-rainfall SSP5-8.5 minus
SSP1-2.6 equal-cell mean changes are +7.231, +23.543, and -1.180 mm,
respectively. Thus the two-ESM positive sign does not survive adding
MPI. Rx5day rises in each, while wet-day frequency and early-stage
rain are mixed. These are short, single-window scenario contrasts,
not an identified response to GMT or an agricultural-damage estimate.
Full results and source/audit references are in
`GLOBAL_DIRECT_DAILY_THREE_ESM_LATE_WEATHER_RESULTS_20260917.md`.

A separately registered within-SSP5-8.5 MRI-ESM2-0 diagnostic uses
resident ISIMIP3b `20210512` daily `pr`/`tas` blocks for 2042--2049
and 2092--2099 harvest years. The per-year builder, raw-cell checks,
both independent eight-year audits, a 45-statistic weather summary,
and a separate 45/45 arithmetic audit pass. For every calendar cell,
the eight-year mean feature in the earlier window is subtracted from
the eight-year mean feature in the later window; spatial summaries
weight cells equally, not by cultivated area or production. Mean
contrasts are +16.063 mm season rain, -0.205 wet days, +0.698 days
maximum dry spell, +4.945 mm Rx5day, and +2.382 C season temperature.
The corresponding same-realization mean GMST contrast is +2.249 K.
Spatial 5th and 95th percentiles are heterogeneity descriptors, not
uncertainty bounds. The wet-day spatial median is positive (+0.125)
despite its slightly negative mean. This is one transient scenario
and cannot be divided by the GMST contrast to obtain a forced per-K
coefficient. The pre-result source-inventory correction discloses that
GFDL-ESM4 SSP1-2.6 has a resident two-window pair too; MRI selection
was for generic-pipeline convenience, not unique eligibility.
Methods, resource and hash receipts are in
`GLOBAL_DIRECT_DAILY_MRI_TWO_WINDOW_PROTOCOL_20260917.md` and
`GLOBAL_DIRECT_DAILY_MRI_TWO_WINDOW_WEATHER_RESULTS_20260917.md`.

The distinct GFDL SSP1-2.6 two-window follow-up is predeclared in
`GLOBAL_DIRECT_DAILY_GFDL_TWO_WINDOW_PROTOCOL_20260917.md`. Its
generic 2042 and 2092 anchor builds pass exact sorted season/stage
frame parity with previously validated bespoke GFDL builds in 144/144
tile-year comparisons. The remaining 14 year builds, two eight-year
cross-year source/calendar/hash audits, and separate 45-statistic
weather-arithmetic audit also pass, with all sampled process RSS
below 169 MB. For the same fixed 67,420 calendar cells, the
2092--2099 minus 2042--2049 equal-cell means are +10.656 mm
season rainfall, +0.800 wet days, -0.071 days maximum dry spell,
+1.299 mm Rx5day and +0.014 C season temperature. Yet the same-
realization eight-year mean GMST is -0.02364 K later-minus-earlier.
This short stabilized-scenario weather difference is not a forced
per-K response. A separate pre-result comparison protocol requires
matching keys, weighting, windows and independent audits before
comparing to the UKESM SSP1-2.6 eight-year windows. All nine mean
weather-feature directions agree; UKESM's GMST difference is
+0.370 K. The two ESMs are not pooled or treated as a precision
sample. The audit-gated comparison code is
`scripts/compare_gfdl_ukesm_ssp126_two_window_weather.py`; exact
results and limitations are in
`GLOBAL_DIRECT_DAILY_GFDL_TWO_WINDOW_WEATHER_RESULTS_20260917.md`.
MRI SSP5-8.5 and GFDL SSP1-2.6 must not be pooled as same-scenario
model replication.

For the separate RIME-X source-support extension, the exact daily
GFDL-ESM4 `r1i1p1f1` SSP1-2.6 `pr`/`tas` pairs cover 2031--2060
with three consecutive decadal files per variable. The predeclared
cross-boundary pilot validates 2041 and 2051 harvest-year 10-row
tiles against 686 season and 2,058 stage records per year from the
earlier two-row contiguous pilot. The serial full-grid completion
reuses the audited 2032--2039 and 2042--2049 panels unchanged and
builds only 2040--2041 and 2050--2059. The independent 28-year
audit verifies all 36 latitude tiles in each year, exact 67,420-cell
calendar support, physical and additive stage identities, hashes,
and 252 new raw-daily cell-season reconstructions. The resulting
1,887,760 season and 5,663,280 stage records pass; sampled audit
peak RSS is 176,603,136 bytes. The initial audit failed at an empty
tile because NumPy could not evaluate an object-typed empty groupby
array; the failure resource/log remain retained, and the `v2`
audit skips numerical comparisons only after both tables are
proven empty.

The separate centered 21-year operation must consume actual 28-year
crop-year feature sequences, not interpolate between disjoint
eight-year climate windows. Eight 2042--2049 centers each average
the annual growing-season and crop-stage indicators over their
21 consecutive harvest years. The initial 10-row centered pilot
stopped at a schema-only difference: the old bounded reference
stored fixed crop-calendar geometry without a `21yr_mean` suffix,
whereas the current reusable smoother labels its arithmetic mean.
For the reviewed retry, geometry values are explicitly mapped and
included in exact-key, 1e-9-tolerance parity comparisons. To
respect the fixed 512 MiB memory ceiling, the retry processes at
most two latitude rows in memory and writes parquet row groups
incrementally. The 3,353-cell latitude-100--110 tile matches all
5,488 prior bounded season rows and 16,464 stage rows at sampled
peak 223,150,080 bytes; the maximum-support 5,630-cell tile passes
at 273,072,128 bytes. Neither the source audit nor this smoothing
check estimates a forced response to GMT, crop yield, welfare loss,
or SCC.
The other 34 tiles subsequently complete under the same serial
resource gates, including typed zero-row outputs for calendar-empty
bands. A separate streamed audit checks all 36 centered receipts,
tile hashes, exact crop-calendar cell keys in each center year,
three-stage additive reconciliation, the common 2042--2049
same-realization GMST index and 168 independently recomputed
21-year annual-feature means from the previously audited source
panels. The global centered outputs pass with 539,360 season and
1,618,080 stage records; sampled audit peak RSS is 412,909,568
bytes. Because the eight 21-year windows overlap heavily and
come from one ESM, one scenario, maize, and rainfed management,
they are not independent evidence of a forced precipitation
response and cannot be used as a global yield/damage/SCC estimate.

### Same-cell historical/future crop-weather support

We froze the support test before reading the future values. The analysis uses
the exact 30,654 positive-area MIRCA-2000 rainfed-maize cells common to the
three-ESM late-century direct-daily panels. For each cell and nine features
(season rain, wet days, longest dry spell, Rx1day, Rx5day, season mean
temperature, and three stage-rain totals), we calculate the 1982--2016
minimum, maximum, and empirical 5th and 95th percentiles from the existing
ISIMIP3a GSWP3-W5E5 crop-year features. We then classify every 2092--2099
ISIMIP3b ESM--SSP cell-year without refitting, clipping, or excluding cells.
Area fractions use fixed MIRCA hectares and years receive equal weight.

Construction requires one finite record per cell-year-feature, a common 1 mm
wet-day threshold, fixed `0,0.3,0.7,1` stages, and stage/season precipitation
reconciliation at the pipeline's existing 0.001 mm tolerance. Each future
manifest and tile is hash bound. A separate implementation rehashes and rereads
all 19,416,960 future season/stage rows, recalculates every area-weighted
fraction, and reconstructs every eight-year summary. Because historical and
future weather come from different ISIMIP pathways, this is a conservative
domain-overlap diagnostic rather than a forced-climate-change contrast. Full
results and source hashes are in
`GLOBAL_MAIZE_HISTORICAL_FUTURE_SUPPORT_RESULTS_20260918.md`.

The companion descriptive normalization divides each area-weighted SSP3-7.0
or SSP5-8.5 minus SSP1-2.6 feature difference by the corresponding ESM/member's
eight-year mean annual GMST difference. It uses the same 2092--2099 years,
requires exact resident GMST identities and Gregorian 365/366-day counts, and
does not average the six ESM/contrast ratios into a production coefficient.
An independent implementation rechecks all nine source files and 114 numerical
quantities. Because scenario composition and internal variability remain in
the numerator and denominator, these ratios are descriptive endpoints rather
than a pattern-scaling emulator or marginal-pulse input.

### Published-style monthly GMT--precipitation benchmark

The separate raw-CMIP6 monthly benchmark follows the PEEPS-type
per-ESM, per-calendar-month ordinary least squares form (Kravitz and
Snyder, 2023, doi:10.1371/journal.pclm.0000159), without claiming
that pattern scaling is novel. The design was fixed before fitting in
`PUBLISHED_MONTHLY_GMT_RESPONSE_BENCHMARK_PROTOCOL_20260917.md`.
For each of GFDL-ESM4 (`gr1`) and IPSL-CM6A-LR (`gr`), member
`r1i1p1f1`, historical/SSP1-2.6/SSP5-8.5 monthly `tas` and `pr`
stores were pinned by source version, metadata, coordinate hashes,
calendar, units and license. Exact historical `fx/areacella` fields
were separately source/MD5-checked; their positive finite areas
reconcile with the atmosphere grids at absolute coordinate tolerance
`1e-10` degrees and sum to approximately Earth's surface. A failed
exact-bit comparison exposed only `1e-14`-degree serialization
differences and was retained rather than discarded. Native-area-
weighted monthly `tas` values were then averaged by actual source
month seconds into annual GMST. The model-specific 1981--2010 mean
sets the predictor origin. An independent 50-digit Decimal audit
recomputed all 404 retained historical/future annual GMST values
from the saved monthly means; this verifies reduction arithmetic,
not climate-model truth.

Per model and calendar month, the streaming training regression is
`pr[y,m,g] = alpha[m,g] + beta[m,g] * (GMST[y] - GMST_hist) + e[y,m,g]`
using SSP5-8.5 years 2015--2080 and the native precipitation flux
units `kg m-2 s-1`. A same-year-GMST annual-quantity regression on
precipitation in mm/year, distributed across months in fixed
historical 1981--2010 monthly shares, is the equal-information
comparator; the unchanged historical monthly flux is the second
reference. Chunked float64 sufficient statistics avoid materializing
multi-decadal grids. Every source chunk checksum, parent metadata,
same model/member/calendar and all source months are checked. The
two coefficient files pass 260 independent high-precision saved-
sentinel OLS comparisons. They are stored only in ignored interim
data. SSP1-2.6 2031--2060 is a whole-scenario holdout, and SSP5-8.5
2081--2100 is a late time-block holdout; no fit term or period was
changed after scores were seen.

Native-grid evaluation converts each month's predicted and actual
flux using that month interval, weights every cell by verified
`areacella`, and reports amount RMSE/bias for monthly and annual
totals. It retains negative predictions in amount errors and reports
their counts and minima instead of clipping. Monthly-share total-
variation scores use one common cell-year support on which actual
and all three forecast paths have positive annual amounts and
nonnegative monthly amounts; the area fraction is explicit. Retained
year-level area-weighted sufficient statistics permit a separate
50-digit Decimal audit of all 108 pooled scores (maximum scaled
error `2.01e-16`). Details and all four result tables are in
`PUBLISHED_MONTHLY_GMT_RESPONSE_HOLDOUT_RESULTS_20260917.md`.
The gains over quantity-only on the two in-GMST-range whole-scenario
tests are <1% monthly-amount RMSE but fail the nonnegative rainfall
gate. Most late time-block years exceed training GMT support. These
all-grid predictive checks do not test rainfed-crop calendars,
wet/dry runs, precipitation extremes, heat--moisture dependence,
scenario-invariant causation, FAIR pulse behavior, crop yields or
GIVE welfare. No benchmark result is promoted into the SCC.

For the next frozen crop-footprint check, use the independent-audit-
bound future SSP1-2.6 monthly climatology arrays for 2031--2060 and
their 2030--2059 predecessor years for January-crossing seasons.
The two linear monthly fits are evaluated at their same-realization
mean GMST anomaly for each 30-year window; for the quantity-only
comparator, year-specific annual predictions are divided by actual
source month durations *before* averaging flux, avoiding a leap-year
ratio-of-means approximation. The already validated native-grid
interpolation, fixed MIRCA-2000 rainfed-maize area and phase-2 crop
calendar generate crop-season monthly bins under both published
source-calendar and explicit harvest-year conventions. Amount RMSE/
bias include every cell with valid actual climate/calendar even if a
model forecast is negative. Share total variation and absolute
centroid error use one common physically valid cell support across
all three predictor families, and its area fraction is reported.
The rainfed-maize support has 28,328 valid cells and 99.309% of
mapped area. Both ESMs and both conventions favor the monthly fit
over quantity-only for 30-year climatological season amount and
monthly distribution, but 9/68 crop-cell months remain negative in
GFDL/IPSL. A separate saved-cell-ledger audit reproduces all 100
aggregate scores with zero numerical disagreement. These checks do
not validate daily climate sequences, crop-yield prediction,
attribution, physical pulse response or SCC. Exact source/fit
bindings, the retained failed path-serialization run and every score
are in `PUBLISHED_MONTHLY_GMT_RESPONSE_MAIZE_RESULTS_20260917.md`.
