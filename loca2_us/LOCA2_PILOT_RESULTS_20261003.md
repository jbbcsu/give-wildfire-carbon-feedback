# LOCA2 official-source audit and bounded pilot results

## Result

The metadata-only official-source audit passed, and the first fixed daily
cloud-chunk pilot completed under the resource contract. This establishes a
working low-storage access route; it is not a county climate projection, crop
response, damage estimate, or SCC.

## Official catalog audit

The audit hash-binds seven official metadata responses. It verifies:

- historical daily coverage from 1950-01-01 through 2014-12-31;
- future daily coverage from 2015-01-01 through 2100-12-31;
- daily precipitation, minimum temperature, and maximum temperature;
- precipitation version `v20240915` in both stores;
- public USGS Zarr assets with precipitation dimensions
  `ensemble × time × latitude × longitude` and future shape
  `221 × 31,411 × 474 × 944`; and
- CC0 statements for both relevant ScienceBase data releases.

The source-size audit rejects national-file download as the pilot route. The
revised county extreme-metric file is 2.676 GB; revised gridded scenario
bundles are 17.0--18.4 GB each. The official daily Zarr store permits bounded
chunk access instead.

## Fixed access-engineering pilot

Before climate values were read, the pilot fixed Cuming County, Nebraska
(`31039`), an approximate internal point (41.92 N, 96.79 W), GFDL-ESM4
`r1i1p1f1`, SSP2-4.5, and 2030-06-01 through 2030-08-31. It read no crop
outcomes.

The selected LOCA2 grid point is 41.90625 N, 263.21875 degrees east. Three
compressed remote objects totaled 60,253,980 bytes (57.46 MiB), below the
64 MiB preregistered cap. The monitored process-group peak was 291,700,736
bytes (278.19 MiB), below the 512 MiB cap, and the run completed in 10.25 s.

The 92-day engineering summary is 289.705 mm total precipitation, 25 wet days
at the 1 mm threshold, a 14-day maximum dry spell, 41.091 mm Rx1day, and
62.810 mm Rx5day. Mean daily Tmin/Tmax are 16.288/31.152 C. These values test
units, indexing, decoding, and feature arithmetic only. A single point and one
model/scenario/window cannot be interpreted as county exposure or climate
change.

## Gates and next step

The source-access engineering gate is open. A subsequent geometry-only step
also constructed TIGER 2019 county-to-LOCA2 weights for Cuming County. The
1,488,343,219 m2 projected polygon is represented by 63 positive LOCA2 cells;
grid coverage is 0.999999999999999 and the weights sum to 0.9999999999999999.
Projected area differs from TIGER's declared land-plus-water area by only
3.05e-8 relative. The monitored job peaked at 182.17 MiB RAM. It read
coordinate metadata and geometry only, not weather values or outcomes.

The first weight attempt stopped before geometry construction because the
frozen display label `Cuming County` did not equal TIGER's exact `NAME` value,
`Cuming`. The failed job receipt is retained. The config records the pre-value
metadata amendment, and the successful rerun used the exact source label.

County geometry weights are now open. Weather validity, crop-season feature
construction, historical nClimGrid validation, outcome response, causal
damage, and SCC gates remain closed. The next bounded step is to compare daily
historical LOCA2 and nClimGrid features on fixed sentinel windows without
reading yields.

## First historical climate-distribution sentinel

An outcome-blind 2001--2012 Cuming-corn sentinel now compares one free-running
historical LOCA2 realization (GFDL-ESM4 `r1i1p1f1`) with the existing
nClimGrid county feature pipeline. Only climate and key columns were read; no
yield column was loaded. Paired-year correlation and RMSE were prohibited
because a free-running historical GCM is not initialized to reproduce the
observed sequence of individual years. The comparison instead uses fixed-
period climatology, standard deviations, and five distributional quantiles.

Across the 12 fixed 170-day seasons, LOCA2 mean rainfall is 432.15 mm versus
461.58 mm in nClimGrid, a -29.44 mm bias. Mean maximum dry spell is 22.22
versus 18.19 days, a +4.03-day bias. In contrast, mean Rx5day is 84.24 versus
84.67 mm, a -0.43 mm bias, although its upper-middle quantile differs. Mean
season temperature is 20.29 versus 19.41 C, a +0.89 C product difference.
Rainfall, dry-spell, Rx5day, and temperature quantile RMSEs are 60.02 mm,
4.52 days, 5.84 mm, and 0.82 C. These are one-model, one-county climate-product
diagnostics, not agricultural effects or generalized LOCA2 skill estimates.

The successful run addressed two disclosed pre-value failures: the existing
full-feature nClimGrid panel lacks Cuming corn rows in 2013--2014, so the first
continuous sentinel is 2001--2012 and the full 2001--2014 gate stays closed;
and simultaneous chunk decoding marginally exceeded the 512 MiB contract, so
variables were decoded sequentially. The successful run planned 559.88 MiB of
compressed remote chunks, persisted no remote arrays, and peaked at 462.14 MiB
RAM. An independent validator reproduced 400 saved arithmetic and support
checks with zero saved-precision disagreement.

This sentinel shows why the U.S. paper must retain quantity, dry-spell, and
extreme-rain diagnostics separately: bias is not uniform across those
representations. Multi-model and multi-county validation remains closed.

## Second-GCM Cuming sentinel

The next outcome-blind step froze IPSL-CM6A-LR `r1i1p1f1` before climate-value
access. This is the second global-bridge GCM after GFDL-ESM4, and `r1` was
selected as the lowest numeric historical realization rather than on climate
skill or any crop outcome. Geography, 2001--2012 support, crop calendar,
features, nClimGrid reference, and distributional diagnostics are identical to
the first sentinel.

IPSL mean season rainfall is 466.49 mm, a +4.90 mm difference from nClimGrid;
maximum dry spell is 18.92 days, a +0.73-day difference; Rx5day is 80.35 mm, a
-4.32 mm difference; and season mean temperature is 20.75 C, a +1.34 C
difference. Their quantile RMSEs are 12.17 mm, 3.10 days, 6.88 mm, and 1.34 C.
Independent validation again reconstructed 400 checks with zero saved-
precision disagreement.

Under the frozen equal-GCM rule, the two-model mean climatology differences
are -12.27 mm for season rainfall, +2.38 days for maximum dry spell, -2.38 mm
for Rx5day, and +1.11 C for season mean temperature. These averages are
descriptive climate-product sentinels, not skill weights: the model-specific
bias ranges are retained and no model is selected using climate or outcome
performance. The IPSL job read 566.98 MiB of compressed remote chunks,
persisted no raw arrays, and peaked at 483,278,848 bytes (460.89 MiB), below
the 512 MiB guard.

The second-GCM sentinel gate is open. General multi-model validation remains
closed with only two GCMs and one county; multi-county, outcome-response,
causal-damage, and SCC gates also remain closed.

## Second-county geographic preflight

The geographic extension was selected without climate values or crop outcomes.
The first proposed contrast, Fresno County, had no rows in the completed
direct-practice nClimGrid reference. Among the 59 counties with complete
2001--2012 corn key/calendar support in both direct-practice strata, the frozen
rule therefore selects the TIGER 2019 internal point farthest from Cuming.
This selects Box Butte County, Nebraska (`31013`), 520.4337 km from Cuming.
The support audit read only county, crop, year, practice, and season-calendar
keys.

Geometry construction passed. The 2,791,584,336.25 m2 projected polygon is
represented by 100 positive LOCA2 cells; coverage is effectively one, weights
sum to 0.9999999999999999, and projected area differs from TIGER's declared
land-plus-water area by 3.46e-7 relative. The monitored job peaked at
192,364,544 bytes (183.45 MiB), below the 512 MiB guard.

The metadata-only climate preflight then stopped before reading any climate
value. Holding the original GFDL-ESM4 member, 2001--2012 support, calendar,
features, and reference fixed requires 60 remote objects across two spatial
chunks, totaling 1,206,323,507 compressed bytes (1,150.44 MiB). This exceeds
the unchanged 1,024 MiB remote-plan cap. The metadata-only preflight itself
peaked at 185,270,272 bytes (176.69 MiB). The second-county climate sentinel
and multi-county validation gates therefore remain closed.

Two chronological six-year partitions were then frozen without changing the
source, member, county, calendar, features, reference, or scoring rule. Their
metadata-only plans both pass: 2001--2006 requires 30 objects and 602,729,539
bytes (574.81 MiB), while 2007--2012 requires 36 objects and 724,320,234 bytes
(690.77 MiB). The preflights peaked at 182,730,752 and 182,747,136 bytes,
respectively, and read neither climate values nor outcomes.

The first serial climate build began only after both preflights passed. The
resource monitor terminated it at 560,070,656 bytes (534.13 MiB), above the
512 MiB gate. It produced neither a feature file nor a successful sentinel
receipt. As required, the second partition was not run and concatenation was
not attempted. No Box Butte climate comparison is reported, and the
second-county and multi-county climate gates remain closed. A future retry
requires a separately frozen lower-memory spatial-chunk accumulation method
and equivalence tests before any new climate-value access.

That lower-memory method was subsequently frozen as
`one_source_spatial_chunk_at_a_time_v1`. It decodes cells from only one source
spatial chunk at a time, constructs the same nonlinear cell basis, then
reassembles cell rows in the original global order before applying the same
full-vector dot product. A deterministic 170-day synthetic test is bit-for-bit
equal to an independently written copy of the legacy all-cell calculation;
missing-cell partitions fail closed. The retry-specific metadata preflight
again passes at 602,729,539 bytes (574.81 MiB), with no climate values or
outcomes read and a 182,190,080-byte (173.75 MiB) peak.

The authorized 2001--2006 retry nevertheless reached 546,308,096 bytes
(521.00 MiB) and was terminated by the unchanged 512 MiB monitor. It wrote no
feature file or successful sentinel receipt. The second partition and
concatenation again were not run. The implementation and failed receipt are
retained as reproducibility evidence, but no geographic climate result or
downstream claim gate is opened.

Primary receipts:

- `data/provenance/loca2_official_catalog_audit_20261003.json`
- `data/provenance/loca2_cuming_gfdl_ssp245_2030summer_pilot.json`
- `data/provenance/loca2_cuming_gfdl_ssp245_2030summer_pilot_job.json`
- `data/provenance/loca2_cuming_tiger2019_weights_20261003.json`
- `data/provenance/loca2_cuming_tiger2019_weights_job_20261003.json` (failed metadata check)
- `data/provenance/loca2_cuming_tiger2019_weights_job_v2_20261003.json`
- `data/provenance/loca2_cuming_gfdl_historical_climate_sentinel_2001_2012_20261003.json`
- `data/provenance/loca2_cuming_gfdl_historical_climate_sentinel_validation_20261003.json`
- `data/provenance/loca2_cuming_gfdl_historical_climate_sentinel_job_v4_20261003.json`
- `data/provenance/loca2_cuming_ipsl_historical_climate_sentinel_2001_2012_20261004.json`
- `data/provenance/loca2_cuming_ipsl_historical_climate_sentinel_validation_20261004.json`
- `data/provenance/loca2_cuming_ipsl_historical_climate_sentinel_job_20261004.json`
- `data/provenance/loca2_cuming_two_model_climate_sentinels_20261004.json`
- `data/provenance/loca2_cuming_two_model_climate_sentinels_validation_20261004.json`
- `data/provenance/loca2_box_butte_tiger2019_weights_20261004.json`
- `data/provenance/loca2_box_butte_tiger2019_weights_job_20261004.json`
- `data/provenance/loca2_box_butte_gfdl_historical_chunk_preflight_20261004.json`
- `data/provenance/loca2_box_butte_gfdl_historical_chunk_preflight_job_20261004.json`
- `data/provenance/loca2_box_butte_gfdl_historical_2001_2006_preflight_20261004.json`
- `data/provenance/loca2_box_butte_gfdl_historical_2001_2006_preflight_job_20261004.json`
- `data/provenance/loca2_box_butte_gfdl_historical_2007_2012_preflight_20261004.json`
- `data/provenance/loca2_box_butte_gfdl_historical_2007_2012_preflight_job_20261004.json`
- `data/provenance/loca2_box_butte_gfdl_historical_2001_2006_job_20261004.json` (memory gate)
- `data/provenance/loca2_box_butte_gfdl_historical_2001_2006_spatial_chunk_v1_preflight_20261004.json`
- `data/provenance/loca2_box_butte_gfdl_historical_2001_2006_spatial_chunk_v1_preflight_job_20261004.json`
- `data/provenance/loca2_box_butte_gfdl_historical_2001_2006_spatial_chunk_v1_job_20261004.json` (memory gate)
