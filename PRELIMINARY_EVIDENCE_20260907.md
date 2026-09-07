# Preliminary precipitation–agriculture evidence

Status as of September 7, 2026. This is a research results summary, not a slide
deck or completed SCC paper. Main aim: replace GIVE's existing agricultural
damage pathway with a defensible joint temperature–water response and assess
the implications for SCC without double counting legacy agriculture.

## What the current estimates say

**Country-specific annual shocks materially weaken the global soybean
quantity result.** On a fixed country-mapped sample, the fitted +0.1 log-rain
index contrast drops from 0.381% to 0.014% for soybean (interval spans zero),
and from 0.574% to 0.367% for maize (positive conditional interval). Soybean
drought contrasts also span zero. Country labels come from a conservative
crop-footprint proxy, not verified GDHY source-unit boundaries. All definitions,
sample exclusions and 16 fits: `GLOBAL_COUNTRY_CONTROL_RESULTS_20260907.md`.

**New global association fits are complete.** On the original 1983–2010
training support, maize rainfall and scPDSI partial contrasts are positive;
soybean quantity and drought intervals include zero after unrestricted annual
controls under 20-degree block uncertainty. Positive timing associations do
not reverse the weak/uncertain out-of-sample improvements. These are
equal-grid-pair, aggregate-irrigation historical fits, not future-climate
effects or global production-weighted gains. Exact contrasts, all 16 fits and
two clustering variants: `GLOBAL_HISTORICAL_ASSOCIATION_RESULTS_20260907.md`.

**Regional U.S. rainfall–yield associations persist after daily heat controls.**
For reported non-irrigated corn, the illustrative fitted +100 mm seasonal-rain
contrast near median rainfall is about +5.7% yield; for soybeans it is about
+3.8–3.9%. These are county/state-year fixed-effect historical associations
with held-fixed included controls, not average gains from future climate
change. The samples cover 10 and five states, respectively. Both thresholds
and state-omission sensitivities retain positive direction, with meaningful
variation in magnitude. The previous corn estimate of +7.7% was materially
attenuated by daily heat. Exact specifications, intervals, source counts and
all comparisons: `us_county_validation/US_DAILY_HEAT_ASSOCIATION_RESULTS_20260907.md`.

**Timing/distribution is not a uniformly robust predictive addition.**
Positive timing associations do not override the predictive evidence. The
full daily-heat moisture comparison fails the original every-eligible-state
materiality rule for the distribution extension in all crop/practice groups.
Some tests improve; some do not improve enough or worsen. Rainfall quantity
remains a parsimonious comparator, not a universally validated primary model.
PDSI is a serious competing moisture-stress representation, not an additive
extra precipitation damage. See
`us_county_validation/US_DAILY_HEAT_EXPANSION_RESULTS_20260907.md` and
`us_county_validation/US_MOISTURE_TMAX_RESULTS_20260905.md`.

**Global historical predictive improvements are small and uncertain.**
The continuous maize/soy data permit temporally and geographically separated
prediction tests. Rainfall quantity has the lowest pooled maize RMSE; the
distribution extension has the lowest soybean RMSE. But paired block-based
descriptive uncertainty intervals include zero improvement over their
comparators. scPDSI does not beat quantity here, and soybean scPDSI models
perform worse. GDHY grid counts are not independent observations, and the
block analysis does not eliminate all shared-source/spatial dependence.
See `GLOBAL_CONTINUOUS_GEOGRAPHIC_CLUSTER_RESULTS_20260907.md`.

## What is NOT estimated yet

1. Globally transferable causal yield responses, including a defensible
   long-run adaptation interpretation and joint-driver counterfactual.
2. Agricultural losses attributable to projected climate-induced rainfall
   change across a validated global ensemble or matched marginal CO2 pulse.
3. Agricultural welfare replacement accounting and an empirical updated SCC.

Climate-feature engineering and synthetic GIVE integration tests do not fill
these missing empirical links. Small RMSE gains cannot be converted to dollar
damages. Yield percentages multiplied by revenue are not automatically welfare.

## Immediate continuation priorities

Package the historical results with geographic/sample limits and resolve the
counterfactual response specification; separate this from the missing future
climate-generator implementation. Advance a justified existing-model/direct-
scenario route if it avoids an unnecessary emulator dependency, without
weakening source, attribution or welfare requirements. Explicitly document
the unrepresented crop/sector residual before replacing all GIVE agriculture.
Do not add unrelated sectors or repeatedly rerun completed audit suites.

The next distinct implementation step is the published partial-equilibrium
welfare-route review in `PUBLISHED_WELFARE_ROUTE_ASSESSMENT_20260907.md`:
read the detailed published equations and inspect replication components,
then implement tested economic accounting without inventing calibration inputs.
This proceeds independently of the unavailable daily-generator implementation.

Follow-up: the independent market-accounting core now passes seven synthetic
tests, including stable tiny-increment surplus calculations. It is not
calibrated, and no SCC gate is opened. Detailed supplement review is blocked
by the web reader's 34.8 MB size limit and the local no-download rule below
150 GiB; a bounded document exception or supplied readable copy would unblock
that review. See `WELFARE_ACCOUNTING_PROTOTYPE.md`; do not repeat the same
failed PDF searches on subsequent follow-ups.

The active task now chains safe steps, with a five-minute in-task follow-up
instead of the previous four-hour standalone schedule. One monitored job at
a time; up to 4 GiB with current memory-pressure checks. Low-output existing-
data work proceeds below the bulk-acquisition reserve; no automatic raw-data
rehydration. A completed preliminary benchmark is not overall project completion.
