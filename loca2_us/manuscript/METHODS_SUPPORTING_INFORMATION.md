# Methods Supporting Information

## M1. Reproducibility state

The current release contains the preregistered source and validation design,
an official-catalog audit, and synthetic tests. It does not contain restricted
NASS credentials or raw climate arrays. Raw and interim files are ignored.

## M2. Climate sources

Daily CMIP6-LOCA2 historical and future data are accessed from the official
USGS Water Mission Area STAC Zarr assets. Required fields are precipitation,
daily minimum temperature, and daily maximum temperature. Precipitation must
identify LOCA2 version `v20240915`. Historical and future periods are
1950--2014 and 2015--2100; future scenarios are SSP2-4.5, SSP3-7.0, and
SSP5-8.5. Exact ensemble, source-model, experiment, and variant labels are
retained in every derived receipt.

## M3. County and crop-calendar features

The implementation reuses the semantic contract, not the arrays, of the
existing nClimGrid county pipeline. Features are first constructed at the
weather-grid/crop-calendar level and then aggregated. They include crop-season
precipitation, wet days, conditional wet-day intensity, maximum consecutive
dry days, Rx1day, Rx5day, normalized three-stage shares, precipitation timing
centroid and concentration, stage mean temperature, and heat accumulation.
Stage precipitation must sum to the season total within saved precision.

## M4. Ensemble structure and holdouts

Primary aggregation is equal across GCMs and equal across variants within a
GCM. All variants and scenarios from one `source_id` are assigned together to
one of five folds using the first eight hexadecimal characters of
`sha256(source_id)` modulo five. This grouping is frozen before outcome access.
Historical climate calibration diagnostics use 1981--2000; fixed temporal
validation uses 2001--2014.

## M5. Historical climate validation

LOCA2 historical features are evaluated against the existing NOAA
nClimGrid-Daily county feature pipeline on a predeclared common sample. Metrics
include bias, RMSE, correlation, trend difference, quantile error, dry-spell
error, and Rx5day error. TIGER 2019 versus TIGER 2023 boundary differences are
crosswalked and reported; no silent GEOID coercion is allowed.

The first geometry sentinel uses the same TIGER 2019 Cuming County polygon as
the nClimGrid pipeline. LOCA2 cell edges are inferred from the regular
one-dimensional coordinates, transformed with the county to EPSG:5070, and
intersected exactly. Sixty-three cells have positive intersection. Coverage,
declared-area reconciliation, unique cell keys, and weight sum are fail-closed
checks. This stage uses coordinate metadata only and does not establish
weather validity.

Historical CMIP6 simulations are free-running realizations, so their year
ordering is not treated as a prediction of observed annual weather. Validation
therefore compares fixed-period means, standard deviations, and quantiles; it
does not report paired-year correlation or RMSE. The first sentinel uses the
continuous 2001--2012 support available in the existing outcome-keyed
nClimGrid feature panel. The intended 2001--2014 gate remains closed until
2013--2014 are reconstructed independently of outcome availability.

Nonlinear bases are constructed per LOCA2 cell before county area weighting,
matching the nClimGrid operation order. Precipitation totals, wet-day counts,
maximum dry spells, Rx1day, Rx5day, three stage totals/shares, concentration,
timing centroid, and temperature summaries are then compared on identical
calendar windows. Remote variables are decoded sequentially to respect the
512 MiB memory guard.

## M6. Agricultural response families

The response stage remains closed. When authorized, the primary quantity
family, quantity-plus-distribution family, and drought-index family will be
fit and evaluated on identical support. Drought indices are competitors, not
additional causal channels. Temperature controls are common. Promotion
requires stable blocked out-of-sample improvement and sign/domain checks;
nulls and degradation are reported.

## M7. Irrigation and adaptation

Direct non-irrigated and irrigated NASS outcomes are primary where coverage is
adequate. All-practice outcomes are secondary. Future adaptation cases remain
fixed, trend, and upper scenarios. LOCA2 does not identify irrigation adoption
or water availability, so neither is inferred from climate fields alone.

## M8. Claim controls

Climate projections are not crop damages. Predictive crop relationships are
not automatically causal. Causal relationships are not automatically welfare
damages. Damages are not automatically marginal SCC increments. Each bridge
requires a separately validated receipt and an explicit overlap audit.
