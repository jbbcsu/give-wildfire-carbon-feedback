# Protocol: GFDL late-century Hultgren weather-basis contrast

Date frozen: 2026-09-23

## Estimand

The first future benchmark compares Hultgren maize weather-basis features under GFDL-ESM4 SSP5-8.5 versus SSP1-2.6 for physical harvest years 2092–2100. Holding the climate model, bias-adjustment product, crop calendar, crop area, and harvest years fixed isolates a within-model scenario contrast. It does not isolate a causal precipitation effect, because temperature and precipitation both differ between scenarios and internal variability remains in the nine-year window.

## Inputs

- ISIMIP3b bias-adjusted GFDL-ESM4 member `r1i1p1f1`, W5E5, daily global `pr`, `tasmin`, and `tasmax`, 2091–2100.
- Scenarios SSP1-2.6 and SSP5-8.5.
- GGCMI Phase 3 2015-society maize calendars, separately `mai_noirr` and `mai_firr`.
- MIRCA-OS v2 maize 2000 rainfed and irrigated harvested areas.

The preceding source year is retained so cross-year crop seasons ending in 2092 are complete. Exact extrema URLs, byte counts, SHA-512 values, DOI `10.48364/ISIMIP.842396.1`, version `20210512`, and CC0 rights are frozen in `data/provenance/isimip3b_five_esm_late_drought_extrema_20260921.json`. Precipitation identities remain bound in their existing acquisition receipts.

## Transformations and outputs

Each scenario is processed separately for rainfed and irrigated maize using `scripts/build_hultgren_grid_weather_basis.py`. The builder streams one day at a time, applies Snyder Tmin–Tmax degree-day integration, constructs crop-season phase rainfall totals and sums of squared monthly rainfall at grid-cell level, and writes one harvest year per Parquet row group.

The comparison reports area-weighted scenario levels and SSP5-8.5-minus-SSP1-2.6 changes in:

- GDD and KDD;
- total crop-season precipitation;
- precipitation totals in crop month 1, months 2–4, and month 5 through harvest;
- the sum of squared monthly precipitation;
- phase shares of crop-season precipitation; and
- scale-normalized monthly concentration, defined as the sum of squared monthly precipitation divided by squared crop-season total.

Thus total water quantity and within-season timing/distribution are both retained. Distribution measures are not presumed to improve agricultural prediction; their later response role remains governed by the pre-specified incremental out-of-sample evidence gate.

## Validation

Each of the four bases must pass source, grid, units, chronology, crop support, finiteness, completeness, and row-count gates. The independent validator will recompute distributed same-year and cross-year cell-years directly from the raw daily files using the scalar implementation. Scenario comparison is allowed only after both scenarios have identical cell/year/calendar/area support within a regime.

Rainfed and irrigated contrasts are reported separately. A combined agricultural contrast requires an explicit irrigation-weighting/adaptation assumption and is not part of this transformation step.

## Resource and retention controls

Only one numerical worker runs at a time under the 512 MiB sampled-RSS ceiling, 64 MiB owned-output target, and 130 GiB free-disk floor. One `tasmin`/`tasmax` pair is reacquired and hash-verified at a time. After both regime outputs and independent validations are complete, the raw extrema pair may be deleted with a receipt binding the reproducible public source identities and retained outputs.

## Claim gates

This comparison may support statements about an alternative-product, one-model late-century weather-basis contrast. It may not be described as:

- the observed relationship between climate change and precipitation;
- an exact GMFD/SAGE or NEX-GDDP reproduction;
- a causal precipitation-only yield effect;
- a global agricultural damage estimate; or
- an SCC estimate.

Those claims require, respectively, broader model/scenario evidence, response-function application with validated spatial moderators, monetary aggregation, and GIVE pulse-minus-baseline integration.
