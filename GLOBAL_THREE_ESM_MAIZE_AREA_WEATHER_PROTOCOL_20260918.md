# Frozen rainfed-maize-area weather comparison

Registered before reading any 2092--2099 weather values for this
weighting analysis. The already validated direct-ISIMIP3b daily-derived
maize/rainfed panels for UKESM1-0-LL, IPSL-CM6A-LR and MPI-ESM1-2-HR,
SSP1-2.6/3-7.0/5-8.5, and harvest years 2092--2099 supply the weather.
This is a **descriptive climate-input** comparison, not a fitted
precipitation-per-K relationship or crop-yield/damage/SCC result.

Use one fixed [MIRCA-OS v2 HydroShare release](https://www.hydroshare.org/resource/e4582ca0042148338bb5e0148b749ed6/)
2000 rainfed-maize harvested-area basis from
`data/interim/mirca_os_v2/irrigation_shares_2000.parquet`, SHA-256
`7512ffc580928a03f75bbce5f3d4263c9bb2c631a8ff04075973acb4b149e4ba`.
Keep only `crop=mai`, `irrigation=noirr`, finite strictly positive
`rainfed_area_ha`, unique exact `(lat,lon_360)` keys. This has 30,821
positive-area cells and 108,086,337.428 mapped ha before climate-calendar
matching. An outcome-blind 2092 UKESM SSP1-2.6 key-only check found
30,654 matches and 47,672.170 ha excluded; do not impute these. Require
the same exact matched key set across **all** 72 ESM/scenario/year
panels, and report its count and share of original area. If not stable,
stop rather than changing the support to obtain a desired sign.

For each source year, read validated 36 latitude tiles, binding the
independent global validation to the SHA-256 of its global manifest
and each read season/stage tile to its manifest hash. Validate unique
season keys, exactly three stage rows per key, finite/nonnegative
precipitation and extremes, stage-rainfall sum equals season rainfall,
and exact fixed `0,0.3,0.7,1` stage proxy. Compute the following
fixed-area-weighted mean weather exposures for each ESM/scenario/year:
season rainfall, stage 1/2/3 rainfall, wet days >=1 mm, maximum dry
spell days, Rx1day, Rx5day, and season mean temperature. Also compute
equal-cell means **on the same matched crop support**, solely to show
the effect of area weighting. Average these eight yearly means equally
within each ESM/scenario and subtract SSP1-2.6 from SSP3-7.0 and
SSP5-8.5. Do not divide by same-realization GMST; short scenario
differences mix forcing and internal variability.

Report per-ESM, per-scenario contrasts and sign agreement for seasonal
amount, stage allocation, wet/dry exposure and rainfall extremes; do
not pool ESMs into a causal global estimate or interpret the min/max
as confidence intervals. A separate implementation must recompute the
weighted numerators/denominators and scenario contrasts from saved
compact ledgers or source tiles, checking source hashes and support.
No yields, prices, welfare or GIVE files are read. Retain raw/interim
outputs ignored; only safe code, protocol and aggregate report are
versioned. Keep one monitored worker at a time under 512 MiB sampled
RSS, 64 MiB owned output, 130 GiB free disk and 2 MiB log caps.
