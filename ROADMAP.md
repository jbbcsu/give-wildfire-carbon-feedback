# Implementation roadmap and boundary register

## Now: global agriculture replacement

1. Obtain the manifest inputs into a separately versioned data store and record
   checksums/licenses.
2. Build crop-calendar seasonal precipitation quantity as the parsimonious
   direct-weather reference. Test timing, occurrence, intensity, dry-spell,
   and wet-extreme extensions only for robust incremental value under common
   outer holdouts. Build PDSI/scPDSI, SPEI, and soil-moisture representations
   as mutually exclusive competitors, not additive moisture terms.
3. Derive every response-basis term within irrigation regime, combine regimes
   with fixed independent area shares, and fit the single aggregate crop-grid
   yield outcome. Report null and worse predictive results; never select a
   family by its eventual SCC magnitude.
4. Freeze a causal response only after predictive stability, identification,
   external validation, and process-model benchmarking pass. Separately derive
   the selected moisture exposure under matched baseline and CO2-pulse climate
   draws; historical drought prediction alone does not identify this climate-
   to-drought link.
5. Translate one validated joint yield response through one welfare/market
   layer and run
   matched baseline/pulse global SCC simulations for `fixed`, `trend`, and
   `upper` adaptation scenarios.

The eventual cell-to-FUND aggregation uses the frozen country-to-FUND mapping
in `config/`; it still requires a separately licensed and versioned grid-cell
country mask plus baseline harvested-area/value weights. Do not infer a FUND
region from latitude or use climate-responsive weights.

## Later: noncoastal infrastructure flooding (deferred)

Create a separate `InlandInfrastructureFloodDamages` component with basin
discharge/short-duration-rainfall hazard, buildings/infrastructure exposure,
protection, and vulnerability inputs.  It must exclude cropland pixels and
coastal surge/sea-level losses; the latter remain in CIAM.  Do not attach this
component to the agriculture aggregator or include it in current SCC results.
