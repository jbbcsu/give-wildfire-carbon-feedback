# Crop-specific response and SCC integration contract

This contract separates empirical response estimation from welfare accounting.
It is executable scaffolding, not a calibrated damage function and not an SCC
result.

## Array boundary

Every response draw supplies arrays keyed by `draw_id`, `year`, ordered FUND
region, and crop/season. The crop order is frozen in
`config/crop_response_contract.toml`. Feature anomalies are constructed under
matched baseline and CO2-pulse climate paths before geographic aggregation.
Crop/season coefficients remain distinct; hierarchical estimation may share
information but cannot collapse the executable bundle to an undocumented
common slope.

`CropResponseAggregation` accepts crop-specific mean temperature, seasonal
precipitation, precipitation timing, one water-stress representation, wet
extremes, heat extremes, and the registered temperature--precipitation
interaction. The water-stress field is deliberately singular: a direct
dry-spell/water-balance specification and a PDSI/SPEI/soil-moisture
specification are alternatives unless a validation protocol explicitly
identifies non-overlapping terms.

## Weight and coverage rule

`crop_value_share` is a fixed baseline share of the complete agricultural
value pool in each FUND region. It must not respond to the climate realization
or CO2 pulse. The production default requires shares to sum to one. A partial
coverage run is allowed only when `require_full_coverage=false`; it is a
diagnostic, reports the coverage share, leaves the unrepresented share with no
modeled response, and is not eligible for an SCC estimate. Normalizing four
or six modeled crops to one would instead extrapolate their response to
unmodeled agriculture and therefore requires a separately justified welfare
model, not a silent code default.

## Adaptation and welfare

Positive crop losses are multiplied by the named crop-specific adaptation
schedule before aggregation; modeled benefits are retained. Any adaptation
cost is an explicit share of that crop's baseline value. The resulting
regional joint-loss fraction is passed once to `JointAgriculture`, which
scales it by the MooreAg-compatible regional agricultural value pool and emits
`agcost` in billion 2005 USD/year.

This reduced-form scaling is only an interface test. A production analysis
must choose and validate one welfare layer (for example, a GTAP-compatible
emulator) and show that crop prices, trade spillovers, CO2 fertilization, and
adaptation costs each enter once. If the selected welfare layer emits regional
monetary welfare directly, it should replace the scaling step rather than be
added to it.

## GIVE wiring and paired runs

For each Monte Carlo draw:

1. Freeze FAIR/RFF-SP, climate model/member, calendar, response, crop weights,
   adaptation, and welfare draw IDs.
2. Construct baseline and one-tonne-CO2-pulse crop features with those same
   IDs and verify that pre-pulse differences are zero.
3. Evaluate `CropResponseAggregation` separately for the paired feature paths.
4. Replace `MooreAg.Agriculture` with `JointAgriculture`; connect its `agcost`
   to `DamageAggregator.damage_ag`. Never instantiate both agriculture
   components.
5. Keep Cromar mortality, energy, and CIAM enabled; disable DICE and
   Howard--Sterner aggregate damage functions. Discount the pulse-minus-base
   total-damage path using GIVE's established SCC routine.

An integration test must inspect the model component graph, not merely compare
numeric totals: exactly one agriculture producer may feed `damage_ag`. Further
required gates are complete region/crop coverage or a pre-registered gap
model; units and FUND order; finite coefficient draws; fixed normalized
weights; matched IDs; zero-feature and zero-pulse conservation; held-out
response skill; observed-support flags; and a one-for-one agriculture
replacement test.
