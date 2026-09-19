# GFDL future SPEI boundary pilot protocol

Registered before reading derived drought values on September 19, 2026.

## Question and role

Can the frozen observational SPEI transform be applied without refitting to a
complete, source-consistent ISIMIP3b historical/future boundary under the
current memory and storage limits? This is an engineering and numerical
continuity test. It is not a drought-yield estimate, climate-change attribution,
damage calculation, or SCC result.

## Fixed inputs

- Climate model: GFDL-ESM4 `r1i1p1f1`, ISIMIP3b/W5E5 version `20210512`.
- Historical daily fields: 2011--2014 `pr`, `tasmin`, and `tasmax`.
- Future daily fields: 2015--2020 under SSP1-2.6, SSP3-7.0, and SSP5-8.5 for
  the same three variables.
- Spatial support: the first 512 cells in the frozen 31,208-cell maize/soy crop
  support ordering, exactly as stored in the validated historical candidate
  block `data/interim/spei_sparse_fit_block_20260908/spei.nc`.
- Transform: Hargreaves-Samani monthly P-minus-ET0, right-aligned 1/3/6-month
  sums, and the cell/calendar-month GLO parameters fitted only on 1982--2011
  observational GSWP3-W5E5 weather in that frozen block.

Every raw climate file must match the already registered byte count and SHA-512
in `isimip3b_gfdl_historical_ssp126_boundary.toml`,
`isimip3b_gfdl_scenario_matrix.toml`, or
`isimip3b_gfdl_temperature_extrema.toml`. The builder rehashes the files; it
does not rely on names alone.

## Required checks

1. Exact daily chronology, native 360 x 720 coordinates, declared units, and
   common coordinates across variables.
2. No missing daily triplets and no temperature-order violation beyond the
   registered 0.00005 K float32 tolerance.
3. Exactly 120 consecutive months per scenario. The 2011--2014 monthly inputs,
   accumulated balances, and standardized values must be bit-identical across
   scenarios except for the expected leading scale-3/6 warm-up missingness.
4. Frozen parameters must have valid fit status, 30 calibration values, finite
   location/shape, positive scale, and absolute shape below one. No parameter
   is re-estimated from GFDL or future values.
5. Report by scenario and scale: finite values, tail clips, mean SPEI, and
   fractions at or below -1 and -1.5 for 2015--2020. These are cell-month
   engineering summaries, not independent event frequencies or damages.
6. An independent validator must rehash the result, reconstruct every reported
   aggregate from the saved arrays, verify historical identity and zero missing
   values after the scale warm-up, and check all false scientific-use gates.

## Resource gates

Run one process under 512 MiB sampled process-group RSS, 64 MiB newly allocated
output, a 130 GiB free-space floor, and a 2 MiB log cap. Read one global daily
field at a time; never load a daily-year or global multi-variable cube. Do not
download any data.

## Interpretation gate

Passing authorizes only extension of the same frozen transform to later
ISIMIP3b windows once their registered inputs are available. The 2015--2020
scenario paths are short and weakly separated, are not common-random-number
CO2 pulses, and cannot be interpreted as climate-change effects or marginal
SCC inputs.
