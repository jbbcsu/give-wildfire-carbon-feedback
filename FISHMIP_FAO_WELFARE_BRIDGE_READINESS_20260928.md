# FishMIP–FAO welfare-bridge readiness audit

## Decision

The resident evidence does not support a defensible global coupling from
FishMIP catch to fisheries welfare. A global structural catch-density
diagnostic exists, but a globally complete **welfare-ready** response does not.
The next requirement is a licensed bioeconomic bridge bundle, not a scalar
price, a fixed historical allocation, or a transferred Blue-SCC coefficient.

## What the resident data establish

- The 20 checksum-pinned FishMIP files span two climate forcings, two ecosystem
  models, historical/control experiments, and SSP1-2.6/SSP5-8.5. Their exact
  four-structure intersection has 40,398 finite 1-degree cells.
- The only acquired response variable is `tc`, global monthly total catch
  density in `g m-2`. It has no stock, species, market-commodity, fleet,
  landing-country, consumer-country, price, cost, or welfare dimension.
- The adjusted paths are scenario/control structural diagnostics, not matched
  baseline and one-ton-CO2-pulse responses. Absolute model levels are not
  averaged.
- The FAO marine panel has 27,625 species/country/FAO-area records and 75 years
  of physical live-weight tonnage/status pairs. Its 14 static fields contain
  no price, cost, revenue, profit, elasticity, demand, supply, trade, effort,
  management, consumer, producer, or surplus field.
- FAO country is primarily vessel flag, not harvest EEZ, producer ownership, or
  consumer incidence. The licensed EEZ geometry has not been acquired because
  provider permission or human terms acceptance is required; fleet and trade
  incidence remain unidentified even after a future spatial overlay.
- No FishMIP path beats the constant holdout benchmark under the registered
  FAO quality-status family, so historical fit does not supply model weights.
  FAO species composition total-variation distances of 0.315–0.448 and country
  distances of 0.253–0.357 reject a fixed-share bridge.

## Precise external-data request

The machine-readable request in
`config/fishmip_fao_welfare_bridge_readiness_v1.toml` requires five linked
components:

1. Same-realization baseline and marginal one-ton-CO2-pulse harvest or
   availability by model, management case, year, cell/stock, and commodity.
2. Licensed cell/stock-to-EEZ, producer, landing, trade, and consumer incidence,
   with high seas, joint claims, disputes, and missing coverage explicit.
3. Commodity-country-year prices, quantities, demand parameters or
   elasticities, supply/cost parameters, management/effort response, and trade
   closure sufficient to calculate consumer and producer surplus separately.
4. An accounting-boundary record excluding indirect/induced multipliers and
   resolving aquaculture, terrestrial-food substitution, nutrition mortality,
   CIAM, coral, and biodiversity overlap.
5. Explicit licenses, versions, source URLs/DOIs, hashes, coverage definitions,
   and missing/zero/suppressed codes for every raw and derived input.

The audit forbids global `tc × price`, fixed FAO shares, EEZ-as-incidence,
historical-fit probability weights, gross revenue as welfare, Blue-SCC
coefficient transfer, and SSP differences as a marginal pulse.

No imputation or renormalization was performed, and no damage or SCC was
calculated.

## Reproduction

```bash
python3 scripts/audit_fishmip_fao_welfare_bridge_readiness.py
python3 test/test_fishmip_fao_welfare_bridge_readiness.py
```
