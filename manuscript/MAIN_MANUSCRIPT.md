# Precipitation patterns, global agricultural damages, and the social cost of carbon

Detailed dated research notes are preserved in [the development log](RESEARCH_DEVELOPMENT_LOG.md); this draft presents the scientific argument and current validated evidence.

## Abstract

**Preliminary research draft, September 22, 2026; no global damage or SCC estimate is reported.**

We develop a precipitation-aware agricultural replacement for GIVE, with the
eventual aim of estimating climate damages without double counting its existing
agriculture sector. The analysis distinguishes rainfall quantity, within-season
distribution and drought, and requires distribution predictors to demonstrate
incremental out-of-sample value rather than assuming their superiority.
Directly reported irrigated and non-irrigated U.S. county yields provide a
historical association check; a separate nationwide panel of all-practice
corn and soybean yields supplies a prospective 2020–2025 prediction test on
counties with low reported irrigated acreage. In that test, adding rainfall
timing, dry spells, and heavy-rain features to seasonal total and temperature
reduces soybean log-yield root-mean-squared error from 0.15546 to 0.14781,
but changes corn error only from 0.18291 to 0.18224. The soybean result
survives alternative fixed-2017 low-irrigation-share screens; corn's small
gain is not robust. Seasonal PDSI is a serious competing moisture predictor,
not an additive rainfall control, and does not displace the terminal soybean
pattern specification on the same sample. These are predictive and conditional
historical results, not causal estimates of climate-change damages.

Separately, two climate models and two scenarios provide spatially global maize
exposure comparisons for 2031–2060 versus 1981–2010. Pooled seasonal rainfall
changes of +0.05% to +2.79% coexist with monthly redistribution and offsetting
regional changes; annual and seasonal quantity-change signs differ across
roughly 20–22% of supported rainfed area. Published crop-model benchmarks
produce strongly model-dependent precipitation contributions, even under
identical external production weights. Original EPIC-TAMU yield-source
comparisons verify a particular imposed joint heat/rainfall scenario on fixed
support; the original rain-only and temperature-only corners remain
unretrieved. A separate direct-daily diagnostic covers five climate models,
three scenarios and the 2092--2099 global rainfed-maize window on fixed crop
area. Under SSP5-8.5 minus SSP1-2.6, area-weighted seasonal rainfall changes
are -67.68/+5.74/-6.94/+10.17/+20.12 mm for GFDL/IPSL/MPI/MRI/UKESM:
the total has no common sign. Wet days decline and the longest dry spell and
Rx1day rise in all five models; Rx5day rises in four. Under SSP3-7.0, rainfall
is positive in two models, while wet days again decline and longest dry spells
rise in all five. A complementary crop-calendar water-balance calculation
applies frozen observational 1982--2011 SPEI parameters to daily precipitation
and Hargreaves--Samani reference evapotranspiration for the same five ESMs and
three SSPs. For rainfed crop-season SPEI-3, all five models are drier in both
higher scenarios for maize and soybean; five-model mean differences relative
to SSP1-2.6 are -0.449/-0.662 for maize and -0.326/-0.542 for soybean under
SSP3-7.0/SSP5-8.5. Across five windows, three SPEI scales, and three fixed
irrigation-area bases, at least four of five models are negative in all 180
crop--scenario cells. These named-model signs are not probabilities. These
validated exposures permit a prespecified endpoint diagnostic against
same-realization 2092--2099 GMST. The origin-constrained rainfed season
SPEI-3 slope is -0.1876 SPEI K-1 for maize and passes every whole-ESM and
whole-scenario holdout against zero change. Soybean's -0.1469 SPEI K-1 slope
fails the whole-ESM rule because MRI reverses the improvement. Across all
feature cells, 37/45 maize and 13/45 soybean links pass the combined rule.
These are multi-forcing endpoint slopes, not transient or marginal-pulse
emulators. Applying the maize slope *conditionally* to the matched core-GIVE
FAIR pulse path passes zero-pulse, pre-pulse and decreasing-pulse numerical
checks; the maximum normalized signal is `3.44568e-4` SPEI per GtC. This
tests the interface but does not validate the endpoint slope as a marginal
emissions response. The short scenario contrasts neither identify forced
rainfall per K nor yield or damage effects. Together these results
establish an auditable empirical and climate-input foundation, not
identified climate damages. In the global country-held-out yield comparison,
no empirical moisture family clears the predeclared promotion gates:
seasonal quantity has weak and uncertain maize gains, the soybean comparison
has inadequate fold support, and distribution and scPDSI are unstable or
worse. We therefore report them as benchmark and sensitivity families rather
than converting them to damages.

As a literature-based climate benchmark, 4,703 published EPA/PEEPS annual
precipitation slopes covering 184 GIVE countries can be mapped directly to
the matched core-GIVE FAIR marginal temperature path. Their country/model
uncertainty is substantial: 53.63% of slopes are positive and 46.37% are
negative. This establishes a reproducible annual-quantity climate link but
does not represent within-season timing, extremes, drought, crop response, or
economic loss.
Validated response transport, compatible climate-pulse inputs, adaptation
calibration and agricultural welfare integration remain necessary before
estimating an incremental social cost of carbon.

Exact samples, contrasts, uncertainty and remaining claim restrictions are in
the linked results records and `RESULTS_STATUS.md`. Historical associations,
future exposure differences and crop-model benchmarks are separate estimands.

## 1. Introduction

Agricultural climate damages can depend on both the quantity and distribution
of weather within a growing season. A country-year annual precipitation
average obscures planting timing, dry-spell duration, waterlogging, and
heavy-rain exposures, but that does not establish that a complex distribution
model will outperform a crop-season quantity measure. These features can
covary with temperature and CO2, so a precipitation-only model can misattribute
joint climate effects.

Prior empirical studies motivate testing rather than presuming this added
complexity. [Fishman (2016)](https://doi.org/10.1088/1748-9326/11/2/024004)
separates rainfall quantity from rainy-day frequency in Indian crop outcomes,
and [Lesk, Coffel, and Horton
(2020)](https://doi.org/10.1038/s41558-020-0830-0) studies the distribution of
hourly rainfall intensity in U.S. maize and soybean yields. [Kuwayama et al.
(2019)](https://doi.org/10.1093/ajae/aay037) provides a U.S. county benchmark
using observed composite drought severity. These studies justify candidate
features and validation tests; none supplies a coefficient that can be
transported directly into a global SCC calculation.

[Santini et al. (2022)](https://doi.org/10.1038/s41598-022-09611-0)
document global associations between crop-yield anomalies and the timing,
duration, and severity of multiscale SPEI drought. [Tuninetti and Davis
(2026)](https://doi.org/10.1038/s41467-026-72715-y) instead map global
rainfed and irrigated crop sensitivity to historical actual-evapotranspiration
shortfalls using a soil-water-balance model and prescribed FAO yield-response
factors. The former motivates the multiscale timing tests; the latter supplies
a spatial process benchmark. Neither is treated as a directly transportable
marginal yield or SCC coefficient.

[Hultgren et al. (2025)](https://doi.org/10.1038/s41586-025-09085-w)
provide the closest published end-to-end benchmark: a global empirical crop
response with within-season precipitation phases, temperature, irrigation,
income, and long-run climate interactions, followed by agricultural valuation
and a FaIR pulse calculation. We have hash-validated the published maize
estimate and its full covariance matrix. Their maize model captures rainfall
quantity and timing jointly: daily GMFD rainfall is summed to months before
polynomial transformation, and a fixed ten-month season is represented by
linear and quadratic rainfall terms for month 1, months 2--4, and months 5+.
The phase structure was selected using nested tests and cross-validation rather
than assumed a priori. Their Supplementary Table S13 reports
partial staple-crop SCC sensitivities of $3.80--$17.75/tCO2 under varietal
switching and $1.71--$7.99/tCO2 with additional flexible production and trade.
These are ranges across changed assumptions, not confidence intervals or this
paper's estimate. The current public data route omits a regression input needed
to reproduce the final local response surface and baseline covariate
distribution, so the published values remain
an external scale/methods benchmark rather than a coefficient or SCC imported
into GIVE.

This study asks: how does the agricultural component of the global SCC change
when a temperature-indexed agricultural pathway is replaced by a joint,
crop-calendar-aligned temperature--precipitation response? The scope is crop
yield and agricultural welfare. Noncoastal infrastructure flooding is deferred
to a distinct future module; coastal surge and sea-level costs remain under
CIAM.

## 2. Contribution and accounting boundary

The contribution is an auditable climate-to-crop-to-welfare-to-SCC chain with
daily precipitation-pattern features, not a second additive damage sector.
The executable contract preserves crop/season-specific coefficients through
response evaluation, applies fixed baseline value weights only after that
step, and blocks incomplete agricultural coverage by default. The new
`JointAgriculture` component emits the same regional `agcost` quantity as the
baseline agriculture component and replaces it. The primary quantity is the
joint climate marginal damage. Any precipitation attribution is a declared
decomposition of a joint model, not a separately identified causal outcome.

This is not the first climate or crop emulator. PEEPS supplies CMIP6
annual/monthly spatial precipitation patterns as functions of global mean
temperature (Kravitz and Snyder, 2023, doi:10.1371/journal.pclm.0000159);
MESMER-M-TP generates spatially coherent monthly temperature--precipitation
fields (Schöngart et al., 2024, doi:10.5194/gmd-17-8283-2024), and a
MESMER-X extension emulates annual-maximum one-day rainfall along global
warming trajectories (Pierini et al., 2026,
doi:10.1088/1748-9326/ae5fad). None alone supplies validated
crop-calendar daily rainfall timing, consecutive dry days, and Rx5day
for our SCC estimand. RIME-X directly maps simple-climate-model GMT
trajectories to warming-level-dependent regional climate and impact
indicator distributions and supports user-defined ISIMIP indicators
(Schwind et al., 2026, doi:10.5194/gmd-19-6797-2026); it is a close
feature-response benchmark, subject to joint-feature and matched-pulse
tests. STITCHES retains high-frequency archived ESM sequences along
target temperature trajectories (Tebaldi et al., 2022,
doi:10.5194/esd-13-1557-2022), while the Kemsley et al. (2024,
doi:10.1002/joc.8320) Markov--gamma generator scales daily wet/dry
and amount parameters with warming. The published DiffESM model
disaggregates monthly rainfall into 28-day daily sequences but leaves
continuity across generated blocks for future work (Bassetti et al., 2024,
doi:10.1029/2023MS004194). Cross-scenario transfer of a precipitation
pattern can fail even where within-scenario reconstruction is adequate
(Kravitz et al., 2017, doi:10.5194/gmd-10-1889-2017). OSCAR-crop
maps CO2, temperature, aggregate growing-season precipitation, and nitrogen
to crop yields inside a compact Earth-system model. The distinguishing target
here is narrower: determine whether crop-stage rainfall timing, dry-spell
persistence, and heavy-rain exposure materially change agricultural marginal
damages relative to an aggregate-water benchmark, using matched pulse/base
paths and a non-overlapping GIVE welfare replacement.

## 3. Data and feature construction

The planned production outcome set includes GDHY gridded yield for maize,
rice, wheat, and soybean; current corrected aggregate-regime diagnostics cover
maize and soybean only. Daily ISIMIP climate fields and GGCMI Phase 3 crop calendars supply
stage-level temperature and precipitation information. Features include
stage-weighted temperature, seasonal precipitation or water balance,
consecutive dry days, wet-day frequency, heavy-rain/water-excess metrics, and
stage-resolved maximum-temperature threshold days and degree-days. Heat
thresholds are registered explicitly rather than supplied by a universal code
default. Partition validation requires ordered thresholds to have nested day
counts and aggregate degree-day differences consistent with those counts,
before stage totals are reconciled to the season. All features are computed at
grid-cell and crop-year level before aggregation. Monthly CRU scPDSI supplies a
calendar-aligned historical candidate for the competing climatic-water-balance
family. The global 1982--1989 and 2012--2016 maize and soybean candidate paths now pass full
source-bound partition validation and complete derived-input allocation
recomputation after constructing 16 seasonal/stage scPDSI features by
irrigation regime and then applying fixed MIRCA shares. The candidate itself
contains no direct-weather terms; a separate matched historical predictive
diagnostic has been fit and is reported below. SPEI and scPDSI/PDSI receive serious
comparison in the U.S. validation and global robustness work; future
water-stress features must be recomputed from matched baseline and pulse
climate paths rather than extrapolating an observed index.

GDHY supplies one crop-season-grid-year yield rather than separate rainfed and
irrigated outcomes. Legacy diagnostics used only the rainfed calendar
exposure. Corrected minimal maize and soybean diagnostics now combine rainfed
and irrigated response bases with independent fixed-baseline crop-area shares
to retain exactly one exposure row per observed yield; the allocator does not duplicate
the outcome across regimes or infer the shares from yield. MIRCA-OS v2 annual
harvested-area maps now supply candidate fixed 2000 weights, with the 2005,
2010, 2015, and 2020 maps retained as vintage sensitivities. The exact 0.5°
maize and soybean mappings pass source, grid, and share checks. Annual MIRCA
rice remains blocked because its monthly source fails metadata checks and the
2000 seasonal reconstruction fails reconciliation to annual Rice; wheat lacks
a documented spring/winter mapping. Every nonlinear weather basis and compound interaction is formed
within each regime before the fixed area shares are applied. This defines an
aggregate-yield reduced form and does not identify separate regime yields;
production weights would require independent regime-specific baseline yields,
and crop-value weights remain reserved for welfare aggregation. Early
primitive-weather-weighted aggregate-regime diagnostics violate this ordering and are
withdrawn. The corrected minimal predictive workflow now has an explicit
contract-aware prebuilt-basis mode; it remains distinct from the unfrozen
production causal response.
For the same 1982--1989 maize and soybean panels, a broader 54-column
candidate contract now passes independent reconciliation after irrigation
allocation. It carries seasonal/stage rainfall amount, normalized
shares/timing/concentration, wet-day frequency and conditional intensity,
CDD, Rx1day, Rx5day, temperature, and interactions. This establishes that
both quantity and temporal-distribution inputs can be represented without
post-aggregation transforms; the 1 mm wet-day definition and response form
remain unselected, and the table is not authorized for fitting.
Matching later-period rainfed and irrigated panels are now complete for maize
and soybean over 2012--2016. After fixed-2000 MIRCA allocation, the direct-
pattern tables contain 165,955 maize and 119,670 soybean crop-grid-year rows,
including 60,818 and 26,748 positive observed yields. Outcomes without an
eligible crop-grid MIRCA weight (484 maize and 433 soybean records) are
excluded rather than infilled. The official GDHY archive also has a temporary
2015 positive-support drop that is restored in 2016; this is retained as a
source-support limitation and complete-positive-support sensitivity, not
repaired in the outcome data.
Coverage also changes materially with the denominator. Current
consecutive-pair cells contain 79.02% of positive MIRCA maize harvested area
and 89.29% of soybean area, even though about 98% of GDHY-observed cells match
a MIRCA weight. A same-vintage area-times-yield proxy is undefined over the
remaining 20.98% and 10.71% of MIRCA area, and no compatible spatial
crop-value input is yet pinned. We therefore do not normalize represented
cells to global agricultural welfare or characterize the sample as global
production coverage.

The secondary U.S. validation track now contains 21,596 paired irrigated and
non-irrigated crop-county-years over 1981--2019: 7,079 corn, 4,845 soybean,
and 9,672 all-classes-wheat pairs. This support is regional, not nationally
representative. All 807 reported county GEOIDs match 2019 TIGER; eight counties
remain under historical-boundary review. All 468 monthly NOAA nClimGrid-Daily
objects for 1981--2019 were acquired and validated: the bounded acquisition
utility checked the frozen HTTP identity, local SHA-512, NetCDF schema, and
exact daily calendar for each of the 27,857,685,556 compressed bytes. The
reproducible raw grid cache was then evicted on 21 September 2026 to conserve
local storage; its URL, HTTP identity, byte count, and checksum inventory is
retained, as are the official county-average source, derived panels, and
student-share file. Registered aggregation over
419 eligible counties and 39 harvest years produces exactly 23,722 paired-
practice rows and 20,228 common direct-weather/PDSI consecutive-year changes;
both assembly and exact recomputation pass. This regional construction enables
a historical predictive comparison but does not estimate a causal weather--
yield response or create a damage/SCC input.

## 4. Empirical design

The production registry includes a hierarchically pooled fixed-effects
candidate with crop/grid controls, year effects, flexible stage weather
functions, and temperature--precipitation interactions. It will be compared
to process-based GGCMI/ISIMIP outcomes and, only as a predictive comparator, a
constrained sequence/ML model. CO2 concentration and adaptation will be
explicit scenario inputs; market feedback will be applied exactly once in the
welfare translation.

The production functional form is not yet frozen. Its registered comparison
set keeps seasonal amount distinct from normalized stage shares and timing,
wet-day frequency distinct from conditional wet-day intensity, CDD distinct
from Rx1day/Rx5day, and mean temperature distinct from crop-specific heat
extremes; registered temperature--water interactions are evaluated jointly.
Direct precipitation-pattern, climatic-water-balance, and soil-moisture
representations are competing water-stress families and are never stacked.
The parsimonious reference is joint temperature plus crop-calendar seasonal
precipitation quantity. Distribution, occurrence, intensity, dry-spell, and
wet-extreme extensions survive only if pre-specified outer holdouts show robust
and stable incremental value; null and worse results are reported plainly, and
the seasonal-quantity reference may become primary. PDSI/scPDSI and SPEI are
serious alternative predictors under those same outer splits, not secondary
checks or extra covariates added to the direct-water specification. Selection
is based on validity, stability, parsimony, and external validation, never SCC
magnitude.

The empirical decision sequence is deliberately ordered. First, predictive
screens compare the seasonal-quantity reference with nested distribution
extensions and mutually exclusive drought-index families on identical support
and outer holdouts. Second, only a specification with a defensible identifying
design can produce historical response draws. Third, climate-induced change in
the selected moisture representation is estimated from matched baseline and
CO2-pulse climate paths. Fourth, validated response draws and climate changes
enter the single agriculture welfare replacement and SCC calculation. Passing
an earlier step does not authorize a claim at a later step. In particular, a
historical scPDSI--yield prediction exercise is not an estimate of how climate
change alters drought, and neither is a drought damage or SCC estimate.

The existing three-model exercise is a deliberately minimal predictive
diagnostic: it omits frequency, intensity, Rx5day, heat, and the alternative
drought families and only indirectly represents normalized timing through
three window totals. The reported pre-revision audits also allowed adjacent
first-difference pairs to share one yield endpoint across temporal or extreme
train/test splits. Those values are legacy dependent stress tests and are stale
under the revised configuration hash. Production model comparison requires
purged observation-disjoint temporal and extreme splits in addition to the
already grid-disjoint spatial blocks; rerunning a purged predictive diagnostic
still does not establish causality or authorize an SCC response.
The revised evaluator and audit validator implement that purge and pass
synthetic failure-mode tests. Real 1982--1989 MIRCA-2000 maize and soybean
minimal diagnostics have also been rerun with zero endpoint overlap in every
temporal and retrospective high-tail stress split. These runs validate the corrected
order-of-operations and split plumbing; they do not promote the minimal basis
to the production response. Because GDHY has one aggregate crop-season-grid-year
yield, the production outcome cell excludes an irrigation dimension. The choice between a
level fixed-effects model with crop-year shocks and a first-difference model
with registered year-shock controls remains unresolved rather than inherited
from the diagnostic.

## 5. SCC implementation

The published Hultgren partial-SCC calculation is used as an external methods
and scale benchmark. Its 16 Table S13 rows use 2023 USD, constant 2%
discounting, SSP3 income, a FaIR 1 GtC pulse in 2025, and assumptions that vary
market geography, elasticities, expenditure caps, CO2 fertilization, and
production flexibility. No unreported central row is inferred. The exact
transcription, source hashes, and closed project-SCC gate are recorded in
`HULTGREN_PARTIAL_SCC_BENCHMARK_20260923.md` and its machine-readable receipt.
Our production result must instead use the registered GIVE currency, pulse,
discounting, regional aggregation, adaptation, and replacement conventions.

For every paired climate draw, a baseline and marginal CO2-pulse path share
GCM/member, crop calendar, socioeconomic path, response draw, and weighting
scheme. The primary future driver derives the exact crop-calendar features
from version-pinned daily ISIMIP3b historical and SSP fields, fits
ESM/member-specific feature responses to same-realization global temperature,
and evaluates both FAIR paths with the same ESM/member and residual innovation.
Annual training GMST is defined as the cos(latitude)-weighted mean of the
pinned daily `tas` field from that exact ESM/member/scenario; an executable
gate requires one finite physical Kelvin value and source per year across all
feature families. Bounded complete-file precipitation and mean-temperature
coverage now includes historical and all three SSPs for four frozen ESMs, with
the fifth ESM represented by SSP3-7.0. Every available cell passes pinned
SHA-512, full decoded content/chronology, historical-boundary, same-realization
GMST, and bounded crop-feature reconciliation gates. This is bounded source
and processing validation, not a fitted feature response.
An unmatched scenario contrast is not treated as a marginal pulse. Whole-ESM
and whole-scenario holdouts, historical-support flags, zero-pulse identity, and
decreasing-pulse convergence must pass before the resulting features can enter
the response. After all empirical, welfare, coverage, and paired-climate gates
pass, cell-level yield responses will be aggregated with fixed baseline
weights, translated to 16 FUND regions, and supplied to the replacement
component; GIVE's existing marginal-damage/discounting machinery will then
calculate the global SCC. Before either member of a paired run, a structural audit requires
`DamageAggregator.damage_ag` to have the sole internal producer
`JointAgriculture.agcost` and requires the baseline `Agriculture` component to
be absent. The unmodified GIVE graph fails this test by design. A passing graph
is an accounting prerequisite, not evidence of response validity or an SCC
result. After the two agriculture component paths run, a second executable
audit requires matched finite crop and regional output arrays, verifies every
required output is identical before the registered first-divergence year, and
applies an all-years identity check to a separate zero-pulse control. These
checks do not validate the empirical response, welfare layer, or full marginal
SCC run. Results report fixed, trend, and upper adaptation scenarios separately.

The outcome-blind input screen currently selects all five ESM realizations
with complete historical and three-SSP coverage for daily precipitation and
temperature variables (80 version-pinned datasets). Acquisition remains a
bounded subset of the 1.757 TB catalogue. All five frozen realizations now have
complete historical and three-SSP `pr`/`tas` cells for the registered smoke
years.
A real two-latitude maize/rainfed engineering cell produces 2,744 crop-years
and 8,232 three-window records per future scenario with exact precipitation
and day-count reconciliation. MRI's four-scenario diagnostic improves 24/44
folds relative to the cell-mean benchmark, but its median RMSE ratio is
0.99971 and worst ratio is 1.09903; it is not promoted. UKESM's corresponding
diagnostic improves 23/44 folds (median ratio 0.99985; worst 1.03248). The
exact five-ESM joint product has 565,950 rows. Whole-ESM folds improve 41/55
(median ratio 0.99760; worst 1.05145), while whole-scenario folds improve 36/44
(median ratio 0.99744; worst 1.01605). The independent validator passes, but
the model is not promoted.
A bounded aggregate numerical smoke then reuses one residual identifier across
baseline and pulse for 880 ESM-feature-year-scale rows. Zero-pulse and
pre-divergence identity, separate baseline/pulse support flags,
direct-versus-centered agreement, and convergence across 0.01, 0.005, and
0.0025 K perturbations pass. Nineteen pulse rows are above and 10 below the
bounded aggregate training range. These are artificial Kelvin perturbations,
not FAIR baseline/pulse paths.
Separately, the pinned core deterministic GIVE/FAIR marginal model produces
2,204 matched temperature rows for 1750--2300 under zero and
0.0001/0.00005/0.000025 GtC pulses in 2020. Baselines are identical across
pulse-size runs, zero and pre-pulse identity are exact, the first nonzero
temperature response occurs in 2021, and the two smallest normalized signals
converge. The maximum response to 0.0001 GtC is 1.8368e-7 K. This establishes
the actual FAIR temperature-delta input. A subsequent version-pinned
engineering sensitivity maps the 2012--2300 FAIR paths to each ESM using its
2012--2014 historical mean. Under the bounded affine surface, absolute anomaly
mapping and centered-coordinate evaluation agree to a maximum `4.55e-12`
across 127,160 paired rows. However, only 5.95% of mapped temperature rows and
35.90% of feature rows remain inside the seven-year training support per
formulation. Mapped baseline GMST first exceeds support in 2021 for GFDL, 2027
for MPI, and 2033 for IPSL, UKESM, and MRI. The equivalence is a coordinate
identity, not evidence for the
reference window or response model, and the support result prohibits
promotion to damages or SCC.
Before extending the surface, we fixed two later-century daily blocks without
examining their features: 2041--2050 and 2091--2100 for all five ESMs, three
SSPs, and `pr`/`tas`. The official metadata gate pins 60 public CC0 files
totaling 124,935,312,957 bytes. This is an acquisition plan only; full content,
GMST, features, and expanded holdouts remain unvalidated, and post-2100 FAIR
years remain outside direct ISIMIP training support.
The first registered GFDL SSP1-2.6 `pr`/`tas` pair for 2041--2050 passes full
SHA-512 and decoded 3,652-day content gates. The paired `tas` also produces ten
annual same-realization GMST rows. The bounded two-latitude-row maize/rainfed
smoke produces 5,488 seasonal and 16,464 stage rows for 2042--2049 with exact
additive reconciliation. The matching 2091--2100 pair and 2092--2099 bounded
feature block pass the same gates. The GFDL SSP3-7.0 2041--2050 pair and
bounded feature block also pass. Relative to matched SSP1-2.6 cells, SSP3-7.0
has mean differences of +0.574 C, -18.33 mm seasonal precipitation, -1.11 wet
days, and +3.20 maximum dry-spell days. These are descriptive forcing
differences, not yield effects. The registered SSP5-8.5 2041--2050 pair and
feature block also pass, as do the SSP3-7.0 and SSP5-8.5 2091--2100 pairs and
bounded 2092--2099 feature blocks. In the exact 181,104-row three-SSP
midcentury product, a simple
whole-scenario GMST adjustment improves only 14/33 feature comparisons versus
a cell-mean benchmark (median RMSE ratio 1.00036; maximum 1.06410), including
only 1/11 when SSP5-8.5 is held out. Exact support flags classify 20,562 held-
out values (11.35%) outside the corresponding two-scenario cell/feature
envelope. The matching 181,104-row end-century product improves 13/33
comparisons (median RMSE ratio 1.00110; maximum 1.23350), with 27,260 held-out
values (15.05%) outside support. A temperature-only sensitivity reclassifying
the validated FAIR paths against the expanded 287.659--291.189 K GFDL GMST
envelope moves the last within-support baseline year from 2020 through 2300;
common-random-number,
zero/pre-divergence identity, and decreasing-pulse convergence checks still pass. The adverse
holdout result is engineering evidence against promotion, not a yield effect.
No yield is attached to these smokes and no climate-feature response has been
fitted. The evidence establishes software behavior, not future agricultural
damages.

Separately, a source-locked, memory-bounded full-grid engineering run now
extracts one GFDL-ESM4 SSP1-2.6 harvest year (2032) for rainfed maize:
67,420 valid crop-calendar cell-years and 202,260 stage records. All 36
latitude tiles and 21 independently recomputed raw daily cells pass. This
establishes a feasible low-memory input construction, not multi-year or
multi-model coverage and not an estimated warming--rainfall, yield, or damage
response. The locked result and validator record are in
`GLOBAL_DIRECT_DAILY_GFDL_FULL_2032_MAIZE_RESULTS_20260917.md`.
The same preregistered, independently checked tiling route now covers all
eight harvest years 2032--2039 within this single GFDL-ESM4 SSP1-2.6
source decade (539,360 rainfed-maize calendar cell-years; 1,618,080 stage
records). Exact cross-year calendar masks and physical bounds pass. This
remains source-only input construction; neither year-to-year variation nor
these counts identify a warming response, crop loss or SCC.
Two additional full-grid source-only anchors in this same GFDL-ESM4
SSP1-2.6 run, harvest years 2042 and 2092, have separately passed source
identity, 36-tile construction, fixed 21-cell raw-weather validation and
exact crop-calendar/physical checks. These anchors extend the temporal
range of available crop weather inputs; they do not convert a one-ESM,
one-scenario collection into an identified GMT response.
The first second-ESM extension has also produced and independently
validated exact-cell UKESM1-0-LL SSP1-2.6/3-7.0/5-8.5 rainfed-maize
crop-weather features for harvest year 2092. Relative to SSP1-2.6, the
unweighted calendar-cell mean seasonal precipitation differs by
+9.60/+26.23 mm in SSP3-7.0/SSP5-8.5, but only 50.2%/52.2% of cells
are wetter; the additional rainfall is concentrated in middle-stage
means, and the SSP5-8.5 maximum-dry-spell mean differs little. These
single-year scenario contrasts are descriptive and contain no crop
outcomes; they cannot be interpreted as a GMT response or damages.
The same registered source-only tiling method now covers all five
ISIMIP3b ESMs and three SSPs for harvest year 2092, with independent
raw-cell and exact-calendar validation for each of the 15 panels.
This broadens model/scenario *input coverage* but is still just one
weather year per panel; neither an emulated GMT response nor an
agricultural SCC effect has been estimated from it.
The same source-locked route now independently validates three
UKESM1-0-LL scenario panels at harvest year 2042 as well, and eight
consecutive late-century harvest years 2092--2099 under UKESM
SSP1-2.6. The latter used separately audited one-year tiles after an
eight-year tile hit the 512 MiB resource guard; the complete panel
has 539,360 season and 1,618,080 stage records. The one-year 2042
scenario rain differences from SSP1-2.6 (+2.04/-4.06 mm for
SSP3-7.0/SSP5-8.5) differ in sign and magnitude from the 2092
single-year differences; neither date isolates forced rainfall
change. Same-realization annual temperature parquets and feature
sources are hash-aligned for all six anchors, but a validated
GMT-to-crop-weather response, yield impact and SCC remain open.
The full-grid SSP1-2.6 daily-feature panel now also spans all eight
harvest years 2042--2049, yielding two separately audited eight-year
UKESM weather windows when paired with 2092--2099. This supplies
1,078,720 calendar-cell seasons and 3,236,160 stages across the
two nonadjacent windows, but is still one ESM/scenario and does not
by itself establish a forced precipitation response or damages.

The next registered IPSL-CM6A-LR SSP1-2.6 `pr`/`tas` pairs for 2041--2050 and
2091--2100 also pass exact byte, SHA-512, decoded-content, same-realization
GMST, and bounded feature/reconciliation gates. Their paired daily files use
a fixed 12:00 timestamp rather than GFDL's 00:00; both variables share each
exact 3,652-day sequence. The IPSL SSP3-7.0 2041--2050 and 2091--2100 pairs and
bounded feature blocks pass the same gates. Both IPSL SSP5-8.5 pairs and
bounded feature blocks also pass. The MPI-ESM1-2-HR SSP1-2.6 2041--2050 and
2091--2100 pairs also pass the exact 3,652-step 12:00 content,
same-realization GMST, and bounded maize/rainfed reconciliation gates, raising
registered progress to 28 of 60 files and fourteen feature blocks. The MPI
SSP5-8.5 2041--2050 pair passes the same gates. Together with the separately
registered MRI SSP1-2.6 2041--2050 block, progress reaches 32 of 60 files and
sixteen feature blocks. Relative to matched MPI SSP1-2.6 cells, its
mean differences are +0.237 C, +17.88 mm seasonal rain, +1.37 wet days, -1.00
maximum dry-spell days, +1.71 mm Rx1day, and +6.75 mm Rx5day. These three MPI
later-century cells are engineering evidence only and do not support a whole-
scenario or whole-ESM response claim. The MRI SSP3-7.0 2041--2050 pair and
bounded block also pass, raising tracked
progress to 34 of 60 files and seventeen feature blocks. Relative to matched
MRI SSP1-2.6 cells, mean differences are +0.369 C, -11.02 mm seasonal rain,
-1.07 wet days, +0.23 maximum dry-spell days, -0.32 mm Rx1day, and +0.26 mm
Rx5day. These are descriptive climate differences; incomplete MRI scenario and
period coverage precludes a whole-scenario or expanded whole-ESM claim. The
MRI SSP5-8.5 pair subsequently completes the midcentury scenario matrix;
relative to SSP1-2.6, matched means are +0.777 C,
-8.81 mm seasonal rain, +0.28 wet days, -2.83 maximum-dry-spell days, -1.50 mm
Rx1day, and -2.68 mm Rx5day. The resulting 181,104-row MRI three-scenario
midcentury product improves 15/33 comparisons (median RMSE ratio 1.00027;
maximum 1.04233), including 4/11 for held-out SSP5-8.5, and places 21,236
values (11.73%) outside support. This adverse single-ESM result raises tracked
progress to 36/60 files and eighteen blocks but does not authorize a response,
damage, or SCC. MRI SSP1-2.6 and SSP3-7.0 end-century pairs now pass the same
exact file, GMST, feature, and reconciliation gates. Matched SSP3-7.0 minus
SSP1-2.6 means are +2.928 C, +2.24 mm seasonal rain, -0.97 wet days, +2.41
maximum-dry-spell days, +0.25 mm Rx1day, and +1.15 mm Rx5day. The MRI SSP5-8.5
end-century pair and block also pass, raising tracked progress to 42/60 files
and twenty-one blocks. Its matched SSP5-8.5-minus-SSP1-2.6 means are +4.591 C,
-13.23 mm rain, -2.62 wet days, +5.44 maximum-dry-spell days, +0.75 mm Rx1day,
and +0.56 mm Rx5day. The 181,104-row end-century whole-scenario audit improves
16/33 comparisons (median RMSE ratio 1.00006; maximum 1.06514), including 9/11
for held-out SSP5-8.5, and flags 27,090 values (14.96%) outside support. This
mixed, adverse result leaves response, damage, SCC, whole-ESM, and FAIR
feature-support gates closed.
The remaining registered MPI-ESM1-2-HR SSP3-7.0 mid- and end-century pairs and
SSP5-8.5 end-century pair also pass exact file, content, same-realization GMST,
bounded-feature, and reconciliation gates, raising tracked coverage to 48/60
files and twenty-four blocks. Matched SSP3-7.0 minus SSP1-2.6 seasonal-rain
differences are -4.38 mm at midcentury and -17.02 mm at end century; matched
SSP5-8.5 minus SSP1-2.6 is -13.20 mm at end century. These climate-support
contrasts are not yield responses or damage estimates and do not open any SCC
gate. The corresponding MPI whole-scenario audits improve 14/33 feature
comparisons at midcentury and 15/33 at end century, while 11.65% and 15.24%
of held-out values are outside exact support. These adverse results do not
promote the emulator. A four-ESM whole-ESM audit improves 27/44 comparisons at
midcentury but only 12/44 at end century, with 8.34% and 9.47% of held-out
values outside exact three-ESM support. Because UKESM remains absent, this
does not complete the frozen five-ESM validation gate. The first later-century
UKESM1-0-LL pair, SSP1-2.6 at midcentury, passes exact catalogue bytes/SHA-512,
complete ESM-specific midnight chronology, full decoded content, same-
realization GMST, and exact seasonal/stage reconciliation for the bounded
maize/rainfed block. This raises coverage to 50/60 files and twenty-five
blocks, but five UKESM pairs and the complete five-ESM holdout are still
missing; response, damage, welfare, and SCC authorization remains false.
The matching UKESM SSP1-2.6 end-century pair also passes, with byte-identical
GMST, 5,488-season/16,464-stage feature, and reconciliation reruns. Separate-
slice end-century-minus-midcentury means are +0.849 C, -3.19 mm rain, +0.33
wet days, +0.49 maximum-dry-spell days, +0.69 mm Rx1day, and +2.48 mm Rx5day.
These descriptive period means are not a yield response or causal contrast.
Coverage is 52/60 files and twenty-six blocks; four UKESM pairs and every
production gate remain open. The UKESM SSP3-7.0 midcentury pair passes the
same gates. Relative to the exact-key SSP1-2.6 cell, mean changes are +0.876 C,
-6.76 mm seasonal rain, -0.72 wet days, +2.66 maximum-dry-spell days, -0.53 mm
Rx1day, and +1.60 mm Rx5day. Coverage is 54/60 files and twenty-seven blocks.
This is descriptive climate-feature support, not a response, damage function,
or SCC input. The UKESM SSP3-7.0 end-century pair also passes; relative to
exact-key SSP1-2.6, mean changes are +4.293 C, +8.32 mm rain, +1.07 wet days,
+0.60 maximum-dry-spell days, +1.46 mm Rx1day, and +2.85 mm Rx5day. Coverage
is 56/60 files and twenty-eight blocks; only the two SSP5-8.5 UKESM pairs
remain before the five-ESM rerun. The UKESM SSP5-8.5 midcentury pair also
passes; its exact-key SSP5-8.5-minus-SSP1-2.6 mean changes are +1.195 C,
+5.16 mm rain, -0.19 wet days, +0.55 maximum-dry-spell days, +2.37 mm Rx1day,
and +6.68 mm Rx5day. Coverage is 58/60 files and twenty-nine blocks; the last
UKESM pair and every response, damage, welfare, and SCC gate remain open. For
the complete UKESM midcentury three-scenario product, GMST adjustment improves
only 13/33 whole-scenario feature comparisons over the cell-mean benchmark;
the maximum RMSE ratio is 1.22120 and 12.21% of held-out values lie outside
exact support. This adverse result prevents production promotion. For
the five-ESM midcentury product, GMST adjustment improves 32/55 whole-ESM
comparisons, but the maximum RMSE ratio remains 1.08533 and 6.47% of values
lie outside exact four-ESM support. The final UKESM SSP5-8.5 end-century pair
completes all 60 file gates and thirty bounded feature blocks. Its matched
SSP5-8.5-minus-SSP1-2.6 means are +5.918 C, +29.61 mm rain, +2.46 wet days,
+0.93 maximum-dry-spell days, +2.44 mm Rx1day, and +4.68 mm Rx5day. The UKESM
end-century whole-scenario audit improves 17/33 comparisons, with 16.51% of
values outside exact support. Across the complete five-ESM end-century product,
GMST adjustment improves 30/55 comparisons and 7.14% of values lie outside
exact four-ESM support. These are engineering support diagnostics; FAIR
baseline/pulse, response, damage, welfare, and SCC gates remain open. For the
deterministic 2,376,990-row early/mid/end-century join, the same matched FAIR
temperature paths generate 127,160 common-random-number feature pairs. All
63,580 feature levels per alignment method are within the enlarged bounded
envelope, while 44 temperature rows (MPI in 2012) are below support. Zero-pulse
and pre-divergence identity, direct/centered agreement, and decreasing-pulse
convergence pass. This is a bounded one-crop/two-latitude engineering result;
the affine response surface remains unpromoted and no damage or SCC use is
authorized. For
IPSL, SSP3-7.0 relative to matched SSP1-2.6
cells has midcentury mean
differences of +0.365 C, +13.22 mm seasonal rain, +0.93 wet
days, -1.36 maximum dry-spell days, +2.18 mm Rx1day, and +3.84 mm Rx5day. The
end-century means are +4.146 C, +25.70 mm seasonal rain, +2.85 wet days, -2.26
maximum dry-spell days, +3.12 mm Rx1day, and +4.47 mm Rx5day. These are
descriptive forcing differences, not yield effects. Matched midcentury
SSP5-8.5-minus-SSP1-2.6 means are +0.607 C, +19.88 mm seasonal rain, +2.07 wet
days, -0.77 maximum dry-spell days, +2.01 mm Rx1day, and +3.13 mm Rx5day. In
the exact 181,104-row IPSL three-SSP midcentury product, whole-scenario GMST
adjustment improves only 15/33 feature comparisons versus the cell-mean
benchmark (median RMSE ratio 1.00028; maximum 1.02568), including 3/11 for
held-out SSP5-8.5. Exact support flags put 20,529 values (11.34%) outside the
two-scenario envelope. The matching IPSL end-century product improves only
10/33 comparisons (median RMSE ratio 1.00275; maximum 1.27466), including
2/11 for held-out SSP5-8.5, and places 30,619/181,104 values (16.91%) outside
support. These adverse single-ESM results do not complete whole-ESM validation
and do not authorize a response, damage, or SCC.

## 6. Results

### 6.1 Climate-feature validation

Report calendar coverage, baseline alignment, daily-feature distributions, and
agreement across weather products.

The current direct-daily global rainfed-maize climate diagnostic covers
GFDL-ESM4, IPSL-CM6A-LR, MPI-ESM1-2-HR, MRI-ESM2-0 and UKESM1-0-LL
under three SSPs for 2092--2099. Each of the 120 annual panels has 67,420
crop-calendar cells; fixed MIRCA-OS v2 rainfed-maize weights retain 30,654
exactly common cells and 99.9559% of mapped positive area. Independent audits
bind every source/year manifest and reconstruct the annual and contrast
arithmetic. For SSP5-8.5 relative to SSP1-2.6, area-weighted growing-season
rainfall is -67.68/+5.74/-6.94/+10.17/+20.12 mm across the five models,
while wet days decline and maximum dry-spell length and Rx1day rise in all
five; Rx5day rises in four. Under SSP3-7.0, rainfall is positive in only two
models, wet days decline in all five, maximum dry-spell length rises in all
five, and Rx1day/Rx5day rise in four/three. Thus total quantity and crop-stage
allocation remain model-dependent even where frequency and dry-spell signs
are more stable. The five-model sign counts are not probabilities or
confidence intervals; each model contributes one realization and only eight
terminal years. Full values and audit hashes are in
`FIVE_ESM_MAIZE_AREA_WEATHER_RESULTS_20260921.md`.

The complementary published-pattern benchmark retains 4,703 finite
country/model annual-precipitation slopes across all 184 GIVE countries after
explicitly preserving 81 unavailable country/model pairs. Across the retained
pairs, 53.63% of slopes are positive and 46.37% are negative; the ensemble
median is positive for 103 countries and negative for 81. Only nine country
ensembles have a positive 5th percentile and four have a negative 95th
percentile, underscoring model uncertainty. Applying each slope to the actual
matched FAIR pulse-minus-baseline temperature gives a transparent
annual-quantity precipitation path. For the smallest tested pulse, normalized
temperature responses from the two smallest pulse sizes agree over 2021--2300
to a maximum relative discrepancy of `1.5764e-4`; an independent
implementation reproduces all 18 selected pulse/year summaries and convergence
statistics. This benchmark does not create monthly or daily rainfall, dry
spells, extremes, drought indices, or crop outcomes and is not an agricultural
damage or SCC estimate. Protocol, results, and exact artifact hashes are in
`EPA_ANNUAL_COUNTRY_PATTERN_RESULTS_20260921.md` and
`EPA_FAIR_ANNUAL_PRECIPITATION_PULSE_RESULTS_20260921.md`.

In a separate, predeclared **within-SSP5-8.5** MRI diagnostic, the
2092--2099 minus 2042--2049 equal-calendar-cell mean differences are
+16.06 mm seasonal rainfall, -0.21 wet days, +0.70 days in maximum
dry-spell length, and +4.94 mm Rx5day. Its independent 45-statistic
arithmetic audit passes. The median wet-day difference is positive,
illustrating spatial heterogeneity behind the slightly negative mean.
This one-ESM, two-short-window comparison is not a forced precipitation-
per-K slope or agricultural damage; the full result and source
qualification are in
`GLOBAL_DIRECT_DAILY_MRI_TWO_WINDOW_WEATHER_RESULTS_20260917.md`.

The separate GFDL-ESM4 SSP1-2.6 2042--2049 versus 2092--2099
two-window diagnostic also passes complete daily-source, anchor-parity,
cross-year and independent weather-arithmetic audits. Its equal-cell
later-minus-earlier mean season rain is +10.66 mm, wet days +0.80,
maximum dry spell -0.07 days and Rx5day +1.30 mm. A predeclared
same-SSP UKESM comparison has matching directions for these features,
but GFDL's mean GMST is **0.024 K lower** in the later window whereas
UKESM's is +0.370 K higher. These short, stabilized-scenario weather
differences cannot identify a forced global-warming precipitation
response, and no pooled two-model or yield result is inferred. Source
and comparison receipts are in
`GLOBAL_DIRECT_DAILY_GFDL_TWO_WINDOW_WEATHER_RESULTS_20260917.md`.

The historical CRU scPDSI candidate covers 240,784 maize crop-grid-years
(115,758 positive GDHY outcomes) and 176,537 soybean crop-grid-years (47,653
outcomes) during 1982--1989, plus 150,490/59,772 and 110,336/26,601 during
2012--2016, after complete-key drought-coverage and MIRCA-weight gates. The
raw source, calendars, stage partitions, area weights, allocation audit, and
final candidate are hash-bound; the validator fully recomputes allocation from
the derived stage tables without claiming full raw-metric recomputation. This
closes a data-construction gate for one competing
historical drought representation. The diagnostic -2 threshold is not a
selected drought definition. The candidate panel itself fits no response; the
separate downstream predictive diagnostic emits no coefficients and selects no
production model. CRU scPDSI cannot supply the matched future baseline/pulse
drought path required for SCC.

Four data-only common-support assemblies place this historical benchmark and
the direct-weather candidate on identical crop-grid-year support while keeping
their 16 and 54 features in separate, mutually exclusive views. Common
rows/positive outcomes and direct-only dropped rows/positive outcomes are
240,784/115,758 and 24,744/1,921 for maize in 1982--1989;
176,537/47,653 and 14,935/269 for soybean in 1982--1989;
150,490/59,772 and 15,465/1,046 for maize in 2012--2016; and
110,336/26,601 and 9,334/147 for soybean in 2012--2016. No scPDSI-only row or
observed outcome is dropped in any bundle. The validator verifies hashes and
recomputes the intersection from the supplied immediate candidate tables, but
does not rerun raw-source pipelines or bind their validation receipts; those
upstream receipts remain an external prerequisite. This assembly estimates no
model or causal effect and produces no coefficient, model-selection, future-
projection, damage, or SCC result. The empirical hierarchy therefore remains
unchanged: seasonal quantity is the direct-weather reference, distribution is
retained only for robust stable outer-holdout value, and drought families
compete mutually exclusively rather than stack.

**Historical drought-family predictive comparison.** A
coefficient-suppressing diagnostic compares seasonal quantity and historical
scPDSI on 209,036 identical maize and soybean consecutive-year pairs with the
same crop-stage temperature and heat controls. Direct quantity has the lowest
mean RMSE across five unbuffered spatial folds for maize (0.288589 versus
0.290401 for controls and 0.288697 for the best scPDSI specification) and
soybean (0.209670 versus 0.211282 and 0.210183), lowering RMSE in all ten
crop-fold comparisons. The gains are small and metric-sensitive: direct
quantity lowers MAE in four of five maize folds but only two of five soybean
folds. The seasonal scPDSI summary has the lowest RMSE in all five maize stress
subsets, while direct quantity wins three of five soybean stress subsets. An
independent clean-room refit reproduces all 110 aggregate metrics exactly. No
coefficient or row-level prediction is emitted.

These diagnostics weight crop-grid-year pairs equally and use unbuffered
spatial folds. A separate paired bootstrap resampling crop-specific 10-degree
cells finds that every one of the 12 scPDSI-versus-direct RMSE/MAE intervals
includes zero. For direct quantity versus controls, the pooled OOF RMSE
difference interval is entirely below zero for maize but ends about 0.000001
above zero for soybean; both MAE intervals include zero. These are descriptive
loss sensitivities conditional on fixed fold fits, not population confidence
intervals, training/model-choice uncertainty, or response uncertainty.
Because the CRU scPDSI product uses a 1901--2025 full-record calibration, its
early-to-later score is retrospective rather than a genuinely prospective
forecast. The comparison selects no production response, reports no SPEI
result, and does not identify a causal effect, project climate-induced drought
change, or authorize damages or an SCC input.

**Published global water-stress spatial benchmark.** The four official
Tuninetti--Davis maize/soybean rainfed/irrigated 5-arc-minute sensitivity maps
were independently matched to our crop-calendar SPEI3 contrasts on frozen
0.5-degree support. All eight crop--regime--scenario cells have negative
area-weighted mean SPEI3 changes, ranging from -0.320 to -0.791. Spatial rank
agreement is weak and mixed: area-weighted correlations between published
historical ETa-tail loss severity and projected drying range from -0.267 to
+0.225. Rainfed maize is positive (0.042 under SSP3-7.0 and 0.225 under
SSP5-8.5), irrigated maize is negative (-0.267 and -0.218), rainfed soybean is
negative under area weighting (-0.121 and -0.079), and irrigated soybean is
positive (0.172 and 0.119). All five climate models project drying in only
28%--54% of common cells even though the global means are negative; at least
four project drying in 55%--74%.

An independent audit passed 450,966 numerical checks and twelve direct raw
ASCII-block checks. The mixed spatial result supports preserving irrigation
structure and process-based benchmarking, but rejects direct use of the
published historical-tail map as a universal future yield-response or SCC
coefficient. Full results and hashes are in
`TUNINETTI_2026_SPATIAL_VALIDATION_RESULTS_20260922.md`.

### 6.2 Yield-response validation

Report spatial, temporal, and extreme-year held-out skill; coefficient and
functional-form uncertainty; and comparison with process-model ranges.

**Published-structure U.S. drought benchmark (September 22, corrected).** A
primary-source audit established that Kuwayama et al. sum weekly drought
exposure from October of the preceding year through September of the harvest
year. We therefore froze a correction before acquiring year-2000 inputs or
inspecting corrected estimates; the earlier January--December result remains
an auditable timing sensitivity. The corrected archive contains 574 official
state-year files and 2,209,813 county-weeks. Its 39,299 unique county-years have
mean D0--D4 county-area-equivalent weeks of 8.603, 5.739, 3.906, 2.287, and
0.821, close to the paper's agricultural-area means of 8.47, 5.66, 3.87, 2.26,
and 0.80 on 40,040 observations. Similar means validate source scale but do not
establish identical spatial exposure.

The corrected drought-only design retains county and year fixed effects,
state-specific trends, and the reconstructed 1997/2002/2007/2012 Census
irrigation rule. The all-U.S. classifier contains 2,913 eligible counties (883
irrigated, 2,030 dryland); excluding its four Hawaii counties gives the exact
continental count of 2,909 (879 irrigated, 2,030 dryland) reported by the
paper. All
twenty category associations remain negative, and every same-category dryland
estimate is more negative than its irrigated counterpart. Dryland corn ranges
from -0.136% per D0 week to -1.141% per D4 week; dryland soybean ranges from
-0.175% to -0.839% across D0--D3 and is -0.619% at D4. Correcting timing reduces
the calendar-year D4 magnitudes materially, particularly soybean (-2.202% to
-0.619%), demonstrating that numerical severity gradients are window-sensitive.

Adding independently prepared April--September rainfall and heat controls
attenuates coefficients and breaks monotonicity. Corn-dryland D2/D3 and soybean-
dryland D1/D2 remain negative with state-cluster p-values below .05; other
dryland categories do not. Corn-dryland D2--D4 and soybean-dryland D1--D3 retain
negative signs after every represented-state deletion, but corn D1 and soybean
D4 do not. Irrigated soybean has a positive, precise D4 coefficient after direct
weather controls. This pattern supports broad drought/yield and irrigation-
heterogeneity validation, but rejects interpretation of individual mutually
exclusive category slopes as structural marginal damages.

Independent joint-design checks reproduce drought-only coefficients within
`1.46e-11`, weather-hierarchy coefficients within `1.23e-08`, and state-
robustness covariance and sentinel deletions within predeclared tolerances. All
runs remain below 455 MB RSS. The heat basis is project-consistent rather than
the paper's exact degree-day construction, and county-area exposure does not
replace the paper's agricultural-area intersection. No coefficient is
transported into the global response or SCC calculation. Full methods,
uncertainty, hashes, and limitations are in
[`US_USDM_OCTSEP_RESULTS_20260922.md`](../US_USDM_OCTSEP_RESULTS_20260922.md).

**Agricultural-area spatial-fidelity sensitivity.** We then replaced
whole-county drought shares with two frozen, outcome-blind approximations to
the paper's agricultural-land intersection: cultivated CDL classes plus
fallow/idle cropland, and the same mask plus grassland/pasture. The 3.96 km
equal-area route uses all 679 weekly USDM vector maps and the official 2008
30 m CDL while staying below the 640 MiB memory ceiling. On a common 36,803
county-year support, agricultural weighting shifts D0--D4 mean exposures only
modestly. All twenty drought-only slopes remain negative under both masks and
preserve the dryland-versus-irrigated qualitative ordering. Across the twenty
terms, the largest absolute agricultural-versus-county coefficient movement is
0.01593 percentage point per equivalent week.

The direct-weather conclusion is also unchanged. Under the cultivated mask,
corn-dryland D2/D3 and soybean-dryland D1/D2 remain negative with state-cluster
p-values below .05 and retain their signs after every represented-state
deletion; several other terms are imprecise or change sign. The two
agricultural masks differ by at most 0.00806 percentage point in the
weather-controlled model. Independent validators reproduce slopes, covariance,
and sentinel deletions within predeclared tolerances. These results show that
coarse spatial weighting is not driving the historical benchmark, but they do
not supply causality, a future climate-to-drought link, global transfer, or an
SCC input. A subsequent outcome-blind multi-resolution audit finds small
typical 3.96 km error but fails its frozen maximum gates: weekly share TVD
reaches 0.1779 and one annual category differs by 1.5174 weeks. By contrast,
990 m weekly TVD versus native 30 m has median 0.00149, 90th percentile
0.00537, and maximum 0.01145. We therefore retain the 3.96 km estimates only as
diagnostics and require a partitioned national 990 m rebuild before finalizing
agricultural-area coefficients. Complete results are in
[`US_USDM_AGRICULTURAL_AREA_RESULTS_20260922.md`](../US_USDM_AGRICULTURAL_AREA_RESULTS_20260922.md)
and
[`US_USDM_MULTIRESOLUTION_SENTINEL_RESULTS_20260923.md`](../US_USDM_MULTIRESOLUTION_SENTINEL_RESULTS_20260923.md).

**Current nationwide U.S. predictive benchmark (September 16).** The
pre-outcome fixed-2017 Census screen selects counties with at most 10%
reported irrigated crop acreage; the NASS outcome is still *all-practice*
yield, not observed rainfed yield. Models fitted in 1981--2019 are scored
on the same crop-specific county-years in 2020--2025. With county fixed
effects, a common trend, and temperature controls, terminal log-yield RMSE is:

| Crop | Seasonal rainfall quantity | Quantity plus timing/dry spells/heavy rain | Competing seasonal PDSI |
|---|---:|---:|---:|
| Corn | 0.18291 | 0.18224 | 0.18469 |
| Soybean | 0.15546 | 0.14781 | 0.15307 |

The soybean pattern extension improves all six annual scores in the main
screen, but the corn difference is small and unstable. Post-result fixed-2017
20% and 30% screens retain soybean's pooled gain, whereas corn's gain remains
near zero; 2022-vintage composition screens are not prospective validation.
In a further post-result state-composition audit on the exact fixed forecasts,
soybean's pooled gain remains positive after omitting any single state
(minimum +0.00589 log-yield RMSE points), but only 18 of 28 state scores
favor the pattern group and North Dakota worsens. Corn's leave-one-state-out
range includes a negative gain. This is score composition, not a new
geographic holdout or independent confirmation; details are in
[`US_COUNTY_AVERAGE_STATE_COMPOSITION_RESULTS_20260916.md`](../US_COUNTY_AVERAGE_STATE_COMPOSITION_RESULTS_20260916.md).
These are model-family comparisons, not separate additive damages. They do
not separate precipitation from temperature causally or establish transfer
to global agriculture. The exact samples, state-trend sensitivity, PDSI
construction, independent checks, and conditional uncertainty are in
[`US_COUNTY_AVERAGE_PDSI_COMPETITOR_RESULTS_20260916.md`](../US_COUNTY_AVERAGE_PDSI_COMPETITOR_RESULTS_20260916.md)
and [`US_COUNTY_AVERAGE_IRRIGATION_SCREEN_RESULTS_20260916.md`](../US_COUNTY_AVERAGE_IRRIGATION_SCREEN_RESULTS_20260916.md).

A preregistered count-only attempt to obtain a newer practice-specific state
validation target failed its support gate. Exact 2020--2025 NASS survey queries
contain only one irrigated and one non-irrigated corn state row per year and no
practice-specific soybean state rows. We therefore do not acquire or model
those state outcomes and do not relabel the all-practice county terminal test
as direct non-irrigated validation. See
[`US_STATE_DIRECT_PRACTICE_TERMINAL_SUPPORT_RESULTS_20260921.md`](../US_STATE_DIRECT_PRACTICE_TERMINAL_SUPPORT_RESULTS_20260921.md).
A second count-only route through 2012/2017/2022 Census county production and
harvested area also fails: irrigated corn area is reported, but the identically
filtered production series is absent, and all tested non-irrigated and soybean
practice cells lack matched quantities. No yield ratios are constructed
([`US_CENSUS_DIRECT_PRACTICE_OUTCOME_SUPPORT_RESULTS_20260921.md`](../US_CENSUS_DIRECT_PRACTICE_OUTCOME_SUPPORT_RESULTS_20260921.md)).

**Historical measurement and direct-practice checks.** On the exact
11,861 regional crop/county/year keys, county-average and older gridded
weather measurements are close for seasonal totals but differ more for
nonlinear dry-spell and heavy-rain metrics; neither source is certified as
ground truth. Refitting the original 1981--2018 paired irrigated/nonirrigated
association on identical keys with county-average weather barely changes
the registered +100-mm ratio contrasts (corn −7.54973% to −7.52542%; soybean
−4.32422% to −4.30556%). These are conditional associations, not causal
irrigation effects or SCC inputs. The exact estimator and independent
recomputation records are in
[`US_COUNTY_WEATHER_ESTIMATOR_COMPARISON_RESULTS_20260916.md`](../US_COUNTY_WEATHER_ESTIMATOR_COMPARISON_RESULTS_20260916.md)
and [`US_PAIRED_PRACTICE_WEATHER_ROUTE_RESULTS_20260916.md`](../US_PAIRED_PRACTICE_WEATHER_ROUTE_RESULTS_20260916.md).

**National U.S. zero-outcome support.** The locked 1981--2019 all-practice
corn source contains 499 reported zero-yield county-years in 150 counties and
217 spells. Of these, 419 rows pass the fixed geography gate, only 45 have a
usable fixed-2017 irrigation share, and only seven meet the 10% high-rainfed
selector. The longest spell is 10 years and 118 rows have an adjacent positive
observation. All reported zeroes occur during 1998--2009 even though the
declared source spans 17 earlier and 10 later years, and the five most
represented states contain 73.55% of the zero rows. Among adjacent-positive
rows, only 15 have an eligible fixed irrigation share and 4/5/5 meet the
10/20/30% high-rainfed selectors. The audit retains rather than recodes
zeroes, but their temporal and geographic concentration prevents treating
them as a generic crop-failure signal; it does not choose a two-part outcome
model or estimate a response.

Across counties with numeric crop-specific irrigation shares in the 2012,
2017, and 2022 Censuses, an outcome-free descriptive audit finds 2017--2022
agreement of 92.28% for corn, 92.64% for soybeans, and 84.16% for wheat under
the 10% high-rainfed selector. Corresponding share correlations are 0.938,
0.954, and 0.834. Census vintage is therefore a material wheat sensitivity;
the audit does not change the primary pre-outcome 2017 selector, identify an
irrigation effect, or authorize a response, damage function, or SCC input.

A counts-only support audit applies the fixed 2017 selector to the locked
1981--2019 national panel without reading yield magnitudes. Across 10/20/30%
thresholds, retained reported county-years are 15,772/19,832/22,219 for corn
(20.80%/26.15%/29.30%) and 14,652/17,328/18,685 for soybean
(23.65%/27.97%/30.16%). At 10%, annual support ranges from 296 to 424 corn
counties and 283 to 391 soybean counties. This material, threshold-sensitive
attrition must be reported in any national validation and supplies no
irrigation effect, response, damage, or SCC estimate.
A key-only cross-crop audit further shows that the primary 10% selector leaves
9,715 common corn/soybean county-years across 264 counties, 66.30% of the
smaller selected crop panel. Annual common support ranges from 161 to 263
counties and the selected county-set Jaccard index is 0.475. Any joint crop
validation must use this intersection rather than either marginal crop count;
the audit reads no yield magnitude and estimates no response.
At the primary 10% threshold, an outcome-blind geographic audit retains 28 of
41 reported corn states and 28 of 31 reported soybean states; the five largest
retained states contribute 42.96% and 42.15% of selected county-years. National
validation must therefore keep state/region holdouts rather than treating a
large county-year count as geographically representative.

**Regional U.S. competing-moisture diagnostic.** The registered NASS/
nClimGrid/PDSI comparison retains 23,722 corn/soy crop--county--practice-year
levels and 20,228 consecutive-year log-yield changes on exact common support.
Models are separate by crop and irrigation practice and compare controls,
seasonal rainfall quantity, quantity plus eight distribution/extreme terms,
seasonal PDSI, and preplant/stage PDSI without stacking moisture families.
Eligible development holdouts are Colorado, Kansas, North Dakota, Nebraska,
and South Dakota for corn and Arkansas, Kansas, and Nebraska for soybean;
terminal tests use 2012--2019 observations from counties present in
development. All training/test level endpoints are disjoint.

The direct distribution extension fails the frozen uniform-state materiality
rule for irrigated corn (one of five states) and non-irrigated corn (four of
five; South Dakota reverses). For non-irrigated corn it nevertheless lowers
quantity-only RMSE by 0.060342 in the terminal test and 0.006075 in the
extreme test. Seasonal and stage PDSI are more stable competitors in this
stratum: both beat quantity-only in all five state holdouts, by mean state-fold
RMSE differences of 0.015309 and 0.018826, and also improve terminal RMSE by
0.049216 and 0.045035 and extreme RMSE by 0.032397 and 0.039544.

The distribution extension clears the development rule for both soybean
practice strata. For non-irrigated soybean it improves quantity-only RMSE in
all three state holdouts (mean 0.012279), the terminal test (0.058268), and the
extreme test (0.028115). For irrigated soybean, however, its 0.003862 mean
state-fold improvement reverses to a 0.012312 worsening in the terminal test;
it is therefore not characterized as temporally stable. PDSI comparisons are
smaller or geographically mixed outside non-irrigated corn.

A standalone implementation reconstructs the raw-level intersection and
first differences and solves the 120 fits by QR rather than the registered
least-squares path. Maximum disagreement is `4.44e-16` for RMSE and
`2.00e-15` across any reported numeric field; all split,
purge, rank, and promotion fields agree exactly. The regional outcome support,
fixed historical calendars, limited state folds, point-loss comparisons, and
shrinking direct-practice reporting support prohibit causal, nationally
representative, damage, or SCC interpretation. Support falls to 63 corn and
25 soybean counties in 2018 and 3/1 in 2019; no missing outcome is filled.
County-cluster paired-loss intervals, a 2019-endpoint exclusion, and balanced-
support windows remain separate sensitivities and are not silently inferred
from these point rankings.

As a preliminary coefficient-bearing bridge, we fit historical county and
state-by-year fixed-effects associations through 2018, with county-clustered
standard errors and quadratic stage-mean temperature controls. Model form was
frozen from the predictive screen: quantity only for corn and quantity plus
early/middle precipitation shares for soybean. In 7,013 non-irrigated corn
county-years, an additional 100 mm is associated with fitted yield differences
of 11.07%, 7.72%, and 3.59% at the 25th, 50th, and 75th percentiles of seasonal
rainfall; corresponding irrigated-corn differences are 0.04%, -0.41%, and
-0.98%. In 4,844 non-irrigated soybean county-years, the analogous values are
7.44%, 4.46%, and 1.11%. A partial 10-percentage-point middle-for-late-season
rainfall shift is associated with 4.73% for non-irrigated soybean and -0.21%
for irrigated soybean. Corn timing coefficients remain secondary because the
timing extension failed its prior geographic-stability gate. These estimates
are selected-sample historical associations, not causal or nationally
representative effects; they do not identify adaptation, CO2 fertilization,
irrigation water, climate-induced precipitation change, damages, or SCC.
A clean-room fixed-effect projection and QR/cluster-sandwich reimplementation
reproduces 324 reported numeric fields within `1.04e-13`. County-clustered
normal 95% intervals exclude zero for all three non-irrigated quantity
contrasts and for the non-irrigated soybean timing contrast; this sampling
uncertainty statement does not remove the design and transport limitations.

The separate all-practice national weather route remains a construction
diagnostic. It validates 932 of 2,628 county-weight receipts before failing
closed at Trigg County, Kentucky, whose weather-valid area is 0.907267979 of
declared land versus the fixed 0.95 gate. A hash-bound scan revalidates all
completed weight files: their minimum ratio is 0.960832366, only one is below
0.97, and 60 have positive masked area. Although Trigg is below every completed
receipt, the partial set spans 16 states and reflects FIPS-ordered execution
plus earlier bounded smokes. We therefore neither relax the threshold nor
exclude the county, and no partial national response is estimated.
An official 2019 TIGER/Line area-water follow-up exactly reconciles the
county's 102,999,105 m2 declared water across 2,123 hydrographic polygons.
Fractional polygon/grid intersection assigns 81,538,947 m2 of water and
127,512,062 m2 of land to the 16 masked cells; removing water from both valid
and masked areas lowers valid fractional-land coverage to 0.888503097. The
unchanged 0.95 gate therefore still fails, and no county exclusion, partition,
response, damage, or SCC result follows.
As an outcome-free sensitivity check, we also audited NOAA's own January 1981,
July 2000, and January 2019 nClimGrid-Daily county area averages. All three
sampled months have identical 3,107-county support. Official numeric code
15221 maps to Trigg FIPS 21221, and all sampled Trigg daily values are finite
and temperature-ordered; the July 2000 check independently validates Adair
County, Iowa, under the same rules. This establishes
a source-computed county-average alternative, not an estimator replacement:
historical boundary vintage and equivalence to the registered polygon-area
weights remain unvalidated.
An outcome-blind direct comparison retains Cuming County, Nebraska, and
Fresno County, California, in April 1990, July 2000, and drought-month July
2012. Temperature series agree at correlations above 0.99999 except for a
still-high 0.999993 minimum in April. Daily precipitation correlations are at
least 0.99983 except for Fresno's near-zero-rain July 2012 series (0.98533),
and the largest monthly precipitation-total difference is 0.9926 mm. This
supports close bounded agreement while explicitly rejecting general
equivalence. A recent-boundary January 2019 extension retains the same two
counties, 3,107-county source support, and 31 finite days; polygon-minus-
official monthly rain is +0.0441 mm in Cuming and +0.4057 mm in Fresno. These
nonzero differences continue to reject estimator equivalence or an estimator
replacement. A fixed December-2019 extension retains 31 finite days and exact
3,107-county support; polygon-minus-official monthly rain is -0.3216 mm in
Cuming and +0.3431 mm in Fresno. All eight county-variable correlations are
at least 0.999986, but the nonzero signed differences again prohibit an
equivalence claim or route replacement.

A fixed June-2019 growing-season comparison adds 30 days with the same source
support; polygon-minus-official monthly rain is +0.4135 mm in Cuming and
+0.0449 mm in Fresno. A checksum-bound synthesis of all seven selected months
requires 56 county-variable cells: 55 have nonzero maximum differences, while
the dry Fresno July-2000 rainfall pair is an exact constant match with
undefined correlation. The minimum defined correlation is 0.98533 and the
largest monthly rainfall-total difference is 0.9926 mm. This temporal evidence
continues to reject general estimator equivalence and route replacement.

The current-hash, basis-before-weighting diagnostic covers 117,679 observed
maize yields (102,847 consecutive pairs) and 47,922 observed soybean yields
(41,915 pairs) during 1982--1989. Temporal and extreme training sets are
yield-endpoint disjoint from their test sets. Every registered model improves
on zero-change RMSE in every crop/holdout. For maize, stage-joint RMSE is
0.2921 spatially and 0.2974 in high-tail stress pairs, compared with 0.2948 and
0.3024 for seasonal-joint; in the temporal block seasonal-joint (0.3070) and
stage-joint (0.3071) are essentially tied. For soybean, stage-joint is lowest
spatially (0.2185) and in high-tail stress pairs (0.2212), while seasonal-joint
is lowest temporally (0.2586 versus 0.2617 for stage-joint). Zero-change RMSEs
are 0.3082/0.3256/0.3144 for maize and 0.2322/0.2737/0.2332 for soybean in
spatial/temporal/extreme order. These are predictive diagnostics over eight
years, not causal effects. The stage model mixes crop-window amount, dry
spells, Rx1day, temperature, and interactions, so this result does not yet
identify an effect of temporal distribution conditional on seasonal amount.
It instead justifies the registered production comparison that separates
quantity from normalized timing, occurrence, intensity, and extremes.

That explicit quantity-versus-distribution comparison has now been run under
a separate hash-locked, coefficient-suppressing screening contract. Relative
to stage-temperature controls plus seasonal rainfall quantity, the best
distribution candidate reduces pooled held-out RMSE by 0.00117--0.00138 in the
three maize comparisons and by 0.00084--0.00261 in the three soybean
comparisons. The pattern is not uniform: the full distribution set worsens
soybean temporal RMSE by 0.00355, individual fold/year signs are heterogeneous,
and the pooled differences have neither paired uncertainty intervals nor a
multiple-comparison adjustment. The label used for the retrospective
high-tail stress split also covers about 47% of pairs in this eight-year panel
because a pair is included when either endpoint crosses either within-cell CDD
or Rx1day threshold; it is not rare-event or prospective validation. These
small predictive differences motivate continued testing of both rainfall
quantity and timing, but do not identify a causal precipitation effect or
select the production response.

The same hash-locked screen on 2012--2016 data does not reproduce a stable
distribution advantage. Among 46,434 maize pairs, every distribution extension
worsens spatial and temporal RMSE relative to seasonal quantity; timing and
concentration improve the high-tail score by only 0.000044. Among 20,682
soybean pairs, dry spells improve spatial RMSE by 0.001516 and
occurrence/intensity improve high-tail RMSE by 0.001366, but every extension
worsens temporal RMSE. The combined distribution set worsens temporal RMSE by
0.004826 for maize and 0.003491 for soybean. For maize's 2015--2016 temporal
block, even the seasonal-quantity and temperature models are worse than the
zero-change benchmark. No registered distribution family improves on seasonal
quantity in all three holdouts for either crop.

A separate three-model minimal-basis complete-positive-support sensitivity,
motivated by GDHY's temporary 2015 support drop, retains 91.23% of maize pairs
and 94.23% of soybean pairs.
Seasonal joint temperature--quantity is lowest-RMSE in every crop-by-holdout
comparison in that selected subset, although complete-support conditioning can
change the sample and the seven-family screen has not been rerun on the
subset. The later-period evidence therefore favors seasonal
quantity as the current parsimonious direct-weather reference and does not
clear the registered retention gate for any distribution extension. It does
not freeze a causal production model: PDSI/scPDSI, SPEI, and soil moisture
remain competing moisture-stress families under the same holdouts, and no
predictive ranking is an SCC result.

All earlier rainfed-panel response rankings were generated under a superseded,
endpoint-overlapping split and are excluded from current manuscript results.
Their source-panel coverage remains documented in `RESULTS_STATUS.md`; every
response comparison must be rerun under the current hash before it can be
reported.

At the integration boundary, the replacement installer now passes an executed
synthetic control on the unmodified GIVE model: the MooreAg agriculture
component is removed, existing regional socioeconomic aggregators are reused,
the new `agcost` is connected once, and the declared nonagricultural sector
flags are preserved. The test uses synthetic normalized crop shares and zero response
arrays on GIVE's complete model time axis. All active-year crop and regional
response outputs are complete, coverage is one, and both the component and
GIVE-aggregated agriculture damage paths remain zero. It therefore establishes
execution/connectivity only and supplies no empirical response, paired marginal
damage, or SCC evidence.

Future-climate feature support is no longer evaluated on maize alone. A
checksum-bound UKESM midcentury diagnostic adds first- and second-season rice,
soybean, spring wheat, and winter wheat rainfed calendars plus a soybean
irrigated calendar. Every cell passes finite/bounded rainfall, wet-day,
dry-spell, Rx1day/Rx5day, complete-year, and exact seasonal/stage reconciliation
checks. SSP5-8.5-minus-SSP1-2.6 mean rainfall ranges from -38.27 to +19.05 mm
and maximum-dry-spell changes range from +0.46 to +9.56 days across rainfed
crops. The soybean irrigation comparison is a calendar-exposure sensitivity,
not an irrigation treatment effect. Because this remains one ESM, one period,
two latitude rows, and no yield response, it cannot promote the adverse
aggregate emulator or enter damages or SCC calculations.

The preregistered pathway-aware ridge candidate also fails promotion. It
improves 71 of 88 nested whole-ESM/whole-scenario feature comparisons and its
median RMSE ratio to the cell-mean benchmark is 0.99443, but the maximum ratio
is 1.00703 and 85 predictions violate nonnegative feature bounds. The locked
maximum, every-feature, and physical-bounds criteria therefore fail. We do not
propagate this candidate through the actual FAIR pulse paths or into crop
responses, damages, or SCC calculations.

The outcome-blind physical-link successor likewise fails. Positive log and
bounded-logit links plus a joint centered-log-ratio stage composition remove
all negative and above-one predictions and preserve stage sums to `3.33e-16`,
but only 34 of 88 original-scale comparisons beat the cell-mean benchmark.
Median and maximum RMSE ratios are 1.00775 and 1.13855; none of the stage-share
or precipitation-concentration-HHI comparisons improves. We therefore withhold
the actual FAIR pulse evaluation and all downstream response, damage, and SCC
use.
On exact holdout keys, the physical-link candidate improves on the rejected
identity-link form in only 9/88 comparisons, rescues none of its benchmark
failures, and loses 37 of its benchmark successes. Thus enforcing feature
domains does not resolve the structural predictive failure.

The literature-constrained next benchmark is RIME-X v1.0, which derives
warming-level conditional quantile maps for climate or impact indicators and
interpolates them onto simple-climate-model temperature paths. We pin the
published article and exact software archive and validate only independent
synthetic interpolation mechanics. A real crop-feature fit is not attempted:
the bounded ISIMIP3b artifact has discontinuous short blocks rather than the
published 21-year smoothing support, and univariate quantile maps do not
preserve the joint dependence among rainfall quantity, timing, dry spells,
extremes, heat, and drought. Whole-ESM, whole-scenario, actual FAIR, damage,
and SCC gates remain closed.

We additionally retain the USEPA pattern-scaled climate-variable workflow as
an external annual-total benchmark. That implementation applies precomputed
PEEPS annual precipitation--GMST slopes and aggregates them to GIVE countries
using area, GDP, or population weights. It does not construct daily or
crop-stage precipitation distributions or agricultural damages. We therefore
compare the annual spatial response and a preregistered FAIR--GCM rank-pairing
sensitivity, while retaining daily crop-calendar features, crop-area/value
weights, and joint agriculture replacement as the primary analysis. Annual
pattern scaling and country aggregation are not novelty claims of this paper.

As a separate climate-method benchmark following the published PEEPS
monthly pattern-scaling construction (Kravitz and Snyder, 2023,
doi:10.1371/journal.pclm.0000159), we fit GFDL-ESM4 and IPSL-CM6A-LR
raw-CMIP6 monthly precipitation to their own native-area-weighted annual
GMST on SSP5-8.5 2015--2080. Whole-SSP1-2.6 2031--2060 and late
SSP5-8.5 2081--2100 are frozen holdouts. In both whole-scenario tests,
the monthly-pattern specification reduces native-global-grid monthly
amount RMSE by less than 1% relative to a same-information annual-
quantity-only fit (GFDL 57.555 to 56.992; IPSL 59.703 to 59.155
mm/month), and improves month-share total-variation distance modestly.
However, it predicts negative rainfall in 2,621 and 7,805 grid-cell
months, respectively. The later-time tests have severe GMT-support
extrapolation and many more negative predictions. These are
all-atmosphere-grid climate scores, not cropland, yield or SCC results;
the linear monthly fit therefore remains a benchmark and is not used
as GIVE forcing. Exact sources, physical-failure counts and an
independent 108-score arithmetic audit are reported in
`PUBLISHED_MONTHLY_GMT_RESPONSE_HOLDOUT_RESULTS_20260917.md`.
On fixed rainfed-maize calendars, the same held-out SSP1-2.6
2031--2060 **monthly-climatology** benchmark gives a more crop-relevant
comparison. For the 28,328 supported crop cells, the monthly pattern
reduces area-weighted crop-season rainfall RMSE relative to the
quantity-only fit from 48.211 to 45.929 mm in GFDL and from 36.986
to 28.556 mm in IPSL under the source-calendar convention; the
harvest-year convention gives the same direction. Month-share
distance and rainfall-centroid errors also decline. These are
climate-input scores, not yield effects: there are still 9 and 68
negative predicted crop-cell months, and the comparison has no
year-level or daily variability. The fit remains unpromoted.
`PUBLISHED_MONTHLY_GMT_RESPONSE_MAIZE_RESULTS_20260917.md` provides
the common support, independent ledger audit and all four scores.

We also test the **published author PEEPS coefficients**, distinct from
those project-fitted benchmarks, against their own two-member MPI-ESM1-2-HR
SSP5-8.5 precipitation source. On rainfed-maize nearest-center support,
raw published levels imply a negative month on 2.856% of area in 2015
and 9.879% in 2100. Annual-total RMSE against direct source rainfall
is 131.843/147.021 mm, and mean monthly-share total-variation error
is 0.126917/0.142917 on physically valid within-year support. An
independent audit reproduces 214 reported scalar metrics; a fixed-area
post-result comparison gives +34.172 mm direct versus +43.612 mm
published-pattern annual rainfall change from 2015 to 2100. Because
this is a **same-source, in-sample** diagnostic with physically invalid
predictions, it neither validates a future scenario response nor enters
the agricultural damage or SCC calculation. Full provenance and scope:
`PEEPS_MPI_SSP585_RECONSTRUCTION_RESULTS_20260918.md`.
An all-area post-result change decomposition further separates annual
amount from within-year monthly redistribution. For 2015--2100, direct
versus published area-weighted annual changes are +43.452 versus
+47.329 mm, yet spatial annual-change RMSE is 157.710 mm. The
within-year redistribution component accounts for 44.937 mm of the
46.820 mm overall monthly-change RMSE, compared with 13.143 mm per
month from annual-amount error. This same-source comparison preserves
invalid negative raw levels and cannot be used as rainfall forcing;
see `PEEPS_MPI_CHANGE_DECOMPOSITION_RESULTS_20260918.md`.
A separate, predeclared direct-2015-baseline plus published-monthly-anomaly
test also fails physicality: the 2100 estimate has at least one negative
month on 33.962% of mapped crop area, despite lower annual and monthly
RMSE than a no-change comparator in this same-source test. The failed
route is not used for GIVE rainfall forcing; see
`PEEPS_MPI_BASELINE_ANOMALY_RESULTS_20260918.md`.
Twenty-year source-matched monthly climatologies substantially reduce
single-year noise but do not remove the forcing boundary. Between
2015--2034 and 2081--2100, the mapped-area direct versus published
annual-rainfall changes are +36.933 versus +38.798 mm, with 21.731 mm
spatial annual-change RMSE. The within-year monthly redistribution
component of change error is 5.060 mm per month versus 1.811 mm from
annual amount error. The late published monthly climatology is still
negative in at least one month on 6.131% of mapped area. Even this
favorable same-source, twenty-year smoothing therefore leaves the raw
published pattern unsuitable for GIVE forcing; see
`PEEPS_MPI_20YR_CLIMATOLOGY_RESULTS_20260918.md`.
On the separate, physically valid direct-daily ISIMIP route, fixed
year-2000 rainfed-maize area weights reframe three-ESM late-window
scenario weather. Under SSP5-8.5 minus SSP1-2.6 in 2092--2099,
growing-season rainfall changes are +20.124/+5.737/−6.940 mm in
UKESM/IPSL/MPI, but wet days decline and longest dry spells and Rx5day
increase in all three. This supports retaining both amount and
within-season distribution/extremes as distinct climate *inputs*;
it does not show an independent crop-yield penalty from the latter.
The same 30,654 cells cover 99.9559% of mapped rainfed-maize area in
all 72 panels, and an independent ledger/source-sample audit passes.
The eight-year scenario contrasts are not fitted forced per-K changes,
crop damages or SCC; see
`GLOBAL_THREE_ESM_MAIZE_AREA_WEATHER_RESULTS_20260918.md`.
Published alternatives therefore matter: MESMER-M-TP supplies a
temperature-conditioned positive monthly-precipitation framework,
whereas the 2026 MESMER-X Rx1day extension emulates annual maxima of
one-day rain. These provide monthly and tail benchmarks, respectively,
but neither supplies a ready-made joint daily sequence of crop-season
rainfall, dry spells and temperature for this GIVE replacement. The
specific applicability and available-code gates are recorded in
`PUBLISHED_POSITIVE_AND_EXTREME_RAIN_EMULATOR_REVIEW_20260918.md`.

Before acquiring any additional daily fields, we froze a one-ESM/one-scenario
contiguous-support pilot. GFDL-ESM4 SSP1-2.6 precipitation and temperature for
2031--2060 provide crop-feature years 2032--2059 and eight centered 21-year
outputs for 2042--2049. All six files pass exact catalogue byte/SHA-512 and
full decoded-content gates. The bounded maize/rainfed build has 19,208 season
and 57,624 stage rows with exact unsmoothed reconciliation; its eight centered
windows preserve additive stage/season precipitation and wet-day identities
to numerical precision. This is a mechanics gate only; it cannot authorize a
response or substitute for whole-ESM, whole-scenario, multi-crop,
rainfed/irrigated, dependence, and FAIR pulse validation.
An independent global source extension now verifies the same GFDL
SSP1-2.6 maize/rainfed crop-year features for all 67,420 registered
calendar cells and every 2032--2059 harvest year: 1,887,760 season
and 5,663,280 stage records. All 12 newly built annual panels pass
source-receipt, calendar-key, physical-bound, stage-reconciliation,
and 252 selected raw-daily reconstruction checks. The first
cross-year audit failed only because an empty tile produced an
object-typed empty array; the retained failure receipt and the
reviewed empty-tile correction precede the passing second audit.
The centered 21-year latitude-100--110 parity pilot subsequently
matches all 5,488 prior two-row season and 16,464 stage records
after an explicit fixed-calendar-geometry schema mapping. A
two-latitude-row streaming implementation keeps this pilot's peak
sampled RSS at 223 MB, and the largest 5,630-cell tile passes at
273 MB. All 36 centered tiles subsequently pass an independent
global audit: eight 2042--2049 centers contain 539,360 season
and 1,618,080 stage records, with 168 independent 21-year
annual-feature reconstructions and a 413 MB sampled audit peak.
These achievements establish climate input
support and reproducible feature arithmetic, not a fitted
GMT-to-rainfall response, yield effect, monetary damage, or SCC.
Before examining a real joint fit, we preregister ECC-Q empirical-copula
coupling. Complete ESM--member--scenario--center-year fields provide the rank
templates; separately calibrated marginal quantiles are reordered on physical
coordinates for seasonal quantity, wet frequency, dry-spell fraction,
Rx5/total, Rx1/Rx5, temperature, and stage-rain composition. Baseline and pulse
reuse the same template identities. Synthetic tests reproduce marginal
multisets and the template Spearman matrix exactly with no physical failures.
The pilot has eight templates, below the preregistered minimum of 51, and thus
cannot establish real joint dependence.
The same contiguous realization is then expanded, under a contract frozen
before feature construction, to all 12 combinations of six crops and rainfed
or fully irrigated calendars. Exact annual, physical, additive-reconciliation,
and common-GMST gates pass for 214,928 seasonal and 644,784 stage rows and for
61,408 seasonal and 184,224 stage rows after centering. Paired-calendar
seasonal-rain differences range from -23.33 to +14.60 mm across crops; both
rice pairs are identical on this bounded support. These contrasts isolate
calendar-date sensitivity on one climate realization, not applied-irrigation
effects, and do not expand ESM/scenario or response support.
The preregistered SSP3-7.0 and SSP5-8.5 replications on the same GFDL member
also pass complete 2031--2060 content, feature, reconciliation, and 12-cell
calendar gates. Together they contribute 16 additional centered years, for 24
templates across the three completed GFDL scenarios. In SSP5-8.5, centered
`firr` minus `noirr` seasonal-rain differences range from -22.21 to +13.80 mm
across crops and the two rice pairs remain identical. These are calendar-date
sensitivities, not irrigation effects. The matrix is still below the
51-template joint-dependence minimum and provides neither a whole-ESM holdout
nor evidence for a crop response, damage function, or SCC calculation.
The first cross-ESM contiguous replication uses IPSL-CM6A-LR `r1i1p1f1`
SSP1-2.6. Its six version-pinned daily files, 30-year same-realization GMST,
and all 12 crop-by-calendar cells pass the same content, chronology,
reconciliation, and deterministic-audit gates. It adds eight centered-year
templates; `firr` minus `noirr` centered seasonal-rain differences range from
-23.71 to +12.66 mm across crops, with identical rice pairs. The four completed
ESM-scenario cells provide 32 templates and are unbalanced across ESMs, so
whole-ESM/scenario validation, response, damage, and SCC gates remain closed.
The matched IPSL-CM6A-LR SSP3-7.0 replication also passes all six daily-file,
same-realization GMST, 12-cell feature, reconciliation, and deterministic-audit
gates. It contributes eight additional centered-year templates. Across crops,
the `firr` minus `noirr` centered seasonal-rain difference ranges from -25.10
to +12.80 mm, with identical rice pairs. The five completed ESM-scenario cells
provide 40 templates. The matched SSP5-8.5 cell subsequently passes the same
gates and row counts, including a byte-identical aggregate-audit rerun; its
calendar-only seasonal-rain differences range from -25.94 to +12.50 mm and
both rice pairs remain identical. The six completed ESM-scenario cells provide
48 templates. Its exact-key 2032--2059 comparison with IPSL SSP1-2.6 yields
cell-mean warming of 0.580--0.836 C and seasonal-rain changes of -5.07 to
+12.62 mm; these are descriptive climate-feature changes, not yield effects.
The matrix remains below the 51-template dependence threshold, and an
ESM holdout leaves only 24 training templates while a scenario holdout leaves
32. Joint-dependence, whole-ESM/scenario response, damage, and SCC gates remain
closed.
The preregistered MPI-ESM1-2-HR `r1i1p1f1` SSP1-2.6 replication next passes
all six checksum/content gates, a 30-year same-realization GMST build, and the
same deterministic 12-cell feature and reconciliation audit. It adds 214,928
seasonal and 644,784 stage rows before centering and 61,408 seasonal and
184,224 stage rows after centering. Calendar-only `firr` minus `noirr`
seasonal-rain differences range from -22.48 to +14.72 mm; both rice pairs are
identical. Although the resulting 56 templates exceed the unconditional
51-template minimum, the partial matrix cannot support the preregistered
holdouts: excluding MPI retains 48 templates, excluding either complete ESM
retains 32, and excluding SSP1-2.6 retains 32. No joint dependence, crop
response, damage, or SCC result is estimated from this unbalanced support.
The matched preregistered MPI SSP3-7.0 cell also passes six-file content,
same-realization GMST, all-crop/calendar, reconciliation, and byte-identical
audit gates with the same row counts. Its calendar-only `firr` minus `noirr`
centered seasonal-rain differences span -21.76 to +11.22 mm, and both rice
pairs are identical. The resulting 64 templates still leave only 40--48 after
any whole-ESM or whole-scenario exclusion, below the locked 51-template
minimum. Joint dependence, holdout promotion, response, damage, and SCC use
remain closed.
The preregistered MPI SSP5-8.5 replication passes the same six-file content,
30-year same-realization GMST, all-crop/calendar, exact-reconciliation, and
byte-identical audit gates, adding the same raw and centered row counts.
Calendar-only `firr` minus `noirr` centered seasonal-rain differences range
from -23.99 to +12.62 mm; both rice pairs are identical. The resulting 72
templates leave 48 after every whole-ESM or whole-scenario exclusion, still
below the locked 51-template minimum. No joint dependence, response, damage,
or SCC result is estimated from this incomplete matrix.
The MRI-ESM2-0 `r1i1p1f1` SSP1-2.6 replication then passes the same six-file
content, 30-year same-realization GMST, all-crop/calendar,
exact-reconciliation, and byte-identical audit gates. It adds the same raw and
centered row counts; calendar-only `firr` minus `noirr` centered seasonal-rain
differences range from -28.16 to +13.80 mm, with identical rice pairs. The 80
templates leave 56--72 after whole-ESM exclusions and 56 after SSP3-7.0 or
SSP5-8.5 exclusion, but only 48 after SSP1-2.6 exclusion. The preregistered
balanced matrix remains incomplete, so no joint dependence, response, damage,
or SCC result is estimated.
The MRI-ESM2-0 `r1i1p1f1` SSP3-7.0 replication also passes the frozen six-file
checksum/content, 30-year same-realization GMST, all-crop/calendar,
exact-reconciliation, and byte-identical audit gates. It adds 214,928 seasonal,
644,784 stage, 61,408 centered-seasonal, and 184,224 centered-stage rows.
Calendar-only `firr` minus `noirr` centered seasonal-rain differences range
from -22.93 to +13.08 mm, with identical rice pairs; these are not irrigation
treatment effects. The resulting 88 templates leave 64--72 after excluding a
represented ESM and 56--64 after excluding a scenario, placing every currently
represented exclusion above the locked 51-template minimum. However,
UKESM1-0-LL has no contiguous feature templates and the preregistered balanced
five-ESM matrix remains incomplete. No joint dependence, response, damage, or
SCC result is estimated from the incomplete matrix.
Before inspecting dependence results, we fixed a storage-bounded diagnostic of
within-template Spearman stability over the eight linked physical coordinates
and committed its implementation. It uses all 88 available centered-year
templates and excludes each represented ESM or scenario in turn. Six of seven
exclusions pass the fixed mean, maximum, and strong-pair sign gates. The
MRI-ESM2-0 exclusion fails: the median wet-frequency--Rx1-given-Rx5 correlation
differs from training by 0.192318, above the registered 0.15 maximum. All three
scenario exclusions and the other three ESM exclusions pass, and no strong
pair reverses sign. This result is retained without retuning. It is a
structural diagnostic rather than an empirical-copula or marginal response
fit, and it leaves joint dependence, FAIR feature response, crop response,
damage, and SCC use closed.
A follow-up diagnostic was also committed before its outputs were read. It
retained the failed wet-frequency--Rx1-given-Rx5 pair and the 0.15 gate, then
matched the other ESMs to MRI's available SSP1-2.6 and SSP3-7.0 support. The
absolute difference falls only from 0.192318 to 0.173654. Scenario-specific
differences are 0.163224 and 0.204990, all eight center-year differences exceed
0.15, and ten of twelve crop/regime differences exceed 0.15. Only the two
winter-wheat calendar cells are below the gate. Thus scenario imbalance is not
sufficient to explain the MRI result, while crop heterogeneity remains
material. The decomposition is descriptive and does not fit or authorize a
dependence model or any downstream response.
A no-fit decision audit was registered next and reads only those three
checksum-bound receipts. Pooling the 88 available templates clears the count
threshold but fails the complete five-ESM/three-scenario requirement and the
unresolved MRI stability gate. Conditioning on ESM does not solve the design:
three scenarios by eight center years supply only 24 templates per complete
ESM, 27 fewer than the locked minimum of 51. Thus neither pooled nor
ESM-conditional dependence is authorized; additional templates would require
a separate preregistration that does not assume overlapping centered windows
are independent.
An initial receipt-only temporal count is withdrawn because it incorrectly
treated the legacy annual one-crop/regime holdout rows as centered 21-year
linked multicrop/regime dependence templates. The corrected audit was
separately preregistered and applies compatibility before counting. The 88
nominal RIME-X templates comprise eight overlapping center years in each of 11
completed ESM--scenario cells, leaving at most 11 pairwise-nonoverlapping
templates. Even a complete 15-cell matrix raises this upper bound only to 15,
36 below the fixed minimum of 51; complete-design whole-ESM and whole-scenario
holdouts retain at most 12 and 10. The 2,376,990 legacy early/mid/end rows
contribute zero compatible templates. Pairwise nonoverlap is not treated as
proof of independence, and no dependence, FAIR, response, damage, or SCC gate
is opened.
A separately preregistered metadata-only feasibility audit then solves the
count constraint without fitting. Seven ESM-member tracks across three SSPs
and four pairwise-nonoverlapping 21-year windows yield 84 compatible
templates. Whole-member, worst-case whole-ESM-family under a two-member family
cap, and whole-scenario holdouts retain 72, 60, and 56 templates, respectively;
six member tracks retain only 48 after the limiting family or scenario
holdout. This is structural arithmetic, not a selected ensemble: candidate
members, catalogue availability, storage volume, member independence, and
holdout performance remain unverified, and no acquisition or downstream gate
opens.
The preregistered official-catalogue screen then queried the complete three-SSP
by daily-`pr`/`tas` matrix without filtering climate forcing or member. It finds
only five complete ESM-member tracks spanning the four nonoverlapping 21-year
windows, below the locked minimum of seven. Their 30 datasets contain 270
public, unrestricted CC0 version-`20210512` source files totaling
536,861,000,440 catalogue bytes. The track-count gate therefore fails before
storage or model fitting. No ensemble was selected and no climate payload was
downloaded; member independence, adverse MRI stability, FAIR, response,
damage, and SCC gates remain closed.
The next metadata-only contract pins the 90 official daily files required to
replicate this contiguous design across five ESMs and three scenarios. If all
187.139 GB pass content and feature validation, the matrix contains 120
complete centered templates; whole-ESM and whole-scenario exclusions retain 96
and 80 nominal training templates, respectively. The corrected distinctness
audit does not treat the overlapping centers as independent support. No
additional matrix content or
holdout performance is claimed here.

The U.S. measurement validation also expands spatially. A sample fixed before
output compares official NOAA county averages with the registered polygon
proxy for June 2019 in nine counties across nine states. All 36 county-variable
cells retain complete daily support; minimum correlation is 0.999812, while
polygon-minus-official monthly rainfall-total differences range from -0.8305
to +0.4135 mm. These nonzero differences reinforce that the estimators are
close but not interchangeable and do not estimate a yield response.
Holding those nine counties fixed, a preregistered January/June/December 2019
expansion retains complete support in all 108 county-variable-month cells.
Every cell has a nonzero maximum difference; minimum defined correlation is
0.999758 and monthly rainfall differences range from -0.8305 to +0.6192 mm.
This remains outcome-free measurement validation and does not identify a yield
response or replace the registered polygon estimator.
A further preregistered April/September shoulder-month expansion raises the
same fixed sample to 180 complete cells. Minimum defined correlation is
0.999425, while polygon-minus-official monthly precipitation differences range
from -2.7068 to +1.2868 mm. The expanded evidence continues to reject exact
interchangeability without reading yield outcomes or changing the registered
polygon route.
For the national fixed-2017 10% selector, a key-only audit of the corn/soy
intersection finds 9,715 county-years in 264 counties and 22 states. Median
coverage and the median longest consecutive run are 38 of 39 years, and 105
counties in 17 states are complete. The minimum is eight years. These counts do
not favor complete-case restriction; later joint validation must declare its
missingness and clustering treatment without using outcome magnitudes to choose
the sample.

The retained published-method climate fallback is not yet executable as a
production chain. A preregistered metadata-only audit confirms archived public
implementations for the MESMER-M-TP monthly backbone, MESMER-X Rx1day, and the
STITCHES sequence benchmark, but finds no pinned public software for the fixed
Kemsley Markov--gamma daily generator. Only the monthly-backbone requirement is
established end to end; monthly-to-daily conservation, joint daily temperature
and precipitation, spatial dependence, Rx5day, crop-stage fidelity, whole-model
and whole-scenario holdouts, and matched-pulse convergence remain unresolved.
We therefore retain this chain as a validation plan without substituting a new
generator or promoting any climate, response, damage, or SCC result.
The subsequently identified DiffESM daily benchmark does not amend that
registered chain: the published version generates rain or temperature
separately in 28-day blocks, without demonstrated continuity across blocks or
the joint daily heat--rain response needed for crop windows. Its reported
within-block rain-streak fidelity is not crop-year validation.

We preregistered the numerical interface for a possible future implementation.
It requires keyed occurrence, wet-amount, and spatial innovations shared by
baseline and all pulse sizes, with path role, pulse size, monthly climate, and
path-specific parameters excluded from the random key. Each path must conserve
its own monthly precipitation total through a nonnegative,
occurrence-preserving rescaling, and zero-pulse and pre-divergence daily paths
must be identical. The interface also preserves separate support flags and the
existing direct-daily, whole-model, whole-scenario, crop-stage, and
shrinking-pulse gates. No daily sequence was generated and the absent pinned
Kemsley implementation remains a hard no-fit blocker.

We subsequently froze and implemented only the future output schema and its
fail-closed validator. The schema binds exact receipt, monthly-record, and
daily-record fields; canonical record hashing; unique pair keys; complete
calendar days; shared innovation digests; separate pathwise mass conservation;
one zero and at least three positive pulse scales; and exact zero-pulse and
pre-divergence daily identity. A second canonical hash now binds monthly
identities, path targets, parameter-bundle identity, and support flags while
excluding record order, innovation digests, and daily values. A 32-record tiny
fixture covers leap Gregorian, noleap, 360-day, and all-zero months with zero
mass error; fourteen targeted corruptions fail. This validates the proposed
data boundary and numerical identities, not a generator or climate response;
no real daily values or downstream estimates were produced.

We then preregistered and implemented only a canonical boundary for the
parameter identity referenced by that schema. One parameter record is required
for every exact monthly output key and names the dry-to-wet and wet-to-wet
transition probabilities, gamma shape and scale for wet-day amounts, spatial-
dependence and temperature--precipitation component hashes, and support flag.
The full object is hashed after sorting by the monthly key; the receipt and all
monthly output records must carry that hash, with exact key, support, and code-
identity agreement. Synthetic fixtures reject ten corruptions and link the 32
calendar test records one-to-one. No real parameter estimation, generator
implementation, or downstream climate or damage calculation is implied.

### 6.3 Marginal damages and global SCC

The evidence-led selection gate does not promote any empirical global response
family. Maize seasonal quantity modestly improves country-held-out point RMSE,
but its paired intervals against heat controls and zero change include no
improvement. Soybean has only four valid country folds, lacks a supported
bootstrap, and zero change has lower pooled RMSE. Adding distribution worsens
point RMSE relative to quantity for both crops; scPDSI is unstable across
weightings or worse. We therefore retain quantity plus temperature only as a
research benchmark and distribution/drought as reported sensitivities. No
empirical agricultural damage or SCC result is authorized at this stage.

U.S. NASS validation nevertheless shows a coherent mechanism priority. Over
county-specific common rainfall ranges, lower rain is associated with lower
non-irrigated corn and soybean yields under both nClimGrid and GSWP, while both
reported-irrigated intervals include zero. Distribution and seasonal PDSI both
improve pooled non-irrigated prediction beyond quantity. PDSI is especially
stable for non-irrigated corn, winning in all five baseline states and the
terminal test, but South Dakota reverses after richer Tmax controls.
Distribution fails the uniform-state rule for corn and loses soybean's formal
selection under richer Tmax controls. These results prioritize further U.S.
drought validation; they do not authorize global coefficient transfer.
In a separate post-result 2020--2025 all-practice terminal comparison, direct
rain patterns have the lowest corn and soybean RMSE under common and state-
specific trends, while PDSI mean is worse. Because the outcome-practice and
validation designs differ, this qualifies rather than overturns the direct-
practice evidence and reinforces a competing-model interpretation.

Before transporting an historical response, we compared 35 years
(1982--2016) of same-cell crop weather with 72 direct-daily end-century
panels on a fixed 108.04-million-ha rainfed-maize footprint. Depending on
ESM and SSP, 7.6--19.5% of crop area in an average 2092--2099 year is outside
its cell-specific historical minimum/maximum for seasonal rainfall, and
18.3--33.5% is outside for wet-day frequency. Mean temperature is outside
the same range on 37.0--100% of area. Stage-rainfall and precipitation-extreme
features also show nontrivial extrapolation. These weather-only results do not
measure yield loss or forced change because the historical and future climate
source families differ. They instead reject an unrestricted historical-range
transport assumption and require explicit out-of-support sensitivity before
agricultural damages can enter GIVE.

As a descriptive climate-link benchmark, we normalized each ESM's terminal
SSP3-7.0 and SSP5-8.5 crop-weather contrast against SSP1-2.6 by the matching
realization's 2092--2099 GMST contrast. The six seasonal-rain ratios span
-9.41 to +4.66 mm K-1, whereas every ratio has fewer wet days, longer maximum
dry spells, and larger one- and five-day rainfall maxima. These endpoint ratios
are not fitted emulators or marginal CO2 responses: they use one realization
per ESM, eight terminal years, and scenario differences containing multiple
forcings and internal variability. They support retaining distributional
weather diagnostics while rejecting a universal-sign annual-rain response.

The EPA/FAIR calculation separately demonstrates that a published
country-level annual-rainfall pattern can be evaluated on GIVE's actual
marginal temperature path. It therefore supplies the practical annual-quantity
benchmark requested for analogy with the wildfire climate link. It is not
combined with U.S. yield coefficients or process-crop-model responses here:
doing so would silently transfer a country-annual climate exposure into a
county/crop-season response and would omit the timing, extreme, drought,
temperature, CO2, irrigation, and adaptation channels under study.

Report global agricultural marginal damages and SCC under each adaptation
scenario with draw-level uncertainty. Do not present a precipitation add-on to
baseline MooreAg agriculture.

### 6.4 Sensitivity and accounting checks

Report sensitivity to calendars, weather products, feature definitions,
response form, CO2 treatment, adaptation, regional aggregation, discounting,
and the method for decomposing joint effects.

## 7. Discussion

Interpret results only within historical support and the scenario ensemble.
Distinguish empirical weather responses from long-run adaptation assumptions,
and structural crop-model uncertainty from statistical uncertainty. A future
noncoastal infrastructure module must exclude crop and CIAM-covered coastal
losses before it is combined with SCC results.

## Planned exhibits

| Exhibit | Content |
|---|---|
| Figure 1 | Climate-to-crop-to-welfare-to-SCC architecture and exclusion boundaries |
| Figure 2 | Crop-calendar feature maps and baseline coverage |
| Figure 3 | Held-out response performance and process-model benchmark |
| Figure 4 | Global agricultural SCC distributions by adaptation scenario |
| Figure 5 | Uncertainty/decomposition and sensitivity results |
| Table 1 | Data sources, versions, licenses, coverage, and roles |
| Table 2 | Main response specification and validation gates |
| Table 3 | SCC results and scenario definitions (after estimation) |
