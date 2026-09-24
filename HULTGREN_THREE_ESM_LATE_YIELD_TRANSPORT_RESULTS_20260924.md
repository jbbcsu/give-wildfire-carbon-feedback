# Preliminary three-model late-century maize response transport

## Purpose and claim boundary

This diagnostic transports the published Hultgren et al. (2025) maize
response over crop-calendar-aligned GFDL-ESM4, IPSL-CM6A-LR, and
MPI-ESM1-2-HR SSP5-8.5-minus-SSP1-2.6 weather contrasts for harvest years
2092--2100. It is a published-coefficient benchmark, not a new causal response
estimate, anthropogenic attribution, monetary damage estimate, marginal pulse
calculation, or social cost of carbon result.

## Validated inputs

Each ESM uses one ISIMIP3b realization and daily precipitation, minimum
temperature, and maximum temperature. Rainfed and irrigated GGCMI maize
calendars are transformed separately before fixed MIRCA-OS v2 area
aggregation. All 12 ESM-by-scenario-by-regime bases pass independent
selected-cell recomputation from raw daily sources. Fixed historical
moderators, country assignment, income coverage, response coefficients, and
support restrictions are identical across ESMs. Large temperature inputs were
deleted only after both regime validations passed; checksum-bound recovery
receipts and the compact bases remain.

## Physical weather contrasts

Fixed-area, area-year-weighted differences over 2092--2100 are:

| ESM | Season precipitation (mm) | Monthly concentration | GDD 8--31 C | KDD above 31 C |
|---|---:|---:|---:|---:|
| GFDL-ESM4 | -63.66 (-9.36%) | +0.01267 | +454.39 | +129.84 |
| IPSL-CM6A-LR | +14.23 (+2.11%) | +0.00418 | +693.27 | +275.99 |
| MPI-ESM1-2-HR | +12.83 (+1.92%) | +0.00903 | +509.35 | +116.62 |

Season-total changes do not share a sign, while concentration rises in all
three. Each row is one realization and one scenario contrast, not a
probability-weighted climate projection.

## Fixed-practice published-response benchmark

Percent values equal `100 * expm1(mean log-yield contrast)`.

| Moderator support | Component | GFDL | IPSL | MPI |
|---|---|---:|---:|---:|
| Full (98.95% area) | Joint climate | -37.31% | -66.32% | -39.11% |
|  | Precipitation | -3.57% | -3.00% | -2.58% |
|  | Total-quantity path | -2.93% | -2.58% | -4.17% |
|  | Timing/distribution residual | -0.66% | -0.43% | +1.66% |
| Author min--max (72.17%) | Precipitation | -3.03% | -2.48% | -2.56% |
|  | Total-quantity path | -2.95% | -2.23% | -4.91% |
|  | Timing/distribution residual | -0.08% | -0.25% | +2.46% |
| Author p01--p99 (48.16%) | Precipitation | -2.94% | -1.58% | -2.90% |
|  | Total-quantity path | -2.95% | -2.09% | -5.85% |
|  | Timing/distribution residual | +0.02% | +0.52% | +3.13% |

All nine model-by-support quantity estimates are negative and span -2.09% to
-5.85%. The distribution residual changes sign across ESMs and support
definitions. MPI is especially informative: a comparatively small positive
season-total change still produces a negative quantity-path response because
uniform rescaling acts on nonlinear, stage-specific rainfall terms; an
offsetting positive distribution residual then leaves a -2.58% net
precipitation response. The decomposition is reference-path dependent, not a
unique causal attribution.

The evidence-led hierarchy is therefore stronger after the third ESM:
seasonal quantity is the replicated precipitation signal; within-season
timing/distribution remains a material but non-robust sensitivity. This does
not imply timing is biologically irrelevant.

The simple equal-model full-support mean is -3.05% for precipitation, -3.23%
for quantity, and +0.18% for the distribution residual. These arithmetic
means are descriptive summaries of three named models, not ensemble weights,
uncertainty intervals, or probabilities. Joint losses are temperature-driven,
highly exposed to late-century KDD extrapolation, and not headline-ready
damage estimates.

## Adaptation, uncertainty, and remaining gates

Fixed, trend, and upper adaptation scenarios are all retained. Trend and upper
attenuate only negative cell log-yield responses by 0.3% and 0.7% per year
after 2020, capped at 35% and 70%; modeled benefits are unchanged. These are
transparent sensitivity rules, not empirically estimated adaptation.

Coefficient-only uncertainty excludes climate-model spread, transport,
moderators, adaptation, crop area, valuation, and structural uncertainty.
Two registered ESMs, other major crops, production/value weights, agricultural
welfare mapping, and matched GIVE marginal-pulse evaluation remain required
before reporting monetary damages or SCC.

Machine-readable results are in the model-specific
`data/provenance/hultgren_*_grid_yield_transport*_20260924.json` files and
`data/provenance/hultgren_three_esm_grid_yield_transport_summary_20260924.json`.
