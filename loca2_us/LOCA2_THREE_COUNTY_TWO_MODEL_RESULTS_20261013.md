# LOCA2 outcome-blind third-county historical sentinel

## Frozen selection and scope

Before reading any LOCA2 climate value, the third county was selected from the
unchanged 59 counties with complete 2001--2012 corn-calendar support in both
direct-practice strata.  The rule excluded Cuming and Box Butte, then maximized
the minimum TIGER-2019 internal-point distance to those anchors, with ascending
GEOID as the exact-tie breaker.  It selected Furnas County, Nebraska (GEOID
31065), 324.37 km from Cuming and 347.53 km from Box Butte.

The climate diagnostic uses the same May 6--October 22, 170-day corn season,
GFDL-ESM4 r1i1p1f1 and IPSL-CM6A-LR r1i1p1f1, and NOAA nClimGrid reference as
the earlier sentinels. Free-running years are compared as distributions, not
as paired-year predictions. No yield or other outcome magnitude was read.

## Result

Model-minus-observed climatology biases over 2001--2012 are:

| County | Model | Season rain (mm) | Maximum dry spell (days) | Rx5day (mm) | Mean temperature (C) |
|---|---|---:|---:|---:|---:|
| Cuming | GFDL-ESM4 | -29.44 | +4.03 | -0.43 | +0.89 |
| Cuming | IPSL-CM6A-LR | +4.90 | +0.73 | -4.32 | +1.34 |
| Box Butte | GFDL-ESM4 | -9.61 | +1.62 | -5.63 | +0.89 |
| Box Butte | IPSL-CM6A-LR | +36.63 | -1.51 | +7.92 | +1.03 |
| Furnas | GFDL-ESM4 | -63.87 | +12.08 | +4.90 | +1.03 |
| Furnas | IPSL-CM6A-LR | -22.54 | +7.16 | -4.75 | +1.33 |

Furnas is not a redundant replication of either anchor. Both models are drier
than nClimGrid there, and both produce substantially longer maximum dry spells;
the model rain biases differ by 41.33 mm and their Rx5day biases have opposite
signs. Across the three counties, GFDL rain bias is negative at all three,
whereas IPSL changes sign; dry-spell and Rx5day bias signs also depend on both
county and model. This strengthens the diagnostic evidence that direct-rainfall
pattern uncertainty is spatially heterogeneous and should not be represented by
one model or one sentinel location. It does not establish model skill or a
national uncertainty distribution.

## Validation and resources

Furnas has 60 positive county-to-grid weights with coverage and weight sum
equal to one to floating precision. Each model was processed as two frozen,
nonoverlapping six-year direct-native-chunk jobs and then combined locally.
Sampled process-group peak RSS was 355.23, 355.23, 329.36, and 359.14 MiB for
GFDL 2001--2006, GFDL 2007--2012, IPSL 2001--2006, and IPSL 2007--2012,
respectively, all below 512 MiB.

Each six-year artifact passed an independent 376-check validation with zero
saved-statistic discrepancy. Each 12-year combination passed a separate
517-check reconstruction from the two hashed partition outputs and the
observed inputs, again with zero discrepancy. Arrow emitted sandbox-only cache
size discovery warnings during local Parquet reads; all validation outputs were
finite and exact. The complete 29-test LOCA2 suite passed at a sampled 148.06
MiB process-group peak.

## Claim boundary and next gate

This is a purposive three-county, two-model climate-distribution sentinel. It
does not open a representative multi-county validation, paired-year prediction,
yield-response, causal-damage, future-projection, adaptation, or SCC gate.
The next bounded scientific gate is a preregistered compact support design that
selects additional counties by climate/agronomic strata (not by realized LOCA2
bias), followed by the same direct-chunk diagnostic. Adding more models at only
these Nebraska locations would not resolve the larger geographic-support gap.

## Reproducibility

- `scripts/preregister_third_county.py`
- `scripts/validate_historical_climate_sentinel.py`
- `scripts/validate_historical_climate_partition_combination.py`
- `config/loca2_us_furnas_{gfdl,ipsl}_historical_{2001_2006,2007_2012}_direct_v2.toml`
- `data/provenance/loca2_third_county_preregistration_20261013.json`
- `data/provenance/loca2_furnas_tiger2019_weights_20261013.json`
- `data/provenance/loca2_furnas_{gfdl,ipsl}_historical_climate_sentinel_{2001_2006,2007_2012}_direct_v2_20261013.json`
- `data/provenance/loca2_furnas_{gfdl,ipsl}_historical_climate_sentinel_2001_2012_direct_v2_20261013.json`
- corresponding bounded-job, preflight, and independent-validation receipts
  under `data/provenance/`
