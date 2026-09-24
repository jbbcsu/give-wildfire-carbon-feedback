# Iroquois author-boundary aggregation diagnostic

## New source recovery

The authors' public replication files contain a GADM2-derived impact-region
polygon point frame and hierarchy crosswalk. The hierarchy uniquely maps
Iroquois County, Illinois to impact region `USA.14.630` (GADM ID 204502), and
the point frame supplies its Robinson-projected boundary. This closes the
administrative-boundary and region-ID gaps identified in the earlier TIGER
diagnostic. It does **not** recover the SAGE “anycrop” pixel weights used to
aggregate weather within that boundary.

The source administrative crop-weight table reports 133,723.93 for maize in
`USA.14.630`. Applying fixed-2000 MIRCA maize area to the author boundary gives
132,256.26 ha, only 1.10% lower. This agreement is an external spatial-support
check; it does not prove that MIRCA reproduces the within-region SAGE weights.

## Weather-feature comparison

The author polygon intersects the same six 0.5-degree GSWP3-W5E5 cells as the
2019 TIGER polygon. As before, Snyder temperature exposure and monthly linear
and squared rainfall terms are calculated inside each grid cell before fixed
spatial aggregation. Two variants were specified: equal-area polygon overlap
and MIRCA-maize-weighted overlap.

| Feature and metric | Author-boundary area | Author-boundary MIRCA maize |
|---|---:|---:|
| Season mean Tmax bias (C) | +0.351 | +0.351 |
| Season mean Tmax correlation | 0.942 | 0.942 |
| GDD bias | +74.93 | +74.94 |
| GDD RMSE | 79.43 | 79.45 |
| GDD correlation | 0.959 | 0.959 |
| KDD bias | +7.64 | +7.64 |
| KDD RMSE | 10.14 | 10.14 |
| KDD correlation | 0.969 | 0.969 |
| Season rainfall bias (mm) | +1.25 | +0.84 |
| Season rainfall RMSE (mm) | 88.85 | 88.96 |
| Season rainfall correlation | 0.771 | 0.771 |
| Late-phase rainfall correlation | 0.871 | 0.872 |
| Late-phase squared-rain correlation | 0.817 | 0.818 |

Using the author boundary marginally improves the county-area result from the
TIGER diagnostic: seasonal-rain RMSE falls from 89.03 to 88.85 mm and
correlation rises from 0.770 to 0.771. The principal gap is therefore not the
administrative boundary. Weather-product differences and unrecovered SAGE
within-region weights remain confounded. As in the earlier comparison, KDD RMSE
is slightly worse than the nearest-cell value and is not optimized away.

## Reproducibility and claim boundary

`scripts/extract_hultgren_impact_region.R` extracts the ignored eight-point
Iroquois ring from the hash-locked public FST. The bounded Python diagnostic is
`scripts/diagnose_hultgren_iroquois_author_boundary.py`; its receipt is
`data/provenance/hultgren_iroquois_author_boundary_diagnostic_20260923.json`.
The receipt binds the source FST, hierarchy, extracted ring, administrative
crop-weight table, MIRCA rasters, six cell overlaps, comparisons, and claim
gates.

This closes source administrative geometry and crosswalk gates. It does not
reproduce GMFD, recover SAGE pixel weights, validate future climate transport,
estimate damages, or authorize an SCC calculation.
