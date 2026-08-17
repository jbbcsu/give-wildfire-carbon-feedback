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
The new `JointAgriculture` component emits the same regional `agcost` quantity
as the baseline agriculture component and replaces it. The primary quantity is
the joint climate marginal damage. Any precipitation attribution is a declared
decomposition of a joint model, not a separately identified causal outcome.

## 3. Data and feature construction

The estimation outcome is GDHY gridded yield for maize, rice, wheat, and
soybean. Daily ISIMIP climate fields and GGCMI Phase 3 crop calendars supply
stage-level temperature and precipitation information. Features include
stage-weighted temperature, seasonal precipitation or water balance,
consecutive dry days, wet-day frequency, and heavy-rain/water-excess metrics.
All are computed at grid-cell and crop-year level before aggregation.

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
SCC. Results report fixed, trend, and upper adaptation scenarios separately.

## 6. Results (pre-registered placeholders)

### 6.1 Climate-feature validation

Report calendar coverage, baseline alignment, daily-feature distributions, and
agreement across weather products.

### 6.2 Yield-response validation

Report spatial, temporal, and extreme-year held-out skill; coefficient and
functional-form uncertainty; and comparison with process-model ranges.

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
