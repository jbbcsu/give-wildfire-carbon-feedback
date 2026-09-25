# Preliminary results and claim boundaries

## What is estimated now

### Global precipitation-agriculture quantity channel

The completed paired GIVE calculation replaces the legacy marginal agriculture
response while retaining MooreAg's baseline damage levels. It evaluates a
published global maize response to climate-driven annual rainfall-quantity
changes across 26 climate models. At GIVE's 2% Ramsey schedule, the central
fixed-adaptation, uncapped specification is **-$0.00610 per tCO2** (2020 USD),
with 25 of 26 climate-model point estimates negative.

The full registered design contains 936 paired paths and 3,744 SCC values.
At 2%, its unweighted design-cell mean is -$0.00661, its 2.5th--97.5th design
percentile range is -$0.01137 to +$0.00104, and its full range is -$0.01221 to
+$0.00348 per tCO2; 900 of 936 cells are negative. These are modeling-choice
and climate-model design percentiles, not a probability interval.

Published response-coefficient uncertainty has now been propagated separately.
For the central equal-model mean at 2%, the coefficient-only delta-method
standard error is $0.00218 and the normal 95% interval is **-$0.01037 to
-$0.00183 per tCO2**. Across each of the four discount schedules, 23 of 26
model-specific coefficient-only intervals are wholly negative, two cross zero,
and one is wholly positive. These intervals remain conditional on the narrow
quantity specification.

Geographic and temporal accounting checks clarify the interpretation. Sixty-
one of 106 country means are negative and 45 are positive, but every country
component changes sign across at least one climate model. The United States
and China account for 74.9% of gross absolute country components; removing
both as an accounting diagnostic leaves -$0.00025 per tCO2. At 2%, 44.1% of
the signed value accrues in 2020--2050 and 71.4% by 2100. The through-2100
share ranges from 60.2% at the 1.5% schedule to 87.2% at 3.0%. Thus the narrow
result is geographically concentrated and model-sensitive, but is not small
solely because impacts occur late.

**Allowed claim:** a small paired GIVE SCC estimate has been produced for the
annual global-maize rainfall-quantity channel under explicit market,
adaptation, tail, climate-model, and discounting choices.

**Not allowed:** this is not the total precipitation-agriculture SCC. It omits
rainfall timing, drought, temperature interactions, other crops, endogenous
irrigation and adaptation costs, trade/storage, and several uncertainty layers.
Negative values denote a modeled benefit within this narrow channel and do not
show that climate change benefits agriculture overall.

Primary evidence:

- `QUANTITY_FULL_STRUCTURAL_PAIRED_ENSEMBLE_RESULTS_20260924.md`
- `QUANTITY_COEFFICIENT_DELTA_UNCERTAINTY_RESULTS_20260925.md`
- `data/provenance/quantity_full_structural_paired_ensemble_20260924.json`
- `data/provenance/quantity_coefficient_delta_by_model_20260925.json`
- `QUANTITY_SCC_COUNTRY_DECOMPOSITION_RESULTS_20260925.md`
- `QUANTITY_SCC_PERIOD_DECOMPOSITION_RESULTS_20260925.md`

### U.S. NASS validation

Historical county fixed-effects estimates show materially stronger fitted
rainfall relationships for non-irrigated than irrigated corn and soybean. In
the current direct-practice sample through 2018, a 100 mm rainfall increase is
associated with non-irrigated corn fitted-yield differences of +11.07%, +7.72%,
and +3.59% at the observed rainfall quartiles; the corresponding irrigated
values are +0.04%, -0.41%, and -0.98%. For non-irrigated soybean, the registered
quantity-plus-timing contrasts are +7.44%, +4.46%, and +1.11%, and a partial
middle-for-late rainfall-share shift is +4.73%.

Out-of-sample diagnostics are more guarded. Rainfall quantity improves on heat
controls in eight of eight non-irrigated source/time comparisons, but does not
always beat a zero-change forecast. Timing effects are heterogeneous by crop,
period, and geography. Non-irrigated corn PDSI is the most stable U.S. drought
competitor in the registered predictive comparison, but this does not authorize
a causal response or SCC transfer.

**Allowed claim:** the U.S. evidence supports irrigation stratification and
retaining seasonal quantity as the parsimonious moisture reference, with PDSI
and distribution features tested as competing representations.

**Not allowed:** the fixed-effects associations are not causal climate damages,
the predictive screens do not identify welfare effects, and no U.S.-only SCC
has been produced.

Primary evidence:

- `US_SOURCE_MATCHED_RESPONSE_RESULTS_20260908.md`
- `US_SOURCE_MATCHED_BLOCKED_PREDICTION_RESULTS_20260908.md`
- `us_county_validation/US_COMPETING_MOISTURE_PAIRED_LOSS_UNCERTAINTY.md`

### Fisheries

The local fisheries track has not produced an SCC estimate. A published
external Blue-SCC benchmark reports $22.09755 per tCO2 under its own baseline
settings, composed of $0.05704 market value and $22.04051 non-market
use/nutrition value. It is a literature benchmark, not a GIVE result.

The local FishStat/FishMIP validation weakens the case for empirical weighting
of the four available global biomass paths. In a 1990--1999 calibration and
2000--2014 holdout, no FishMIP path beats the 3.40% relative-RMSE constant
benchmark under the contract quality-status set. Under accepted observations
only, GFDL/BOATS is slightly better than the 7.96% benchmark (7.39%), while the
other three paths are much worse. The paths therefore remain structural
scenarios rather than empirically estimated model weights.

A sector-overlap audit further shows that the published Blue-SCC total cannot
be added directly to GIVE. Its nutrition/mortality pathway requires explicit
cause-of-death and valuation reconciliation against GIVE's Cromar mortality
sector, while its profit/output market multipliers require reconciliation with
agriculture and macroeconomic incidence. This establishes an overlap gate,
not that every published fisheries death or market loss is already counted.

**Allowed claim:** source data and historical validation are reproducible, and
the published benchmark establishes that non-market nutrition can dominate
fisheries SCC estimates.

**Not allowed:** no local fisheries SCC, GIVE-integrated fisheries damage
function, or validated empirical weighting has been obtained. The carbon-pulse
to ocean/ecosystem response and welfare/incidence mapping remain open.

Primary evidence in the isolated fisheries project:

- `../ocean_fisheries_scc/FISHMIP_FAO_BLOCKED_PREDICTION_RESULTS_20260925.md`
- `../ocean_fisheries_scc/BLUE_SCC_FISHERIES_BENCHMARK_AUDIT.md`
- `../ocean_fisheries_scc/data/provenance/fishmip_fao_blocked_level_prediction_20260925.json`
- `../ocean_fisheries_scc/FISHERIES_GIVE_OVERLAP_AUDIT_20260925.md`

## Current interpretation

The precipitation project now has a real but deliberately narrow paired GIVE
estimate. The U.S. work validates the importance of irrigation and the
quantity-first hierarchy but is not yet a causal transport model. The fisheries
work has a credible published scale benchmark but not a local SCC. The next
scientific priority is to add defensible omitted precipitation mechanisms—most
importantly drought/within-season stress and crop/irrigation coverage—without
stacking correlated moisture measures or double-counting MooreAg.
