# MRI-ESM2-0 SSP5-8.5 midcentury validation

The predeclared MRI-ESM2-0 `r1i1p1f1` SSP5-8.5 precipitation and mean
temperature files for 2041--2050 pass their pinned byte counts, SHA-512
checksums, 3,652-day noon chronology, global grid, units, and decoded-content
gates. Each field has 946,598,400 finite values and no missing values.
Precipitation has no negatives and 350,607,000 genuine zeros.

The paired temperature field yields ten annual same-realization GMST values.
The bounded maize/rainfed block contains 5,488 season and 16,464 stage rows for
harvest years 2042--2049. Stage days, rain, wet-day counts, and Rx1day
reconcile exactly. Relative to matched SSP1-2.6 cells, SSP5-8.5 averages
+0.777 C, -8.808 mm seasonal rain, +0.276 wet days, -2.828 maximum-dry-spell
days, -1.500 mm Rx1day, and -2.676 mm Rx5day. These are descriptive climate
differences, not yield or damage effects.

The now-complete three-scenario MRI midcentury block contains 181,104 long
feature rows. Leave-one-whole-scenario-out GMST adjustment improves 15 of 33
feature comparisons over the cell-mean benchmark; the median RMSE ratio is
1.00027 and the maximum is 1.04233. It improves 4 of 11 features when SSP5-8.5
is held out. Exact support flags place 21,236 values (11.73%) outside the
two-scenario envelope.

This closes 36 of 60 predeclared later-century files and eighteen bounded
feature blocks. The single-ESM holdout is adverse engineering evidence and
does not authorize a response: MRI end-century coverage, expanded whole-ESM
validation, FAIR baseline/pulse feature support, damages, and SCC remain open.
