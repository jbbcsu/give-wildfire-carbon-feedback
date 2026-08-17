# Literature-first assessment: agricultural precipitation-pattern damages

## Recommendation

Do **not** begin with a new deep-learning system.  Existing peer-reviewed
global crop-model ensembles are the strongest immediately usable source of
daily climate, crop-calendar, water-balance, yield, and CO2-response
information.  They are suitable as a structured-scenario and uncertainty
benchmark, but they do not directly provide a causal, monetary partial effect
of precipitation timing that can be added to GIVE.  The first publishable
implementation should therefore replace the temperature-only MooreAg
agriculture sector with a jointly estimated temperature--precipitation
response, benchmarked to crop-model ensembles and translated once through a
documented economic/welfare layer.

The current MooreAg implementation takes only global temperature and a
precomputed 16-region GTAP welfare table.  It contains no precipitation input
or separable precipitation coefficient.  Adding a new precipitation loss to
it would double count whenever the original scenario/welfare inputs embodied
water effects; estimating a residual from this collapsed surface is not
identified.  The main model must use either `MooreAg` **or** the new joint
agricultural sector, never both.

## Existing model classes and fitness for GIVE

| Class | What is usable | Limitation for SCC | Decision |
|---|---|---|---|
| Global gridded crop-model ensembles (GGCMI/ISIMIP/AgMIP) | Daily temperature, precipitation, radiation, CO2 and management inputs are propagated through crop physiology/water balance; multi-model, crop, scenario, and irrigation uncertainty can be retained. | Structural models have calibration/management and CO2-fertilization uncertainty; their counterfactuals are not empirical causal estimates, and yield changes need a market/welfare mapping. | Primary climate-impact benchmark and source of projected feature/yield scenarios. |
| Panel econometrics with crop-calendar/stage weather | Can estimate conditional historical associations with location/year fixed effects and jointly control temperature, water, and shocks. | Coverage and measurement error vary; extrapolation to unobserved extremes and long-run adaptation is weak. | Primary estimating strategy if global gridded yields and harmonized daily weather pass diagnostics. |
| Existing Moore et al. / GTAP welfare surface | Already matches GIVE's 16 FUND-region economic architecture. | In this checkout it is temperature-only and cannot identify precipitation effects. | Benchmark only; replace rather than augment. |
| Machine learning | Flexible interactions and sequences can improve prediction in data-rich regions. | Prediction alone is not a climate-change causal effect; distribution shift, correlated drivers, and weak interpretability are material. | Later robustness/emulator layer, not main causal model. |

Relevant peer-reviewed foundations include: [Rosenzweig et al. (2014)](https://doi.org/10.1073/pnas.1401979111)
for multi-model global agricultural risk; [Moore et al. (2017)](https://doi.org/10.1038/s41467-017-01792-x)
for the crop-impact-to-GTAP-to-SCC architecture; [Iizumi and Ramankutty
(2015)](https://doi.org/10.1038/nclimate2351) for observed yield and climate
extremes; [Xia et al. (2021)](https://doi.org/10.1029/2021WR029884) for
growth-stage dependence of precipitation extremes; and [Lange
(2021)](https://doi.org/10.5194/gmd-14-5443-2021) for bias-adjusted climate
inputs.  These support the design; none licenses the use of a universal
precipitation coefficient without re-estimation.

The closest operational empirical candidate is [Carleton et al.
(2025)](https://doi.org/10.1038/s41586-025-09085-w): a global subnational
agricultural framework with adaptation treatment, climate-model and
statistical-draw uncertainty, and an SCC application.  Its reported modest
out-of-sample improvement from rain-day/extreme-rain additions conditional on
seasonal precipitation and daily temperature is a reason to preregister
feature selection rather than presume every timing metric belongs in the main
specification.  Useful complementary evidence is [Zampieri et al.
(2017)](https://doi.org/10.1088/1748-9326/aa723b) on wheat drought/water
excess, [Jarrett et al. (2023)](https://doi.org/10.1016/j.ecolecon.2022.107627)
on global dry spells, [Matiu et al. (2023)](https://doi.org/10.1038/s43247-023-00685-7)
as a predictive compound-extreme benchmark, and [Jägermeyr et al.
(2019)](https://doi.org/10.1038/s41597-019-0023-8) for GGCMI daily forcing and
process-model coverage.

## Target estimand and climate features

For crop `k`, grid/country `r`, harvest year `t`, estimate the counterfactual
yield (or welfare) difference caused by the distribution of precipitation
under a CO2-pulse climate path, holding the explicitly chosen non-precipitation
drivers at their matched pulse/baseline values.  Construct features by local
crop calendar and phenological stage, not calendar year:

* stage-specific precipitation total and water balance (precipitation minus
  reference evapotranspiration, where defensible);
* onset, cessation, seasonal concentration and timing relative to planting,
  flowering and grain filling;
* maximum consecutive dry days, wet-day frequency, heavy-rainfall days and
  Rx1day/Rx5day; and
* joint hot-dry and wet-heat indicators.

Use daily bias-adjusted GCM fields, crop calendars, irrigated/rain-fed shares,
and a fixed historical reference.  Do not infer these quantities from global
annual temperature or annual country rainfall.

## Main empirical design (required before SCC integration)

Estimate a pre-specified, hierarchically pooled response surface on historical
gridded/subnational yields:

`log(y_kr t) = location FE + year FE + f(T stages, P-pattern stages, VPD,
solar) + T×P + controls + error`.

The precipitation contribution in a climate projection is the *joint-model*
prediction difference under the matched projected feature vectors, allocated
with a Shapley/decomposition rule that is declared in advance.  Report the
joint climate effect as primary; label any precipitation-only decomposition as
an accounting attribution, not a uniquely observed causal quantity.  Include
CO2 concentration explicitly and use crop-model CO2 sensitivity scenarios;
never let CO2 fertilization be hidden inside the precipitation coefficient.

Use location fixed effects, flexible year effects, crop/irrigation strata,
spatially blocked and temporally held-out validation, and placebo/pre-trend
checks.  Cluster or spatially model errors.  Treat adaptation as an explicit
scenario: fixed observed practice; calibrated autonomous adaptation; and an
upper-bound calendar/cultivar adjustment.  Market-price and trade feedbacks
are applied once in the welfare layer, not both in the yield estimator and
again in GTAP.

## ML contingency, only if the econometric design fails coverage/skill gates

Build a sequence model only after publishing the above benchmark and a held-out
failure analysis.  Candidate architecture: a crop-calendar-aligned temporal
fusion transformer or LSTM encoder for daily weather, combined with static
soil, crop, irrigation, and management features; a multi-task head predicts
crop-specific yield distribution/quantiles.  Compare it with: (1) a staged
fixed-effects distributed-lag econometric model; (2) gradient-boosted feature
model; and (3) GGCMI/ISIMIP process-based simulations.  Maintain GCM member
coherence and use domain-held-out regions, years, and extremes as test sets.

ML is acceptable only as a calibrated emulator/predictive robustness check
unless it is embedded in a causal design with explicit treatment variation,
counterfactual controls, and uncertainty calibration.  It must pass: no
warming/no feature change => zero marginal effect; sign/shape checks against
crop-water science; calibration on extremes; and a test that its SCC response
does not arise from temperature/CO2 changes when precipitation features are
held fixed.

## SCC translation and secondary flood scope

Aggregate crop losses to the same welfare concept and regional resolution used
by the replacement agriculture component, then run paired baseline/pulse SCC
draws with matched climate, socioeconomic, crop-response, and market draws.
Store total joint agricultural marginal damage and its attribution separately.
Do not combine it with the current MooreAg damage.

Riverine/pluvial damage to housing and built infrastructure remains a later,
separate component driven by basin discharge/short-duration rainfall,
exposure, and protection.  Coastal surge/sea-level damage remains outside its
main scope because CIAM already represents coastal costs.  Flood losses must
not be treated as agricultural yield losses or used to revalue crop prices.
