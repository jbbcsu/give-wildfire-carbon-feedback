# Hultgren rice historical transport preflight

Date: 2026-09-25

## Result

The weight-free first/main-rice (`ri1`) historical weather preflight is
implemented and independently validated for the GGCMI `ri1_noirr` and
`ri1_firr` calendar branches. It covers 27 harvest years (1982--1990,
1992--2000, and 2002--2010) on local GSWP3-W5E5 daily precipitation, minimum
temperature, and maximum temperature.

Each branch contains 272,808 complete cell-years: 10,104 cells in each of 27
years. The outputs contain the published rice weather primitives—GDD from
14--30 C, KDD above 30 C, summed monthly mean Tmin, and linear plus
monthly-square precipitation terms for the 2/3/remainder phases. No area,
production, value, welfare, damage, or SCC field is present.

The broad annual MIRCA Rice irrigated and rainfed rasters are used only as a
Boolean positive-rice support mask. Their magnitudes are neither emitted nor
used as weights. Of 21,968 positive-rice cells with finite `ri1` calendars,
10,104 (45.99%) meet the implemented source-compatible 6--12-month season
rule. The remaining 11,864 cells have 3--5-month calendars and are excluded
rather than coerced into the published phase structure.

## Branch diagnostic

The two local GGCMI `ri1_noirr` and `ri1_firr` calendar files are exactly
identical on the retained support. All 272,808 paired cell-years have identical
planting month, harvest month, season length, and weather primitives. These
files therefore do not provide an irrigation-calendar sensitivity for `ri1`.
The two ledgers remain separate so this fact is explicit and no unsupported
branch aggregation is introduced.

## Validation

The validator loaded the source-validated 46-term published rice estimate and
confirmed that its complete weather-primitive contract matches the emitted
basis. It did not evaluate the response because cell moderators and the source
rice estimation-sample domain are not available on this season-separated
support.

Six direct checks—one for each decade/branch file—reconstructed sampled rows
from the daily NetCDF inputs through the independent scalar implementation in
`src/hultgren_rice_weather.py`. The maximum absolute discrepancy was
`1.14e-13`.

The streaming builder's representative full-decade memory probe peaked at
203,161,600 bytes. The independently measured paired validator peaked at
433,504,256 bytes. Both are below the preregistered 512 MiB ceiling of
536,870,912 bytes.

Validation receipt:
`data/provenance/hultgren_rice_historical_preflight_validation_20260925.json`.
Cell-level paired diagnostics:
`data/interim/hultgren_rice_historical_preflight_20260925/ri1_calendar_branch_cell_diagnostics.parquet`.

## Gates that remain closed

- The historical Hultgren rice estimation sample is not locally available, so
  author min/max or percentile application-domain coverage cannot be assessed.
- The source's India-specific reporting-year exception is not applied because
  this weather-only grid preflight has no validated cell-country crosswalk.
- MIRCA season reconciliation remains blocked; these annual rasters cannot
  allocate rice among `ri1`, `ri2`, and Rice3.
- No cell response, branch average, global weighted response, damage estimate,
  or SCC is reported.
