# MRI-ESM2-0 three-scenario end-century validation

The frozen MRI-ESM2-0 `r1i1p1f1` SSP1-2.6 and SSP3-7.0 precipitation and
mean-temperature files for 2091--2100 pass exact byte, SHA-512, 3,652-day
noon chronology, global grid, unit, and full decoded-content gates. Every
field has 946,598,400 finite values and no missing values. Precipitation is
nonnegative, with 356,694,065 genuine zeros under SSP1-2.6 and 351,568,727
under SSP3-7.0.

Each paired temperature field yields ten same-realization annual GMST values.
Each bounded maize/rainfed cell contains 5,488 season and 16,464 three-stage
rows for harvest years 2092--2099. Stage days, rain, wet days, and Rx1day
reconcile exactly; quantity, timing, maximum dry spell, Rx1day, Rx5day, and
mean temperature pass the registered finite and physical-support gates.

On exact paired keys, SSP3-7.0 minus SSP1-2.6 averages +2.928 C, +2.238 mm
seasonal rain, -0.968 wet days, +2.412 maximum-dry-spell days, +0.250 mm
Rx1day, and +1.151 mm Rx5day. The mean stage precipitation-share shifts are
+0.01195, -0.01361, and +0.00075 across the three fixed windows. These are
two-latitude climate-feature diagnostics, not crop-response or damage effects.

Together with the completed midcentury matrix, these two cells raise the
registered expansion to 40 of 60 files and twenty bounded feature blocks.
The subsequently acquired SSP5-8.5 pair passes the same gates and adds a third
5,488-season/16,464-stage block. Relative to SSP1-2.6, it averages +4.591 C,
-13.229 mm seasonal rain, -2.623 wet days, +5.436 maximum-dry-spell days,
+0.754 mm Rx1day, and +0.560 mm Rx5day.

The completed 181,104-row end-century matrix improves 16 of 33 whole-scenario
GMST comparisons over the cell-mean benchmark. The median and maximum RMSE
ratios are 1.00006 and 1.06514; 27,090 held-out feature values (14.96%) lie
outside the two-scenario support envelope. SSP3-7.0 improves only 2 of 11
comparisons. This adverse/mixed engineering result raises registered progress
to 42 of 60 files and twenty-one bounded blocks but does not authorize a
production emulator. Whole-ESM support, FAIR baseline/pulse feature support,
response, damage, and SCC gates remain closed.
