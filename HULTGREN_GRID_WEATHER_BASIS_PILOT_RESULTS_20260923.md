# Hultgren grid-weather basis pilot results

Date: 2026-09-23

## Result

The bounded implementation successfully transformed retained 1981–1990 GSWP3-W5E5 daily precipitation, minimum temperature, and maximum temperature into the published Hultgren maize weather basis for rainfed maize harvest years 1982–1990. The output has 267,750 cell-years (29,750 cells by 9 harvest years), 19 weather/support columns, nine Parquet row groups, and a 19,643,630-byte footprint.

This is a validated transformation pilot. It is not a yield-response estimate, a future climate-change effect, a damage estimate, or an SCC result.

## Numerical validation

The independent validator passed all schema, uniqueness, completeness, finiteness, and nonnegativity gates. It then recomputed 13 deliberately distributed cell-years—including same-year and cross-year seasons and the first, middle, and last harvest years—directly from the raw daily files using the previously validated scalar Snyder implementation.

The maximum absolute difference across GDD, KDD, the three linear precipitation phases, and the three squared-monthly-precipitation phases was `1.4551915228366852e-11`. This is floating-point summation noise, not a material discrepancy.

The immutable validation receipt is `data/provenance/hultgren_grid_basis_rainfed_pilot_validation_20260923.json`. The ignored 19 MB basis and builder receipt remain under `data/interim/hultgren_grid_basis_pilot_20260923/`.

## Support coverage

The rainfed MIRCA/GGCMI join contains 30,654 positive-area cells and 108,038,665.26 hectares. Applying the published 4–10 month growing-season restriction retains 29,750 cells and 103,070,991.61 hectares, or 95.4019% of matched positive area.

The excluded 4.5981% is entirely short-calendar support in this input: 37 two-month cells representing 143,314.29 hectares and 867 three-month cells representing 4,824,359.36 hectares. The implementation now records cell counts and hectares for every season length so this exclusion is explicit in future runs.

## Resource validation

- Builder: 46.03 seconds, sampled peak process-group RSS 333,873,152 bytes (318.41 MiB).
- Independent validator: 265.25 seconds, sampled peak process-group RSS 338,132,992 bytes (322.47 MiB).
- Both runs stayed below the 512 MiB worker ceiling and the 130 GiB free-disk floor.
- The builder writes one harvest year per Parquet row group, avoiding a multi-year Python-object accumulation.

The validator is slower than the builder because it independently rereads compressed raw daily histories for selected cells. That cost is acceptable for a gate and will not be multiplied across all cells.

## Descriptive quantities—not effects

Area-weighted annual weather-basis summaries are retained in the validation receipt as plausibility diagnostics. For example, across 1982–1990 the rainfed-support weighted phase totals and heat exposures vary from year to year. They must not be interpreted as climate-change effects or agricultural impacts because this pilot contains neither a counterfactual climate scenario nor an estimated response application.

## Next gate

The next defensible numerical step is a matched late-century within-ESM scenario contrast. Reacquire one pre-registered `tasmin`/`tasmax` pair at a time, verify its frozen byte count and SHA-512, build rainfed and irrigated bases separately under SSP1-2.6 and SSP5-8.5, independently validate them, and only then aggregate to impact regions and apply the published response. The published GMFD/SAGE historical reproduction gap remains separate and must not be silently treated as closed.
