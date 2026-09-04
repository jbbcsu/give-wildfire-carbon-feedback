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
The next metadata-only contract pins the 90 official daily files required to
replicate this contiguous design across five ESMs and three scenarios. If all
187.139 GB pass content and feature validation, the matrix contains 120
complete centered templates; whole-ESM and whole-scenario exclusions retain 96
and 80 training templates, respectively. No additional matrix content or
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
