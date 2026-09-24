# Preliminary four-model late-century maize response transport

This diagnostic transports the published Hultgren et al. (2025) maize
response over crop-calendar-aligned GFDL-ESM4, IPSL-CM6A-LR,
MPI-ESM1-2-HR, and MRI-ESM2-0 SSP5-8.5-minus-SSP1-2.6 weather for harvest
years 2092--2100. It is a published-coefficient benchmark, not a new causal
estimate, monetary damage estimate, marginal pulse calculation, or SCC.

All 16 ESM-by-scenario-by-irrigation-regime bases pass independent selected-
cell recomputation from raw daily ISIMIP3b precipitation, Tmin, and Tmax.
Fixed calendars, MIRCA area, historical moderators, country/income mapping,
response coefficients, and support restrictions are identical across ESMs.

## Physical contrasts

| ESM | Season precipitation (mm) | Monthly concentration | GDD 8--31 C | KDD above 31 C |
|---|---:|---:|---:|---:|
| GFDL-ESM4 | -63.66 | +0.01267 | +454.39 | +129.84 |
| IPSL-CM6A-LR | +14.23 | +0.00418 | +693.27 | +275.99 |
| MPI-ESM1-2-HR | +12.83 | +0.00903 | +509.35 | +116.62 |
| MRI-ESM2-0 | +10.46 | +0.00077 | +453.29 | +126.74 |

The season-total sign differs, so these rows cannot be read as a common
global drying projection. They are named single-realization scenario
contrasts, not probabilities.

## Fixed-practice yield-response benchmark

Percent changes are transformations of area-weighted mean log-yield
contrasts.

| Support | Component | GFDL | IPSL | MPI | MRI |
|---|---|---:|---:|---:|---:|
| Full | Precipitation | -3.57% | -3.00% | -2.58% | -1.61% |
|  | Quantity path | -2.93% | -2.58% | -4.17% | -1.98% |
|  | Distribution residual | -0.66% | -0.43% | +1.66% | +0.38% |
| Author min--max | Precipitation | -3.03% | -2.48% | -2.56% | -1.93% |
|  | Quantity path | -2.95% | -2.23% | -4.91% | -2.70% |
|  | Distribution residual | -0.08% | -0.25% | +2.46% | +0.79% |
| Author p01--p99 | Precipitation | -2.94% | -1.58% | -2.90% | -1.18% |
|  | Quantity path | -2.95% | -2.09% | -5.85% | -1.84% |
|  | Distribution residual | +0.02% | +0.52% | +3.13% | +0.66% |

All 12 quantity-path estimates are negative (-1.84% to -5.85%). The
distribution residual changes sign across ESMs and support definitions. The
simple four-model full-support mean is -2.69% for net precipitation, -2.92%
for quantity, and +0.23% for distribution. It is descriptive, not a
probability-weighted estimate or uncertainty interval.

The robust conclusion is therefore qualitative: quantity is the replicated
precipitation signal; timing/distribution is material in some cases but not
sign-stable. The decomposition is reference-path dependent and does not
identify causal timing effects.

Fixed, trend, and upper adaptation sensitivities are retained in every source
record. Coefficient-only uncertainty excludes climate, transport, adaptation,
valuation, and structural uncertainty. One registered ESM, other crops,
production/value weights, welfare mapping, and matched GIVE marginal-pulse
evaluation remain before any monetary damage or SCC claim.

Machine-readable inputs and results are under `data/provenance/`, including
`hultgren_four_esm_grid_yield_transport_summary_20260924.json`.
