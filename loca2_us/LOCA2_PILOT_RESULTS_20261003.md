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

The source-access engineering gate is open. County averaging, crop-season
feature construction, historical nClimGrid validation, outcome response,
causal damage, and SCC gates remain closed. The next bounded step is to create
TIGER-consistent LOCA2-to-county weights for fixed historical sentinel
counties, then compare daily historical LOCA2 and nClimGrid features on the
predeclared 2001--2014 validation block without reading yields.

Primary receipts:

- `data/provenance/loca2_official_catalog_audit_20261003.json`
- `data/provenance/loca2_cuming_gfdl_ssp245_2030summer_pilot.json`
- `data/provenance/loca2_cuming_gfdl_ssp245_2030summer_pilot_job.json`
