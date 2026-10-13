# LOCA2 two-county, two-model historical sentinel

## Purpose

This outcome-blind diagnostic asks whether the proposed U.S. climate stage can
reproduce historical crop-season precipitation distributions at two
geographically separated Nebraska counties before it is coupled to NASS
yields. It compares free-running GFDL-ESM4 and IPSL-CM6A-LR historical output
with NOAA nClimGrid over the identical 2001--2012 corn calendar. Free-running
years are compared as distributions, not paired-year forecasts.

## Model-minus-observed climatology biases

| County | Model | Season rain (mm) | Maximum dry spell (days) | Rx5day (mm) | Mean temperature (C) |
|---|---|---:|---:|---:|---:|
| Cuming, Nebraska | GFDL-ESM4 | -29.44 | +4.03 | -0.43 | +0.89 |
| Cuming, Nebraska | IPSL-CM6A-LR | +4.90 | +0.73 | -4.32 | +1.34 |
| Box Butte, Nebraska | GFDL-ESM4 | -9.61 | +1.62 | -5.63 | +0.89 |
| Box Butte, Nebraska | IPSL-CM6A-LR | +36.63 | -1.51 | +7.92 | +1.03 |

The model ordering and even the sign of several moisture biases vary by
county. At Box Butte, GFDL is too dry with longer dry spells, while IPSL is too
wet with shorter dry spells and larger Rx5day. At Cuming, both models have
longer dry spells, but GFDL is much drier than IPSL. This is direct evidence
against treating any single model's U.S. precipitation pattern as the central
stage-1 result.

## Resource and validation status

The Box Butte IPSL source was fixed before climate values were read. Each
six-year metadata plan contains 30 remote objects and 582.79 MiB compressed.
The direct native-chunk jobs peaked at 357.78 and 381.95 MiB, below the 512 MiB
worker ceiling; the combined output covers every year from 2001 through 2012.
No yield or other outcome column was read.

This completes a two-county-by-two-model sentinel, not a validation over the
NASS outcome geography. The counties were selected outcome-blind, but two
locations and one realization per model cannot establish ensemble skill,
future drought, a crop response, damages, or SCC. Those gates remain closed.

## Reproducibility

Primary Box Butte IPSL receipts:

- `data/provenance/loca2_box_butte_ipsl_historical_climate_sentinel_2001_2006_direct_v2_20261013.json`
- `data/provenance/loca2_box_butte_ipsl_historical_climate_sentinel_2007_2012_direct_v2_20261013.json`
- `data/provenance/loca2_box_butte_ipsl_historical_climate_sentinel_2001_2012_direct_v2_20261013.json`
- corresponding bounded-job and metadata-preflight receipts under
  `data/provenance/`

The comparison values above are read from the combined Cuming GFDL/IPSL and
Box Butte GFDL/IPSL receipts. The scientific feature definitions are unchanged
from `LOCA2_PILOT_RESULTS_20261003.md` and
`LOCA2_VARIABLE_SERIAL_PARTITION_RESULTS_20261013.md`.
