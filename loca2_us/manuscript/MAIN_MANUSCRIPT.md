# High-resolution precipitation change and U.S. agricultural risk

## Status

Study-design manuscript. The official source audit, bounded point-access
pilot, Cuming County geometry aggregation, and first single-model historical
climate-distribution sentinel pass. Multi-county and multi-model climate
validation remain open. No crop-response, causal, damage, or SCC result is
claimed.

## Research question

How do climate-driven changes in crop-season rainfall quantity, timing, dry
spells, and extremes affect U.S. county crop outcomes, and how do those effects
differ between irrigated and non-irrigated production?

## Contribution

The paper will combine an irrigation-stratified NASS county outcome design
with daily, approximately 6-km CMIP6-LOCA2 climate projections. Its novelty is
not the existence of downscaled projections. It is the outcome-blind,
crop-calendar translation of daily projected weather into competing moisture
representations, their validation against an independent historical gridded
weather pipeline, and transparent separation of predictive, causal, welfare,
and SCC claims.

## Planned design

The quantity-only model is the parsimonious reference. Distribution, dry-spell,
and extreme-rain features are promoted only if they add stable out-of-sample
value across prespecified temporal, geographic, and climate-model holdouts.
PDSI/SPEI form a competing moisture family rather than additive damage terms.
All specifications retain common temperature controls. Irrigated and
non-irrigated outcomes are estimated separately, with all-practice outcomes as
a secondary coverage benchmark.

Historical LOCA2 features will first be compared with NOAA nClimGrid-Daily on
fixed common counties and years. Future projections use equal GCM weights and
preserve model, member, and scenario identity. No climate model is weighted
using crop outcomes.

## Relationship to GIVE

This is a distinct U.S. paper and validation track. Any eventual SCC transport
would require a stable causal response, an explicit marginal climate
counterfactual, irrigation/adaptation welfare mapping, and overlap accounting.
The global precipitation-agriculture extension continues to use its separate
ISIMIP/GIVE pathway.

## Current engineering evidence

The official USGS daily stores expose 1950--2014 historical and 2015--2100
future data, with daily precipitation, minimum temperature, and maximum
temperature. The audited precipitation field is LOCA2 `v20240915`. A fixed
92-day, one-point, one-member pilot read all three variables from 57.46 MiB of
compressed cloud chunks while peaking at 278.19 MiB RAM. This demonstrates a
storage-bounded access route only; it supplies no county or agricultural
effect estimate.

A first climate-only county sentinel aggregates 63 LOCA2 cells over Cuming
County and compares 12 fixed corn seasons with nClimGrid. For GFDL-ESM4,
season rainfall is 29.44 mm lower, maximum dry spell is 4.03 days longer,
Rx5day is 0.43 mm lower, and mean season temperature is 0.89 C higher on
average. These product differences are not paired-year forecast errors and
cannot be generalized beyond the single model, county, and period. They
motivate the preregistered multi-model and multi-county climate validation
before any outcome fit.

| Climate feature | LOCA2 mean | nClimGrid mean | LOCA2 minus nClimGrid | SD ratio | Quantile RMSE |
|---|---:|---:|---:|---:|---:|
| Season precipitation (mm) | 432.15 | 461.58 | -29.44 | 0.931 | 60.02 mm |
| Maximum dry spell (days) | 22.22 | 18.19 | +4.03 | 0.870 | 4.52 days |
| Rx5day (mm) | 84.24 | 84.67 | -0.43 | 0.953 | 5.84 mm |
| Season mean temperature (C) | 20.29 | 19.41 | +0.89 | 0.750 | 0.82 C |

The source receipt is independently reconciled over 400 saved arithmetic and
support checks with zero saved-precision disagreement. The 2001--2014
validation block remains closed because the outcome-keyed nClimGrid feature
panel lacks Cuming-corn rows for 2013--2014; the successful sentinel therefore
uses continuous 2001--2012 support. Remote variables were decoded one at a
time, yielding a sampled process-group peak of 484,589,568 bytes (462.14 MiB),
below the 512 MiB guard.
