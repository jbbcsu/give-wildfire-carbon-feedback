# Implementation roadmap and boundary register

## Now: global agriculture replacement

### Priority sequence fixed September 25, 2026

The narrow global-maize annual-rainfall SCC is a benchmark, not the target
estimate. Completion now proceeds through three linked extensions:

1. **Distribution and drought.** Compare seasonal rainfall quantity against
   prespecified within-season timing, wet-day frequency/intensity, dry-spell,
   heavy-rain, and SPEI/PDSI-style moisture-stress families on identical
   support and outer holdouts. Retain a distribution family only when it adds
   stable out-of-sample value; keep moisture families mutually exclusive unless
   a separate attribution design establishes that stacking does not double
   count. Translate timing or drought to SCC only after both the crop-response
   and marginal climate-pulse links pass their promotion gates.
2. **Crop expansion.** Add source-supported rice first, then soybean and wheat
   when a response, covariance, crop calendar, irrigation basis, production
   weight, and welfare mapping are all available on matched support. Never
   scale maize coefficients to another crop or invent missing seasonal weights.
   Report crop-specific estimates before aggregating them.
3. **Winners and losers.** Preserve cell and country responses through the
   damage calculation. Report gross gains, gross losses, net effects, the
   number and production/value share of positive and negative regions, sign
   stability across climate models, and results by irrigation regime and
   adaptation scenario. A small global net value must not be interpreted as
   small local effects.

The first publishable global estimate will therefore be a transparent sum of
only the crop-by-moisture channels that pass all gates. Omitted channels remain
listed rather than being filled by an assumed coefficient.

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
