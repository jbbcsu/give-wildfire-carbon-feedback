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
irrigation regime and then applying fixed MIRCA shares. It contains no direct
weather terms and has not been fitted. SPEI and scPDSI/PDSI receive serious
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
remain under historical-boundary review. NOAA nClimGrid daily weather has been
validated only for a bounded Cuming County construction smoke, while a
HEAD-only inventory pins the 468 monthly 1981--2019 objects (25.944 GiB
advertised). Their remaining contents have not been acquired or validated, so
the U.S. track has not estimated a weather--yield relationship.

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
feature families. One complete MRI-ESM2-0 SSP3-7.0 precipitation and
mean-temperature pair for 2015--2020 passes pinned SHA-512 and full decoded
content/chronology gates. The temperature block supplies six annual
same-realization GMST values with exact 365/366-day support. This is a bounded
source and processing validation, not a fitted feature response.
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
temperature variables (80 version-pinned datasets). Acquisition remains
bounded to complete MRI-ESM2-0 precipitation and mean-temperature fields for
historical 2011--2014 and SSP3-7.0 2015--2020. Exact checksums and full-array
content gates pass, each variable joins at a 24-hour 2014/2015 boundary, and
the matched temperature fields produce ten annual same-realization GMST
values with complete day counts. A real two-latitude maize/rainfed engineering smoke
produces 2,744 crop-years and 8,232 three-window records whose precipitation
and day-count totals reconcile exactly. It revealed and corrected a
noon-timestamp calendar-boundary error that had omitted maturity dates. No
yield is attached to this smoke and no climate-feature response has been
fitted. This remains one ESM and one future scenario, so the real and synthetic gates establish software behavior,
not future agricultural damages.

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
selected drought definition, no response has been fitted, and CRU scPDSI
cannot supply the matched future baseline/pulse drought path required for SCC.

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

### 6.2 Yield-response validation

Report spatial, temporal, and extreme-year held-out skill; coefficient and
functional-form uncertainty; and comparison with process-model ranges.

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
