# Methods Supporting Information

## M1. Reproducibility state

The current release contains the preregistered source and validation design,
an official-catalog audit, synthetic tests, Cuming and Box Butte County
geometry weights, and validated GFDL-ESM4 and IPSL-CM6A-LR 2001--2012
climate-distribution sentinels at Cuming. The Box Butte climate sentinel is
not yet run. The release does not contain restricted NASS credentials or
tracked raw climate arrays. Raw and interim files are ignored.

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
nClimGrid-Daily county feature pipeline on a predeclared common sample. Because
the historical GCM simulations are free-running, the climate-only comparison
uses fixed-period climatology bias, standard-deviation ratios, and quantile
errors for quantity, dry-spell, extreme-rain, distribution, and temperature
features. It does not use paired-year RMSE, correlation, or trend agreement.
TIGER 2019 versus TIGER 2023 boundary differences are crosswalked and reported;
no silent GEOID coercion is allowed.

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

The successful sentinel planned 559.88 MiB of compressed remote chunks but
persisted no remote climate arrays. Its sampled process-group peak was
484,589,568 bytes (462.14 MiB). Independent validation reconstructed 400
support and arithmetic checks with zero saved-precision disagreement. These
checks open only the single-county historical climate sentinel; multi-model,
multi-county, outcome-response, causal-damage, and SCC gates remain closed.

The second-GCM sentinel uses IPSL-CM6A-LR `r1i1p1f1`. The model was selected
from the preregistered global-bridge list, and `r1` was selected as the lowest
numeric historical realization in a metadata-only catalog check before any
IPSL climate value was read. All support and feature definitions are identical
to the GFDL-ESM4 sentinel. The cross-model summary applies the frozen equal-GCM
rule and reports each model separately; it performs no climate-skill or crop-
outcome weighting. IPSL independent validation reproduces 400 checks with zero
saved-precision disagreement. Its sampled process-group peak is 483,278,848
bytes, below the 512 MiB guard. This opens a second-GCM sentinel only, not the
general multi-model validation gate.

The second-county rule is outcome- and climate-value-blind. The completed
direct-practice nClimGrid reference contains no Fresno rows, so Fresno cannot
support the frozen comparison. From the 59 counties with complete 2001--2012
corn key/calendar support in both irrigation strata, the rule selects the
TIGER 2019 internal point farthest from Cuming. Box Butte County, Nebraska
(`31013`) is 520.4337 km away and is selected. The support audit reads only
county, crop, year, practice, and season-calendar keys; it does not read yield.

Box Butte geometry is intersected using the same algorithm and source vintage
as Cuming. One hundred positive LOCA2 cells cover effectively the full county,
weights sum to 0.9999999999999999, and the projected-versus-declared area error
is 3.46e-7 relative. The monitored geometry job peaks at 192,364,544 bytes.
Before any climate value is accessed, a hash-bound remote-object preflight
holds the GFDL member, 2001--2012 years, corn calendar, features, and nClimGrid
reference fixed. It finds 60 objects over two spatial chunks totaling
1,206,323,507 compressed bytes (1,150.44 MiB), exceeding the frozen 1,024 MiB
plan cap. The metadata-only process peaks at 185,270,272 bytes (176.69 MiB),
and execution therefore fails closed.

The next execution must preregister two chronological six-year partitions,
verify each metadata-only plan under the unchanged cap, and build them
serially under the 512 MiB process-group monitor. Concatenation is allowed only
after exact key, calendar, feature, source, and nonoverlap checks. The combined
2001--2012 comparison remains distributional and prohibits paired-year
scoring. Until that receipt passes, the Box Butte climate sentinel and all
multi-county, outcome-response, causal-damage, and SCC gates remain closed.

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
