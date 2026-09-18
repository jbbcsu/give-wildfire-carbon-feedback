# Author PEEPS December rainfall: rainfed-maize support screen

This is the preregistered diagnostic in
`PUBLISHED_PEEPS_CROP_SUPPORT_POSITIVITY_PROTOCOL_20260917.md`, not a
validated climate projection, yield result, damage estimate or SCC.

The first bounded run failed before a result because MIRCA's share table
retains `crop=mai, irrigation=noirr` rows even at zero rainfed area. The
protocol had specified **positive** rainfed hectares, but the first code
version rejected those rows rather than filtering them. Its failed
`crop_support_monitor.json` and `crop_support.log` are retained. The v2
implementation applied the preregistered positive-area filter, excluded
2,541 zero-area rows, and completed at 145,096,704 bytes sampled peak RSS.
The four-year output and receipts are in the ignored
`data/interim/peeps_published_mpi_ssp585_dec_v2_20260917/` folder.

The screen uses only the author-released MPI-ESM1-2-HR/SSP5-8.5/December
rainfall coefficients and matched author GMST from PEEPS v1.1, and exact
MIRCA2000 rainfed maize harvested area (SHA-256
`7512ffc580928a03f75bbce5f3d4263c9bb2c631a8ff04075973acb4b149e4ba`).
It maps each of 30,821 positive-area 0.5-degree MIRCA centers to the
nearest native MPI latitude and circular longitude center, touching
10,167 MPI cells and conserving 108,086,337.428 harvested hectares.
One hundred fixed source rows passed an independent brute-force nearest-
center audit. This point-center mapping is a **proxy**, not conservative
overlap or crop-calendar weighting.

| Year | Negative MPI native cells / 73,728, including ocean | Negative native cells touched by rainfed maize | Mapped rainfed maize ha with negative December prediction | Share of mapped rainfed maize area |
|---|---:|---:|---:|---:|
| 2015 | 109 | 52 | 976,907 | 0.9038% |
| 2030 | 13 | 6 | 132,043 | 0.1222% |
| 2050 | 0 | 0 | 0 | 0% |
| 2100 | 782 | 177 | 794,983 | 0.7355% |

The minimum prediction on a maize-touched cell is -0.005835 mm/day in
2015 and -0.029712 mm/day in 2100 (the more extreme global-grid negative
cells reported in the [source pilot](PUBLISHED_PEEPS_AUTHOR_DECEMBER_PILOT_RESULTS_20260917.md)
are not necessarily cropped). The raw published linear *level* fails the
nonnegative-rainfall gate on a nonzero crop footprint, albeit a small share
in this one month/crop/model. No clipping was applied. This does not
invalidate using published **marginal slopes** around a positive,
source-matched baseline, or using a positive published monthly model; those
are alternative implementations that must be prospectively validated.

Interpretation is strictly limited to one month, ESM, scenario, crop,
irrigation regime and vintage. The December exposure may occur before or
after the crop season at many locations. The next test requires all relevant
calendar months, an explicit historical rainfall anchor, source-matched
temperature scaling, actual crop calendars and held-out scenarios. Do not
convert these percentages to yield losses, damages or SCC.
