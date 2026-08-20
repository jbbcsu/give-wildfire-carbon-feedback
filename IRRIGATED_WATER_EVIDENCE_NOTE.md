# Supplied US water papers: relevance and boundary

## Sources assessed

This note assesses two manuscripts supplied to the project on 2026-08-20:

1. Gordon, Blumberg et al., *Warming and Snow Loss Threaten the Economic
   Viability of Irrigated Agriculture* (hereafter `Gordon-Blumberg`).
2. Blumberg and Warziniack, *Climate-driven water stress in the United States
   is seasonal, regional, and shaped by adaptation* (hereafter
   `Blumberg-Warziniack`).

Their publication status and external data/code releases have not been
independently verified here.  No result, coefficient, data, or figure from
either manuscript is imported into the GIVE component without a separately
documented permission/provenance check.

## Assessment

| Paper | What it contributes | What it does not provide |
|---|---|---|
| `Gordon-Blumberg` | A 950-western-US-watershed hydro-economic design linking temperature, precipitation, April 1 snow-water equivalent, and runoff to irrigated land allocation and cash rents. It distinguishes annual planting responses from longer-run land-use/rental responses, includes temperature-by-runoff interactions, and uses future hydrologic projections. | A global crop-yield response; a rainfed precipitation-timing coefficient; or a standalone SCC damage function. Its western-US coverage and irrigated economic outcomes must not be mechanically extrapolated. |
| `Blumberg-Warziniack` | A monthly US crop-irrigation-withdrawal design using climate/hydrology inputs, month-by-farm-resource-region heterogeneity, high-dimensional fixed effects, county trends, forecast validation, and explicit adaptation counterfactuals. | Crop yields, farm welfare, irrigation water consumption, or a causal valuation of water scarcity. A withdrawal is not a damage measure and cannot be added beside an agricultural loss without an explicit linking model. |

## Implications for the precipitation-SCC project

1. **Keep the present primary estimand rainfed.**  The US county yield module
   must continue to use a crop-specific irrigated-area gate.  It cannot label
   NASS county yield as rainfed simply because a county lies east of a
   meridian or has low average withdrawals.
2. **Do not assume irrigation perfectly buffers precipitation changes.**  In a
   future irrigated-crop extension, allow the weather response to interact
   with a pre-period measured irrigation share and with exogenous seasonal
   water-availability indicators.  The interaction is an empirical question,
   not a fixed adaptation credit.
3. **Treat snow/runoff as a distinct pathway.**  For snowfed western basins,
   crop-season precipitation total is not a sufficient measure of irrigation
   supply.  A later module should construct upstream, seasonally aligned
   snow-water-equivalent/runoff availability, reservoir/institutional context,
   and groundwater reliance.  It must be integrated as an irrigated-water
   constraint within agriculture, not stacked as a second loss for the same
   crop outcome.
4. **Treat withdrawals as an adaptation/input outcome, not damage.**  The
   monthly withdrawal model is useful for scenario design and stress testing:
   fixed practice; continuation of observed efficiency/trends; and a
   deliberately optimistic efficiency case.  It cannot by itself translate a
   climate-induced change in withdrawals into welfare or SCC.
5. **Preserve accounting boundaries.**  The primary global joint agricultural
   replacement still supersedes `MooreAg`; it is not augmented by a US
   irrigated-water estimate.  Any later western-US water-supply module is a
   validation/heterogeneity layer until it has global coverage and a single
   welfare translation.  Coastal and noncoastal flood modules remain outside
   this scope.

## Implementation roadmap

### Now (authorized core work)

* Retain daily precipitation quantity, timing/distribution, dry-spell, and
  heavy-rain features for rainfed crop outcomes.
* Acquire crop-specific irrigated-area data for the US sample and report the
  rainfed-selection threshold/sensitivity.
* Add an `irrigation_gate` provenance field; do not yet add modeled runoff or
  withdrawal controls to the primary rainfed response.

### Later US irrigated-water extension (separate pre-analysis plan)

* Unit: an upstream-supply/cropped-area linkage rather than county-centroid
  weather alone; compare HUC8/HUC12 and allocation-system alternatives.
* Exposures: crop-stage local weather, pre-season SWE, irrigation-season
  runoff, reservoir/storage proxy, groundwater reliance, and water-rights or
  allocation constraints where available.
* Outcomes: irrigated crop area, crop-specific irrigated yield where observed,
  and a clearly separate economic outcome such as rent or net revenue.
* Identification: fixed-effect weather shocks for annual behavior plus a
  separately labelled long-difference/adaptation analysis; do not describe the
  latter as the same short-run causal estimand.
* Integration gate: demonstrate no overlap with the joint crop response,
  independently validate the hydrologic data, and provide a global or
  explicitly US-only welfare bridge before any SCC use.
