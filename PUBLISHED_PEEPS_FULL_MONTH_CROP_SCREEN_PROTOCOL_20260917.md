# Preregistered author PEEPS twelve-month crop-support screen

Freeze before computing: use only the whole-archive-MD5-verified twelve
MPI-ESM1-2-HR SSP5-8.5 monthly `pr` coefficient files and the separately
SHA-256-verified author annual absolute GMST predictor. Verify every
coefficient hash again. Map positive MIRCA2000 rainfed-maize 0.5-degree
centers to the nearest native MPI grid center using latitude distance and
circular longitude distance; this is a diagnostic proxy, not conservative
regridding or crop-calendar exposure. Preserve the existing independent
100-row center-mapping audit and area-conservation check. Exclude zero-area
rows only, and report their number.

For 2015, 2030, 2050 and 2100, evaluate the authors' **linear levels**
`slope_month * absolute_GMST_year + intercept_month`, converting kg m-2 s-1
to mm per calendar month with actual Gregorian month lengths. For each
month/year report mapped rainfed-maize hectares and percent with negative
predicted rain. Also report area with any of twelve months negative. Never
clip, replace or silently discard negative values. A monthly-zero value is
physically allowed but is not valid for share calculations if the annual
total is zero.

For the fixed common set of rainfed-maize centers with all twelve months
nonnegative in **both** 2015 and 2100 and positive annual totals, report
its hectares and share of all positive rainfed-maize hectares. On this
same set compute (a) area-weighted mean predicted calendar-year rain total
in both years and its change in mm and percent; and (b) area-weighted mean
total-variation distance between the two twelve-month *per-cell* shares,
`0.5 * sum_m |share_2100,m - share_2015,m|`. This is monthly redistribution,
not a dry-spell, planting-date, crop-year or yield estimate. If common
support is empty, report this explicitly and do not compute summary means.

Require source hashes, metadata, common native grids, finite predictions,
the independent 100-center mapping audit, area conservation, Gregorian day
weights, and independent Decimal arithmetic sentinels. New output is one
fresh ignored interim JSON below 64 MiB; one numerical worker with sampled
RSS <=512 MiB, log <=2 MiB and free disk >=130 GiB. Preserve any failures.
Do not use this screen as an ESM holdout or infer agriculture damages/SCC.

Sources: Kravitz and Snyder (2023),
https://doi.org/10.1371/journal.pclm.0000159 ; author coefficients and
predictor from https://doi.org/10.5281/zenodo.7557622 ; MIRCA2000 source
and license are recorded in the project's existing MIRCA manifest.
