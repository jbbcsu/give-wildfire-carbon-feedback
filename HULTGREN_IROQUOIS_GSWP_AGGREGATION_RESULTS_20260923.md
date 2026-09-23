# Iroquois multi-cell aggregation diagnostic

## Purpose and claim boundary

This diagnostic asks whether replacing the single GSWP3-W5E5 cell with an
explicit county spatial support materially changes the comparison with the
published Iroquois County maize features. It is **not** an exact replication:
[Hultgren et al. (2025)](https://doi.org/10.1038/s41586-025-09085-w) used GMFD
weather and SAGE any-crop weights, whereas the resident implementation uses
GSWP3-W5E5 weather and prespecified TIGER-area or MIRCA-maize proxy weights.

Following the paper's Supplementary Information, Snyder temperature exposures
and monthly linear and squared precipitation variables are calculated in every
grid cell first. Fixed spatial weights are applied only after these nonlinear
transformations. This order matters, especially for squared rainfall.

## Spatial support

The 2019 Census TIGER boundary for Iroquois County (GEOID 17075) intersects six
0.5-degree cells. The intersection areas cover 100.0000% of the projected
county polygon; the central cell at 40.75 N, 87.75 W holds 76.68% of county
area. We specified three alternatives before reading results:

1. the dominant/nearest cell, reproducing the earlier diagnostic;
2. EPSG:5070 county-polygon intersection-area weights; and
3. fixed-2000 [MIRCA-OS v2](https://doi.org/10.1038/s41597-024-04313-w)
   maize hectares multiplied by each cell's county-overlap fraction.

The MIRCA alternative is maize-specific and therefore informative, but it does
not reproduce the paper's SAGE any-crop weights. The implied within-county
maize-area proxy is 131,783 ha and its irrigated share is 0.55%; both figures
are raster-based spatial proxies, not county statistics or estimation targets.

## Ten-year comparison, 1981--1990

| Feature and metric | Nearest cell | County-area weighted | MIRCA-maize weighted |
|---|---:|---:|---:|
| Season mean Tmax bias (C) | +0.353 | +0.355 | +0.354 |
| Season mean Tmax correlation | 0.933 | 0.941 | 0.942 |
| GDD bias (degree-days) | +75.87 | +75.33 | +75.25 |
| GDD RMSE | 80.64 | 79.84 | 79.76 |
| GDD correlation | 0.956 | 0.958 | 0.958 |
| KDD bias (degree-days) | +7.49 | +7.65 | +7.65 |
| KDD RMSE | 9.92 | 10.15 | 10.15 |
| KDD correlation | 0.969 | 0.969 | 0.969 |
| Season rainfall bias (mm) | +5.84 | +1.27 | +0.88 |
| Season rainfall RMSE (mm) | 90.59 | 89.03 | 89.09 |
| Season rainfall correlation | 0.762 | 0.770 | 0.770 |
| Late-phase rainfall correlation | 0.818 | 0.870 | 0.871 |
| Late-phase squared-rain correlation | 0.735 | 0.816 | 0.817 |

The two multi-cell variants are nearly identical because their weights are
similar and the dominant cell covers most of the county. They modestly improve
temperature, seasonal-rainfall, and late-phase-rainfall comparisons. KDD RMSE
is slightly worse, which is reported rather than optimized away. These results
do not justify choosing a spatial method by fit: both alternatives remain
prespecified sensitivity cases until the source SAGE weights and GMFD primitive
weather can be recovered or independently reconstructed.

## Reproducibility and next gate

The machine-readable receipt is
`data/provenance/hultgren_iroquois_gswp_aggregation_diagnostic_20260923.json`.
It contains SHA-512 identities for the TIGER geometry components and both MIRCA
rasters, all six cell intersections and weights, the full comparison matrix,
and explicit validation and claim gates. The bounded run reads only May--October
1981--1990 for six cells, keeping peak memory compatible with the project's
512 MiB worker limit.

The next source-matching gate is acquisition or reconstruction of the paper's
GMFD daily weather and SAGE any-crop spatial weights. Until then, this result
validates the grid-first aggregation machinery on an alternative climate
product; it does not validate a future yield effect, damage estimate, or SCC.
