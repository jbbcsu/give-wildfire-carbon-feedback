# Iroquois primitive-weather implementation diagnostic

## Why this diagnostic was run

The published maize coefficient vector cannot be applied to future weather
until the primitive climate transformation is reproduced. The Supplementary
Information specifies Snyder's continuous-time sinusoidal interpolation between
daily minimum and maximum temperature, with the temperature-time area
integrated between 8 and 31 C for GDD and above 31 C for KDD. Precipitation is
summed to grid-cell calendar months before the linear and squared monthly terms
are grouped into crop phases.

We implemented those rules and ran a bounded ten-year check for the paper's
Iroquois County example. The diagnostic compares the published 1981--1990
crop-weighted administrative-unit GMFD features with the resident GSWP3-W5E5
0.5-degree cell at 40.75 N, 87.75 W. Both the source calendar and the resident
GGCMI proxy calendar resolve to May--October.

## Results

| Feature | Published GMFD mean | GSWP cell mean | Mean difference | RMSE | Correlation |
|---|---:|---:|---:|---:|---:|
| Season mean Tmax (C) | 25.500 | 25.854 | +0.353 | 0.471 | 0.933 |
| GDD, 8--31 C | 2,114.38 | 2,190.25 | +75.87 | 80.64 | 0.956 |
| KDD, above 31 C | 8.17 | 15.65 | +7.49 | 9.92 | 0.969 |
| Season precipitation (mm) | 563.15 | 568.99 | +5.84 | 90.59 | 0.762 |
| Phase 1 precipitation (mm) | 116.43 | 117.17 | +0.74 | 32.58 | 0.700 |
| Phase 2 precipitation (mm) | 289.87 | 285.22 | -4.65 | 57.10 | 0.796 |
| Phase 3 precipitation (mm) | 156.85 | 166.60 | +9.75 | 34.27 | 0.818 |

The temperature levels and year-to-year movements are close despite the
different weather product and spatial support. The precipitation means are also
close, while year-specific errors are materially larger, as expected from a
single-cell/different-product comparison. Squared monthly-rainfall terms have
correlations of 0.566--0.735 and are especially sensitive to spatial averaging.

## Rejected construction

A preliminary implementation thresholded daily Tmax directly. The primary
source shows this is not the published method. The reproducible rejection check
also demonstrates the consequence: direct-Tmax GDD averaged 3,214 rather than
the published 2,114, and direct-Tmax KDD averaged 71.94 rather than 8.17. That
candidate is retained in the diagnostic receipt as rejected and cannot be used
for future projections.

## Claim boundary and next gate

This is an implementation diagnostic, not exact GMFD replication. The weather
product differs and a single 0.5-degree cell is not the paper's SAGE
any-crop-weighted administrative-unit aggregation. It therefore does not freeze
the grid-first versus administrative-unit-first choice, validate future yield
impacts, or authorize damages or SCC.

The next defensible step is a multi-cell administrative-area comparison using
the same Snyder and monthly-precipitation code, with explicit crop weights and
geometry. If the exact historical GMFD/SAGE inputs cannot be recovered, the
GSWP comparison remains a transport diagnostic and the paper's published
response must be presented as a benchmark with spatial-input uncertainty.

The machine-readable result is
`data/provenance/hultgren_iroquois_gswp_basis_diagnostic_20260923.json`.
