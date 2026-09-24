# Hultgren global region/grid crosswalk results

Date: 2026-09-23

## Result

A reproducible alternative-product crosswalk now links the 0.5-degree climate/crop grid to the authors' 24,376 public impact-region geometries. It contains 110,861 unique positive-intersection cell/region rows and maps 23,087 regions with positive MIRCA maize support. The ignored Parquet output is 8.19 MB; its hash and all source identities are frozen in `data/provenance/hultgren_impact_region_grid_crosswalk_validation_20260923.json`.

This closes the geometry-engineering gate for alternative ISIMIP/MIRCA transport. It does not recover the authors' SAGE `anycrop` pixel weights and therefore is not an exact reproduction.

## Method

The source FST point frame is converted losslessly to a compressed interchange table after enforcing 714,615 points, 24,376 region IDs, 27,005 rings, and the original schema. Source polygons are reconstructed in their native Robinson projection. Their calculated Robinson areas reproduce the stored polygon areas extremely closely: the full range of calculated/stored ratios is 0.999999456–1.000001317.

For crop weighting, polygons and 0.5-degree cells are transformed to global equal-area EPSG:6933. Exact positive-area intersections determine the fraction of each climate cell inside each impact region. Fixed MIRCA-OS v2 year-2000 rainfed and irrigated maize hectares are multiplied by this fraction and normalized separately within each region and irrigation regime. The largest within-region weight-sum error is `2.22e-16`.

## Mixed-resolution overlap

The author impact-region system contains mixed-resolution, partially overlapping regions. This is visible in the public hierarchy: some agglomerated regions coexist spatially with finer regions used by other source datasets. Consequently, 1,530 crop-support cells have summed intersection fractions above one, with a maximum of two. Treating the polygons as a mutually exclusive global partition would double count.

The implemented method therefore normalizes climate weights within each author region. It does not allocate the global MIRCA area across competing polygons. The authors' public region-level `corn` weights remain the appropriate candidate for later global aggregation because those weights sum across regions without reproducing geometric overlap.

## Validation

- All cell/region rows are unique, finite, and have positive intersection fractions no greater than one.
- Only 21 of 33,362 positive union-crop cells have no region intersection; they contain `3.96e-6` of global MIRCA maize area.
- The authors' global corn weight is 136.521 million, versus 137.021 million combined MIRCA maize hectares, a −0.365% difference.
- Across the 19,758 regions with positive values in both sources, the correlation between log-one-plus MIRCA within-region proxy and log-one-plus author corn weight is 0.819.
- The global builder independently recovers six Iroquois cells. Its combined maize proxy is 132,259.60 ha and irrigated share 0.55072%; relative to the earlier U.S.-Albers calculation, differences are `2.52e-5` in area and `1.25e-6` in irrigated share.
- The run used 371,720,192 bytes sampled peak group RSS (354.50 MiB), below the 512 MiB ceiling.

## Important limitation

Regional MIRCA/source-corn ratios are dispersed (median 1.21; 10th–90th percentiles 0.31–11.97, with still wider tails). MIRCA is therefore suitable here only as a transparent within-region spatial weighting proxy. It must not silently replace the authors' regional crop totals. Results require sensitivity to alternative within-region weights and, if obtainable, the original SAGE pixel weights.

No yield response, monetary damage, or SCC estimate is produced by this crosswalk.
