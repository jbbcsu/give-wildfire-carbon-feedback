# MRI-ESM2-0 SSP3-7.0 midcentury validation

The predeclared MRI-ESM2-0 `r1i1p1f1` SSP3-7.0 precipitation and mean
temperature files for 2041--2050 passed their exact pinned byte counts,
SHA-512 checksums, 3,652-day noon chronology, global 0.5-degree grid, units,
and decoded-content gates. Each field contains 946,598,400 finite values and
no missing values. Precipitation has no negative values and 352,760,808 genuine
zeros; temperature spans 187.647--317.034 K.

The paired temperature field produced ten annual same-realization GMST values.
Using the registered maize/rainfed calendar and fixed latitude rows 100--101,
the paired fields produced 5,488 crop-year rows and 16,464 three-stage rows for
harvest years 2042--2049. Stage days, precipitation totals, wet-day counts, and
Rx1day reconcile exactly to the season-level features. The receipt is
`data/provenance/isimip3b_later_century_mri_ssp370_2041_2050.toml`.

Relative to exact-key MRI SSP1-2.6 cells, SSP3-7.0 averages +0.369 C,
-11.018 mm seasonal precipitation, -1.067 wet days, +0.228 maximum-dry-spell
days, -0.323 mm Rx1day, and +0.257 mm Rx5day. These are descriptive climate
differences, not yield or damage effects.

This closes 34 of 60 predeclared later-century files and seventeen bounded
feature blocks. It is an engineering/content validation only: the third MRI
scenario and both remaining MRI end-century scenario cells are incomplete,
whole-ESM and whole-scenario holdouts were not rerun, and no FAIR
baseline/pulse feature support, damage, or SCC input is authorized.
