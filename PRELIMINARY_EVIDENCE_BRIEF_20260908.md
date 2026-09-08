# Preliminary evidence: precipitation, agriculture and GIVE

Goal: replace GIVE's existing agriculture representation with one that can
account for rainfall quantity, timing, drought and irrigation, without adding
the same agricultural damage twice. This is an unfinished research project;
there is **no empirical precipitation SCC estimate yet**.

## 1. Does rainfall affect agricultural yields?

The U.S. results are encouraging for non-irrigated crops. In the matched NASS
reporting sample, moving seasonal rainfall from the sample median to its
10th percentile is associated with about12.9% lower corn yield and10.2%
lower soybean yield in non-irrigated observations. Corresponding associations
in irrigated observations are much smaller, about0.7% and1.0% lower. These
are conditional regression associations, not experimental irrigation benefits,
national averages or climate-change forecasts. The conditional intervals,
geographic coverage and limitations are in
`us_county_validation/US_RAINFALL_CURVE_AND_IRRIGATION_RESULTS_20260907.md`.

Globally, adding country-specific annual controls weakens moisture–yield
associations, especially for soybean. A+0.1 shift in the fixed-weight log-rain
index is associated with+0.367% maize yield [0.135,0.600%], versus+0.014%
soybean yield [−0.543,0.574%]. These are transformations of fitted log-yield
contrasts, not effects of a literal10% rainfall increase. Country labels are
a crop-footprint proxy, and gridded outcomes have construction dependence.
See `GLOBAL_COUNTRY_CONTROL_RESULTS_20260907.md`.

## 2. Is timing more informative than total rainfall?

Not consistently. The global held-out geographic/time tests show small,
uncertain incremental gains, with the relevant paired uncertainty intervals
crossing zero. For maize, quantity-plus-distribution performs slightly worse
than quantity alone in that test. U.S. daily-heat controls also overturn
earlier claims of robust timing improvement. Quantity remains a serious,
parsimonious primary candidate; timing will not be privileged for novelty.
See `GLOBAL_CONTINUOUS_GEOGRAPHIC_CLUSTER_RESULTS_20260907.md` and
`us_county_validation/US_DAILY_HEAT_EXPANSION_RESULTS_20260907.md`.

Drought remains a competing representation, not an extra damage to add to
rainfall. Historical scPDSI shows positive maize associations under annual
country controls, but does not automatically improve prediction; soybean
scPDSI performs worse than quantity in the geographic test. These findings
do not imply drought is unimportant or establish future PDSI attribution.

## 3. Does climate change alter those rainfall exposures?

We currently use bias-adjusted daily climate-model projections, not a promoted
new precipitation emulator. Both seasonal quantity and daily/stage distribution
are measured. The earlier feature emulators failed their validation criteria
and were not used for damages (`PHYSICAL_LINK_FEATURE_RESPONSE_CANDIDATE.md`).

The direct scenario comparisons show why one short window is insufficient:
two models disagree on rainfall direction in2042–2049; the retained2032–2059
rainfall differences are negative in all three inspected models for both
crops. Magnitudes differ substantially. The climate pilot covers only39.25
and39.75°N,500supported maize and327soybean cells, not representative global
or U.S. averages. SSP585-minus-SSP126 is not a no-climate-change comparison
and is not the marginal CO2 pulse required for SCC.

The new full-period daily-heat inputs address a missing temperature control,
not crop damages. See `FULL_PERIOD_HEAT_RESULTS_20260908.md` for their final
matched comparisons, exact-overlap checks and extrapolation limits.

The first historical source check is also complete. GFDL has dry spells
about1.9days longer than the observed-source historical series, even before
comparing future periods. For soybean, the future dry-spell change is slightly
negative against model history but positive against observed-source history.
This is why the baseline and data source matter; the whole latter difference
cannot be labeled a climate-change effect. Heat extrapolation remains large
against either history. See`HISTORICAL_CLIMATE_BENCHMARK_RESULTS_20260908.md`.

The independent IPSL historical benchmark is now complete too. Its historical
precipitation-pattern offsets are smaller, but future changes still depend on
model and baseline: maize precipitation underSSP585 rises relative to IPSL's
history and falls slightly relative to GFDL's history on the same292cells.
This is not a contradiction with the higher-minus-lower-scenario comparison;
they ask different questions. Source-matched heat extrapolation remains large.
See`IPSL_HISTORICAL_CLIMATE_BENCHMARK_RESULTS_20260908.md`. A published
historical counterclimate alternative is being assessed before any new custom
counterfactual model (`ATTRICI_METHOD_ASSESSMENT_20260908.md`).

## 4. What separates this evidence from a defensible SCC result?

We still need a defensible joint crop-response specification and transport
test, historically matched climate-model/source-bias checks, explicit CO2 and
adaptation treatment, production/revenue and market-welfare calibration,
broader representative coverage, and a validated baseline-versus-emissions-
pulse route through GIVE. A large share of future heat exposures lies outside
historical cell-specific ranges. Multiplying historical rainfall coefficients
by scenario changes would hide these unresolved issues.

Published welfare methods have been reviewed and a price/quantity-only
component tested. Hypothetical normalized market calculations are not measured
damages. See `HULTGREN_WELFARE_SOURCE_REVIEW_20260908.md` for resolved source
details and remaining expectation/storage/cost ambiguities. No synthetic test
data or hypothetical shock has been presented as an empirical finding.
