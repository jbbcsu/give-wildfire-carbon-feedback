# Future migration interface contract

## Inputs

- The same annual baseline and marginal-pulse climate paths used by GIVE.
- Origin-destination population stocks and flows, with internal/international and
  voluntary/forced status separated.
- Explicit climate triggers and their already-monetized GIVE sector counterparts.
- Income, housing, public-service capacity, amenities, migration frictions, and
  policy restrictions under the same socioeconomic scenario.
- Joint parameter, climate, and scenario uncertainty draws.

## Required outputs

Each row must identify year, origin, destination, baseline/pulse, hazard,
migration type, welfare component, currency/price year, and uncertainty draw.
The SCC bridge accepts consumption-equivalent or equivalent-variation welfare,
not people moved. Real resource costs must be separated from transfers.

## Accounting identities

1. Coastal relocation in CIAM is always excluded.
2. Property, agricultural income, labor income, mortality, and direct disaster
   losses already monetized elsewhere are excluded from the migration increment.
3. The global total includes origin and destination changes; remittances and
   fiscal transfers are not global damages by themselves.
4. Migration as adaptation may reduce total climate damages. The sign is not
   constrained ex ante.
5. If the structural model cannot decompose overlap, it replaces overlapping
   GIVE modules in a sensitivity run; it is never added to them.

## Validation

- Historical out-of-sample origin-destination flows and immobility.
- Hazard-specific displacement versus longer-run migration.
- External comparison to reduced-form estimates without forcing agreement.
- Sensitivity to migration restrictions, liquidity, destination congestion,
  expectations, adaptation, and socioeconomic scenarios.
- Conservation of population and transparent treatment of deaths and births.
- A zero-pulse identity test and convergence as pulse size shrinks.

