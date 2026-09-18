# Preregistered author-PEEPS December crop-support physicality screen

Status: frozen before inspecting any crop-weighted result, 17 September 2026.
This screen cannot establish prediction skill, yield/damage effects or SCC.

Sources: author-released MPI-ESM1-2-HR SSP5-8.5 December `pr` coefficients
and matching annual GMST from PEEPS v1.1, source receipts/hashes in
`PUBLISHED_PEEPS_AUTHOR_DECEMBER_PILOT_RESULTS_20260917.md`; validated
MIRCA2000 area/share table
`data/interim/mirca_os_v2/irrigation_shares_2000.parquet`, expected SHA-256
`7512ffc580928a03f75bbce5f3d4263c9bb2c631a8ff04075973acb4b149e4ba`.

Filter exact rows `crop=mai`, `irrigation=noirr`, finite positive
`rainfed_area_ha`. Each MIRCA 0.5-degree center maps to the **nearest
native MPI latitude and circular longitude center**, with no crop calendar,
fractional overlap or spatial smoothing. Freeze this point-center proxy
before observing output; it is a screening diagnostic, not conservative
regridding and not a final crop exposure mapping.

At the same four preregistered years (2015, 2030, 2050, 2100), compute
`slope * author_GMST + intercept`, then report: the number of unique native
grid cells touched by rainfed maize, negative native cells touched, total
mapped rainfed maize hectares, hectares whose center maps to negative
predictions, percentage affected, and the most negative crop-mapped value
in mm/day. Do not clip negative values or drop small positive-area cells.

Validation gates: source receipt SHA and dimensions; the area input SHA;
finite positive areas and finite coordinates; one exact filter row per
MIRCA maize/noirrigation center; longitude wrap; all nearest indices in
range; independently recomputed nearest-index checks at 100 fixed evenly
spaced source rows; positive mapped area exactly reconciled to input area
at 1e-12 relative tolerance. A source or geometry failure stops the job.

The output is descriptive for **one ESM, one SSP, one month, one crop and
one irrigation regime**. Even zero crop-weighted negatives would not prove
the published route is physically valid in other months, crops or scenarios.
