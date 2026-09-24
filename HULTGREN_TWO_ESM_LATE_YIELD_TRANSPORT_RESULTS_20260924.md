# Preliminary two-model late-century maize response transport

## Purpose and claim boundary

This diagnostic transports the published Hultgren et al. (2025) maize
response over crop-calendar-aligned GFDL-ESM4 and IPSL-CM6A-LR
SSP5-8.5-minus-SSP1-2.6 weather contrasts for harvest years 2092--2100.
It is a published-coefficient benchmark, not a new causal response estimate,
anthropogenic attribution, monetary damage estimate, marginal pulse
calculation, or social cost of carbon (SCC) result.

## Inputs and validation

- Each ESM uses one ISIMIP3b realization and daily precipitation, minimum
  temperature, and maximum temperature. Rainfed and irrigated GGCMI maize
  calendars are transformed separately before fixed MIRCA-OS v2 area
  aggregation.
- All eight model-by-scenario-by-regime weather bases pass independent
  selected-cell recomputation from raw daily sources. Builders and validators
  stayed below 341 MB sampled process-group RSS.
- The response is the source-reproduced 49-term Hultgren maize estimate with
  its full published covariance matrix. Fixed historical moderators, country
  assignment, income coverage, and support restrictions are identical across
  ESMs.
- Exact source identities, implementation hashes, support, and validation
  results are stored in `data/provenance/`. The raw daily extrema inputs were
  deleted only after validation and checksum-bound eviction receipts were
  written; the compact derived bases are retained locally.

## Physical weather contrasts

Fixed-area, area-year-weighted means over 2092--2100 differ materially across
the two ESMs:

| ESM | Season precipitation (mm) | Monthly concentration | GDD 8--31 C | KDD above 31 C |
|---|---:|---:|---:|---:|
| GFDL-ESM4 | -63.66 (-9.36%) | +0.01267 (+4.68%) | +454.39 | +129.84 |
| IPSL-CM6A-LR | +14.23 (+2.11%) | +0.00418 (+1.57%) | +693.27 | +275.99 |

Thus the sign of the area-weighted seasonal-total change is not common across
these ESMs even though both have greater monthly concentration. Each row is a
single-realization scenario contrast, not a probability-weighted projection.

## Fixed-practice published-response benchmark

The percent values below equal `100 * expm1(mean log-yield contrast)`.
Coefficient-only standard errors remain in the source records.

| Moderator support | Component | GFDL-ESM4 | IPSL-CM6A-LR |
|---|---|---:|---:|
| Full (98.95% of eligible area) | Joint climate | -37.31% | -66.32% |
|  | Precipitation | -3.57% | -3.00% |
|  | Total-quantity path | -2.93% | -2.58% |
|  | Timing/distribution residual | -0.66% | -0.43% |
| Author min--max (72.17%) | Precipitation | -3.03% | -2.48% |
|  | Total-quantity path | -2.95% | -2.23% |
|  | Timing/distribution residual | -0.08% | -0.25% |
| Author p01--p99 (48.16%) | Precipitation | -2.94% | -1.58% |
|  | Total-quantity path | -2.95% | -2.09% |
|  | Timing/distribution residual | +0.02% | +0.52% |

All six model-by-support quantity estimates are negative and span -2.09% to
-2.95%. By contrast, the distribution residual approaches zero or changes
sign on central support. This replication strengthens the evidence-led
hierarchy: seasonal quantity is the current robust precipitation signal;
timing/distribution remains a reported but non-robust sensitivity. It does
not establish that rainfall timing is biologically irrelevant.

The simple equal-model full-support mean is -3.29% for precipitation, -2.76%
for quantity, and -0.54% for the distribution residual. These arithmetic
means are descriptive summaries of two named models, not ensemble weights,
uncertainty intervals, or probabilities. Joint losses are much larger and
temperature-driven; they are highly exposed to extrapolation, especially for
late-century KDD, and are not headline-ready damage estimates.

## Adaptation and uncertainty

Fixed leaves cell responses unchanged. Trend and upper scenarios attenuate
only negative cell log-yield responses by 0.3% and 0.7% per year after 2020,
capped at 35% and 70%; nonnegative responses are unchanged. These are
transparent sensitivity rules, not empirically estimated adaptation, and
adaptation costs remain zero. Component means after loss-only attenuation are
not additive because the rule is applied separately to each component.

Reported standard errors propagate only the common published coefficient
covariance. They exclude climate-model spread, response transport,
moderators, adaptation, crop area, valuation, and structural uncertainty.

## Remaining gates

1. Complete the registered five-ESM response transport and additional time
   windows; two ESMs cannot define the publication ensemble.
2. Replace or bound the alternative income and historical-climate moderators.
3. Add other major crops and production/value weights, preserve irrigation,
   and map yield changes to agricultural welfare without double counting.
4. Evaluate matched GIVE baseline and marginal-pulse paths. A scenario
   difference is not an SCC perturbation.
5. Propagate climate, response, adaptation, valuation, and structural
   uncertainty before reporting monetary damages or SCC.

Machine-readable named-model results and the non-probabilistic summary are
`data/provenance/hultgren_{gfdl,ipsl}_grid_yield_transport*_20260924.json` and
`data/provenance/hultgren_two_esm_grid_yield_transport_summary_20260924.json`.
