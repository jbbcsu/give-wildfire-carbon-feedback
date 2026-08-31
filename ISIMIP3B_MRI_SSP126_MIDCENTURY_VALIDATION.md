# MRI-ESM2-0 SSP1-2.6 midcentury validation

The predeclared MRI-ESM2-0 `r1i1p1f1` SSP1-2.6 precipitation and mean
temperature files for 2041--2050 passed their exact pinned byte counts,
SHA-512 checksums, 3,652-day noon chronology, global 0.5-degree grid, units,
and decoded-content gates. Each field contains 946,598,400 finite values and
no missing values. Precipitation has no negative values and 353,485,749 genuine
zeros; temperature spans 191.094--317.440 K.

The paired temperature field produced ten annual same-realization GMST values.
Using the registered maize/rainfed calendar and fixed latitude rows 100--101,
the paired fields produced 5,488 crop-year rows and 16,464 three-stage rows for
harvest years 2042--2049. Stage days, precipitation totals, wet-day counts, and
Rx1day reconcile exactly to the season-level features. The receipt is
`data/provenance/isimip3b_later_century_mri_ssp126_2041_2050.toml`.

This closes 30 of 60 predeclared later-century files and fifteen bounded
feature blocks. It is an engineering/content validation only: no feature
response was fitted, whole-ESM and whole-scenario holdouts were not rerun, and
no FAIR baseline/pulse feature support, damage, or SCC input is authorized.
