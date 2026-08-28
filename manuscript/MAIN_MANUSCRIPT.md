# Precipitation patterns, global agricultural damages, and the social cost of carbon

## Abstract

Climate change alters not only mean precipitation but also the timing,
seasonality, dry spells, and heavy-rainfall exposures that govern crop water
stress and excess-water damage. Existing GIVE agriculture in this checkout is
a temperature-indexed welfare response with no explicit separable
precipitation input, so it cannot identify a marginal precipitation
contribution. This project develops a replacement pathway:
daily, crop-calendar-aligned climate features will be linked to gridded crop
outcomes in a joint temperature--water response; the fitted response will be
evaluated under matched baseline and CO2-pulse climate paths, translated
through one agricultural welfare layer, and passed to GIVE's SCC calculation.
The empirical hierarchy begins with joint temperature plus crop-calendar
seasonal rainfall quantity, retains distribution terms only for robust
incremental out-of-sample value, and treats PDSI/scPDSI and SPEI as serious
competing moisture-stress representations rather than additive controls.
The current 2012--2016 maize and soybean screens do not identify any
distribution family that improves on seasonal quantity in every registered
holdout, so seasonal quantity remains the parsimonious direct-weather
reference. That ranking is predictive screening evidence, not a causal
response estimate. The matched direct-weather--scPDSI predictive diagnostic is
now validated on 209,036 global-gridded maize and soybean consecutive-year
pairs. Seasonal quantity has the lowest mean spatial-fold RMSE for both crops,
although its improvement over controls is below 1% and its MAE ranking is less
uniform; richer scPDSI summaries add stress-specific rather than stable general
predictive value. Paired geographic loss intervals include zero for every
scPDSI-versus-direct comparison. This is a historical prediction result, not a
causal response, full-global-agriculture result, climate-change projection, or
SCC input. A separate U.S. regional screen validates 20,228 common corn/soy
practice-specific changes. For non-irrigated corn, seasonal and stage PDSI
outpredict rainfall quantity in every eligible state and in terminal/extreme
tests; the direct distribution extension improves four of five states but
fails its frozen uniform-state rule. For non-irrigated soybean, the
distribution extension improves all three eligible states plus the terminal
and extreme tests. Irrigated rankings are less stable. A clean-room QR audit
reproduces all 120 aggregate metrics. These U.S. results are historical
prediction evidence, not causal effects or SCC inputs. Primary SPEI
construction is source-locked but has not yet been executed.
We pre-specify fixed,
trend, and upper adaptation scenarios and retain climate, response, calendar,
and welfare uncertainty. The manuscript reports no SCC estimates until the
validated feature panel and response draws are available. Its central outcome
will be a global SCC decomposition that does not stack precipitation damages
on top of the existing temperature-indexed agriculture component.

Analysis completion and permitted claim status are maintained in
`RESULTS_STATUS.md`; the manuscript must not advance beyond that ledger.

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

This is not the first climate or crop emulator. MESMER-M-TP and related
systems emulate spatial precipitation under warming; stochastic weather
generators translate monthly conditions into daily sequences; and OSCAR-crop
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
objects for 1981--2019 are now local: the bounded acquisition utility checked
the frozen HTTP identity, local SHA-512, NetCDF schema, and exact daily calendar
for each of the 27,857,685,556 compressed bytes. Registered aggregation over
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

The next registered IPSL-CM6A-LR SSP1-2.6 2041--2050 `pr`/`tas` pair also
passes exact byte, SHA-512, decoded-content, same-realization GMST, and bounded
feature/reconciliation gates. Its paired daily files use a fixed 12:00
timestamp rather than GFDL's 00:00; both variables share the exact 3,652-day
sequence. This first IPSL block does not yet form another scenario or ESM
holdout product.

## 6. Results (pre-registered placeholders)

### 6.1 Climate-feature validation

Report calendar coverage, baseline alignment, daily-feature distributions, and
agreement across weather products.

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

### 6.2 Yield-response validation

Report spatial, temporal, and extreme-year held-out skill; coefficient and
functional-form uncertainty; and comparison with process-model ranges.

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

### 6.3 Marginal damages and global SCC

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
