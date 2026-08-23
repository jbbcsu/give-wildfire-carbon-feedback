# Precipitation patterns, global agricultural damages, and the social cost of carbon

## Abstract

Climate change alters not only mean precipitation but also the timing,
seasonality, dry spells, and heavy-rainfall exposures that govern crop water
stress and excess-water damage. Existing GIVE agriculture in this checkout is
a temperature-only welfare response, so it cannot identify a marginal
precipitation contribution. We develop a replacement pathway: daily,
crop-calendar-aligned climate features are linked to gridded crop outcomes in
a joint temperature--water response; the response is evaluated under matched
baseline and CO2-pulse climate paths, translated through one agricultural
welfare layer, and passed to GIVE's SCC calculation. We pre-specify fixed,
trend, and upper adaptation scenarios and retain climate, response, calendar,
and welfare uncertainty. The manuscript reports no SCC estimates until the
validated feature panel and response draws are available. Its central outcome
will be a global SCC decomposition that does not stack precipitation damages
on top of the existing temperature-only agriculture component.

Analysis completion and permitted claim status are maintained in
`RESULTS_STATUS.md`; the manuscript must not advance beyond that ledger.

## 1. Introduction

Agricultural climate damages depend on the distribution of weather within a
growing season. A country-year annual precipitation average obscures planting
timing, dry-spell duration, waterlogging, and heavy-rain exposures. These
features can covary with temperature and CO2, so a precipitation-only model
can misattribute joint climate effects.

This study asks: how does the agricultural component of the global SCC change
when a temperature-only agricultural pathway is replaced by a joint,
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

The estimation outcome is GDHY gridded yield for maize, rice, wheat, and
soybean. Daily ISIMIP climate fields and GGCMI Phase 3 crop calendars supply
stage-level temperature and precipitation information. Features include
stage-weighted temperature, seasonal precipitation or water balance,
consecutive dry days, wet-day frequency, heavy-rain/water-excess metrics, and
stage-resolved maximum-temperature threshold days and degree-days. Heat
thresholds are registered explicitly rather than supplied by a universal code
default. Partition validation requires ordered thresholds to have nested day
counts and aggregate degree-day differences consistent with those counts,
before stage totals are reconciled to the season. All features are computed at
grid-cell and crop-year level before aggregation. Monthly CRU scPDSI supplies a
calendar-aligned historical
climatic-index benchmark only; future water-stress features are recomputed from
matched baseline and pulse climate paths rather than extrapolating the
observed index.

GDHY supplies one crop-season-grid-year yield rather than separate rainfed and
irrigated outcomes. The current diagnostics therefore use only the rainfed
calendar exposure. A production all-area panel will combine rainfed and
irrigated calendar features with independent, fixed-baseline crop-area shares
to retain exactly one exposure row per observed yield; it will not duplicate
the outcome across regimes or infer the shares from yield.

## 4. Empirical design

The primary response is a hierarchically pooled fixed-effects model with
crop/grid controls, year effects, flexible stage weather functions, and
temperature--precipitation interactions. It is compared to process-based
GGCMI/ISIMIP outcomes and, only as a predictive comparator, a constrained
sequence/ML model. CO2 concentration and adaptation are explicit scenario
inputs; market feedback is applied exactly once in the welfare translation.

## 5. SCC implementation

For every paired climate draw, a baseline and marginal CO2-pulse path share
GCM/member, crop calendar, socioeconomic path, response draw, and weighting
scheme. Cell-level yield responses are aggregated with fixed baseline weights,
translated to 16 FUND regions, and supplied to the replacement component.
GIVE's existing marginal-damage/discounting machinery then produces the global
SCC. Before either member of a paired run, a structural audit requires
`DamageAggregator.damage_ag` to have the sole internal producer
`JointAgriculture.agcost` and requires the baseline `Agriculture` component to
be absent. The unmodified GIVE graph fails this test by design. A passing graph
is an accounting prerequisite, not evidence of response validity or an SCC
result. Results report fixed, trend, and upper adaptation scenarios separately.

## 6. Results (pre-registered placeholders)

### 6.1 Climate-feature validation

Report calendar coverage, baseline alignment, daily-feature distributions, and
agreement across weather products.

### 6.2 Yield-response validation

Report spatial, temporal, and extreme-year held-out skill; coefficient and
functional-form uncertainty; and comparison with process-model ranges.

Current diagnostic evidence is deliberately below that release gate. In the
1982–89 rainfed panel, a frozen coefficient-suppressing audit evaluated
321,620 consecutive observed-yield pairs across six crop-season labels. The
three-window joint model had the lowest RMSE in 11 of 18 crop-by-holdout
comparisons, but the seasonal joint and precipitation-only models led five and
two comparisons, respectively. No candidate beat a zero-change prediction in
the second-season-rice temporal block, and richer models also failed that
benchmark in its spatial block. This retained mixed result is an internal
predictive diagnostic, not model selection, causal response evidence, or an
SCC input; the complete-period, irrigated, heat, drought-family, uncertainty,
and external-validation gates remain open. In an outcome-separate 1992–2000
maize replication, the three-window model again led spatial and extreme-case
RMSE, but precipitation-only led the temporal block; the earlier temporal
ordering therefore did not replicate and is not a basis for period-specific
model choice.

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
