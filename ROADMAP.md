# Implementation roadmap and boundary register

## Now: global agriculture replacement

1. Obtain the manifest inputs into a separately versioned data store and record
   checksums/licenses.
2. Derive crop-calendar-aligned features under baseline and matched CO2-pulse
   climate draws; aggregate only after crop/irrigation-level estimation.
3. Fit the pre-registered joint response; benchmark against GGCMI/ISIMIP,
   fixed-effects, and ML predictive comparators.
4. Translate one joint yield response through one welfare/market layer and run
   matched baseline/pulse global SCC simulations for `fixed`, `trend`, and
   `upper` adaptation scenarios.

## Later: noncoastal infrastructure flooding (deferred)

Create a separate `InlandInfrastructureFloodDamages` component with basin
discharge/short-duration-rainfall hazard, buildings/infrastructure exposure,
protection, and vulnerability inputs.  It must exclude cropland pixels and
coastal surge/sea-level losses; the latter remain in CIAM.  Do not attach this
component to the agriculture aggregator or include it in current SCC results.
