# Tropical-cyclone damages: GIVE readiness audit

Status: published benchmark and target coefficients verified October 17, 2026.
No numeric addition to GIVE is authorized.

## Sector selection

Tropical-cyclone damages are the strongest next omitted-sector candidate.
Krichene et al. (2023) provide a peer-reviewed global model, country-specific
temperature damage functions for 41 cyclone-affected countries, a global-mean-
temperature-to-cyclone exposure emulator, an explicit carbon-pulse SCC
calculation, open code, licensed inputs, and machine-readable source tables.
This evidence is substantially closer to GIVE than current global inland-flood
or disease packages.

The exact GIVE target does not explicitly represent tropical-cyclone wind
damage. CIAM covers sea-level-rise and storm-surge pathways. The Krichene model
uses population exposed to cyclone winds of at least 34 knots and explicitly
excludes rainfall and storm surge, so its physical hazard does not directly
duplicate CIAM.

## Reproduced published benchmark

For SSP2-RCP6.0, a 2025 pulse of 1 GtC, a horizon through 2200, and the Ricke
discounting parameters (pure rate of time preference 2%, elasticity 1.5), the
released source table reports median SCCs in constant 2005 USD of:

- 211.729305 dollars per tonne CO2 with temperature and cyclone effects; and
- 173.084449 dollars per tonne CO2 with temperature effects only.

The difference of those published medians is 38.644856 dollars per tonne CO2,
or 22.33% of the temperature-only median. This is an external benchmark, not a
GIVE estimate and not the median of paired cyclone-only draws. The authors'
code computes cyclone-only SCC draw by draw before taking quantiles, but the
released source CSVs do not contain the global paired cyclone-only quantiles.
Subtracting the published uncertainty bounds would also be invalid.

The released coefficient table contains exactly two coefficients for each of
41 countries: an intercept and a linear response of persistent per-capita GDP
growth effects to GMT. The source-table routine multiplies the internal
fractional-growth coefficients by 100, so the published GMT slopes are
percentage points of annual per-capita GDP growth per degree Celsius, not
fractions. Thirty-eight country mean GMT slopes are negative; 36 remain
negative at their published upper 66% bound. These coefficients are a concrete
target for a matched GIVE baseline/pulse evaluation.

## Why it cannot yet be added

The endpoint is persistent GDP growth, not direct wind damage to a named asset
or welfare channel. It can implicitly contain agriculture, labor and health,
infrastructure and reconstruction, business interruption, migration, and
other recovery channels. Adding it to explicit GIVE sector damages could count
some of those consequences twice. It is also not additive to an aggregate
macro damage function such as DICE or Howard-Sterner.

Accordingly, the published result is admissible only as:

1. a non-additive external evidence benchmark;
2. a mutually exclusive macro-growth sensitivity case; or
3. a target for future channel decomposition.

It is not admissible as another line item in the combined GIVE SCC.

## Shortest path to a GIVE-compatible result

The next computation should apply the published country GMT-growth coefficients
to matched GIVE baseline and pulse GMT and country socioeconomic paths. It must
preserve coefficient-draw dependence, compute annual country GDP differences,
reconcile country and global totals, harmonize the 2025 pulse and 2005-to-2020
currency units, and take paired differences before quantiles.

That run should be reported as a mutually exclusive tropical-cyclone macro
sensitivity unless one of two additional evidence paths succeeds:

- decompose the growth response into channels and remove all agriculture,
  labor/health, infrastructure, and migration overlap; or
- replace the broad growth endpoint with direct wind asset/resource losses
  from a global catastrophe model, excluding surge, rainfall, transfers, and
  already represented infrastructure.

The machine-readable contract and tests fail closed if a headline SCC,
difference of medians, or overlapping macro result is promoted as additive.
