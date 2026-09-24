# Preliminary GFDL late-century maize response transport

## Purpose and claim boundary

This diagnostic asks how the published Hultgren et al. (2025) maize response
function evaluates a validated, crop-calendar-aligned GFDL-ESM4
SSP5-8.5-minus-SSP1-2.6 weather contrast for harvest years 2092--2100. It is a
published-coefficient transport benchmark. It is **not** a new causal response
estimate, an anthropogenic attribution, a monetary damage estimate, a marginal
emissions-pulse calculation, or an SCC result.

## Inputs and validation

- Daily ISIMIP3b GFDL-ESM4 precipitation, minimum temperature, and maximum
  temperature were transformed separately on rainfed and irrigated GGCMI maize
  calendars. Nonlinear rainfall and temperature bases were formed before fixed
  MIRCA-OS v2 area aggregation.
- All four scenario-by-regime weather bases pass independent selected-cell
  recomputation from raw daily sources. Rainfed and irrigated area totals are
  103.071 and 28.690 million eligible hectares.
- Fixed historical moderators use 27 retained GSWP3-W5E5 harvest years during
  1982--2010. Years 1991 and 2001 are excluded rather than silently spliced
  across separate source blocks. Fifty-four deterministic raw-daily
  recomputations agree exactly with the stored cell-year values.
- Country labels prioritize a unique MAPSPAM crop-location proxy and use the
  dominant author-region country only where that proxy is unavailable. The two
  assignments agree on 99.642% of their common crop area. Country-level Penn
  World Table output-side real GDP per person covers 98.947% of eligible maize
  area; missing countries are excluded without income imputation.
- The response is the source-reproduced 49-term Hultgren maize estimate and
  full published covariance matrix. The historical regression has 412,282
  complete observations.
- All jobs used one worker. The final full-support response run peaked at
  511.6 MB sampled process-group RSS under a 768 MiB guard.

## Validated physical contrast

Values below are fixed-area, area-year-weighted means over 2092--2100.

| Quantity | SSP1-2.6 | SSP5-8.5 | Difference |
|---|---:|---:|---:|
| Growing-season precipitation (mm) | 680.443 | 616.784 | -63.659 (-9.36%) |
| Phase 1 precipitation (mm) | — | — | -8.727 |
| Phase 2 precipitation, months 2--4 (mm) | — | — | -46.366 |
| Phase 3 precipitation, month 5--harvest (mm) | — | — | -8.566 |
| Monthly concentration | 0.27064 | 0.28331 | +0.01267 (+4.68%) |
| GDD 8--31 C | — | — | +454.393 (+18.19%) |
| KDD above 31 C | — | — | +129.837 (+234.36%) |

This physical result uses one climate model, one realization, two scenarios,
and nine late-century harvest years. It is not a probability-weighted climate
projection. Annual rainfall differences range from negative to positive, so
the pooled decrease does not imply every year or location becomes drier.

## Fixed-practice response benchmark

The primary estimand is the fixed-practice, fixed-area mean log-yield contrast.
The percent column is `100 * expm1(mean log contrast)`. Standard errors
propagate the published coefficient covariance only.

| Analysis support | Eligible area retained | Joint climate | Precipitation | Total-quantity path | Timing/distribution residual |
|---|---:|---:|---:|---:|---:|
| Full observed-income support | 98.95% | -37.31% (SE 0.0830 log points) | -3.57% (0.00629) | -2.93% (0.00546) | -0.66% (0.00259) |
| All moderators within author min--max | 72.17% | -24.99% (0.0949) | -3.03% (0.00441) | -2.95% (0.00426) | -0.08% (0.00177) |
| All moderators within author p01--p99 | 48.16% | -33.12% (0.0841) | -2.94% (0.00424) | -2.95% (0.00404) | +0.02% (0.00204) |

The key robustness finding is qualitative and numerical: the total-rainfall
quantity component stays near a 2.95% loss across all three moderator-support
definitions, whereas the timing/distribution residual changes from -0.66% to
approximately zero. The evidence-led specification hierarchy therefore treats
total quantity as the preliminary signal and within-season distribution as an
unstable sensitivity. This does not show that timing is biologically
irrelevant; it shows that this transported empirical contrast does not yet
support a robust global timing-damage claim.

The much larger joint result is temperature-driven and sensitive to moderator
support. It should not be used as a global damage estimate. Although nearly all
weather values remain inside the historical sample minimum--maximum, only
56.1% of SSP5-8.5 area-year KDD values lie inside the historical p01--p99
range. Country-level PWT income is also outside the authors' historical income
minimum--maximum over 26.2% of analyzed area. These are material transport
limitations.

## Quantity and distribution decomposition

For each cell-year with positive rainfall in both scenarios, the quantity-only
path uniformly rescales the SSP1-2.6 monthly rainfall distribution until its
season total equals SSP5-8.5. Phase-linear terms scale by the total ratio and
monthly-square terms by its square. The distribution residual is the actual
SSP5-8.5 precipitation response minus this reference-distribution path.

This split is path-dependent, not uniquely causal. Common-positive rainfall
support covers more than 99.99% of income-matched area-years. The stored
design-matrix identity has maximum relative numerical error `1.31e-16`, and
the corresponding log-response identity has maximum error `3.65e-14`.

## Adaptation sensitivities

`fixed` leaves the cell response unchanged. `trend` and `upper` attenuate only
negative cell log-yield responses at 0.3% and 0.7% per year after 2020, capped
at 35% and 70%; nonnegative responses are unchanged. These are transparent
scenarios, not empirical adaptation estimates, and adaptation costs remain
zero pending calibration.

| Full-support scenario | Joint climate | Precipitation | Quantity | Distribution |
|---|---:|---:|---:|---:|
| Fixed | -37.31% | -3.57% | -2.93% | -0.66% |
| Trend | -29.12% | -1.95% | -1.72% | +0.20% |
| Upper | -16.51% | +0.26% | -0.08% | +1.36% |

Because loss-only attenuation is applied separately to each cell and
component, adapted component means need not add to the adapted joint mean.
The sign reversal under the upper scenario reflects unchanged modeled benefits
plus attenuated losses; it is a warning about the scenario rule and spatial
heterogeneity, not evidence that adaptation will create a global rainfall
benefit.

## Remaining gates

1. Repeat the response transport across the registered five-ESM, three-SSP
   daily matrix and additional time windows; the one-GFDL result cannot be the
   publication estimate.
2. Resolve or replace the country-level income and fixed historical-climate
   moderator approximation; at minimum retain the support-restricted results.
3. Add crop production/value weights, other major crops, CO2 treatment, and
   an explicit welfare mapping before reporting monetary agricultural damages.
4. Evaluate matched GIVE baseline and marginal-pulse climate paths. A scenario
   difference is not an SCC perturbation.
5. Propagate climate-model, weather-product, moderator, adaptation, valuation,
   and structural uncertainty in addition to coefficient covariance.

Machine-readable results are in
`data/provenance/hultgren_gfdl_grid_yield_transport_20260924.json` and its two
support sensitivities. Independent summary validation is in
`data/provenance/hultgren_gfdl_grid_yield_transport_validation_20260924.json`.
