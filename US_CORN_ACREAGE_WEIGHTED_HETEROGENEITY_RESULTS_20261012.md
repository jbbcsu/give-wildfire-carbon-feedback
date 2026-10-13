# Acreage-weighted U.S. corn heterogeneity diagnostic

## Result

The higher-resolution U.S. result is not small for reported non-irrigated
corn under the published MPI precipitation pattern. Reweighting the frozen
county-panel transport by 2017 Census of Agriculture harvested acres changes
the selected-sample response from -2.32%/K under equal-county weighting to
**-2.69%/K** (500 km spatial interval **-3.27% to -2.11%**) across 15.31
million non-irrigated acres. The corresponding irrigated estimate is +0.06%/K
(-0.12% to +0.24%) across 7.78 million irrigated acres.

This calculation requires observed, non-suppressed total and irrigated corn
area and therefore retains 300 counties in ten states. Suppressed irrigated
area is never interpreted as zero. The response coefficients remain those
estimated on the complete 361-county paired-practice panel; only the
aggregation weights and geographic support change.

## Climate-pattern uncertainty

| Monthly precipitation pattern | Non-irrigated acreage-weighted yield response per K | 500 km interval | Irrigated response per K |
|---|---:|---:|---:|
| Published MPI | -2.69% | -3.27% to -2.11% | +0.06% |
| Project GFDL fit | +0.29% | +0.21% to +0.37% | +0.05% |
| Project IPSL fit | -0.77% | -0.94% to -0.59% | -0.01% |

The climate-model pattern remains the dominant uncertainty. Only MPI is an
author-published PEEPS pattern; GFDL and IPSL are project-fitted structural
sensitivities and are not a probability-weighted ensemble.

## Within-U.S. heterogeneity

Under published MPI, the acreage-weighted non-irrigated response ranges from
-3.88%/K in North Dakota and -3.72%/K in South Dakota to -0.60%/K in Texas,
+0.11%/K in Delaware, and +0.33%/K in the single supported Oklahoma county.
The Oklahoma and New Mexico entries have only one acreage-complete county and
are not state-representative estimates. GFDL reverses several signs: Nebraska
is -0.95%/K while North Dakota is +2.19%/K and Texas +3.21%/K. IPSL is mostly
negative, with Colorado -1.95%/K and North Dakota -1.54%/K. This confirms that
the national mean masks economically meaningful spatial heterogeneity, but
also that the heterogeneity is conditional on uncertain precipitation
patterns.

## Claim boundary

This is an acreage-weighted selected-sample yield diagnostic, not a national
production effect, monetary damage, or SCC estimate. Acreage is fixed at the
2017 Census snapshot; it is not production or welfare weighting. The rainfall
response fails the preregistered strict leave-state and temporal-stability
gates, the support excludes several major Corn Belt states, and the monthly
patterns omit PDSI, daily dry spells, and extremes. These limitations are why
the result helps explain heterogeneity but is not yet promoted into GIVE.

## Reproduction

- `us_county_validation/scripts/build_us_corn_three_pattern_acreage_weighted.py`
- `data/provenance/us_corn_three_pattern_acreage_weighted_20261012.json`
- state and selected-sample table (gitignored):
  `data/interim/us_corn_three_pattern_acreage_weighted_20261012.csv`
