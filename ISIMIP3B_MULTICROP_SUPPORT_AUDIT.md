# Bounded ISIMIP3b multi-crop support audit

The primary daily-feature route now has a checksum-bound midcentury support
audit beyond maize. The fixed UKESM1-0-LL r1i1p1f2 comparison uses SSP1-2.6 as
the reference and SSP5-8.5 as the candidate for harvest years 2042--2049 and
the same two latitude rows used by the engineering smokes. It covers
first-season rice, second-season rice, soybean, spring wheat, and winter wheat
under rainfed calendars, plus soybean under its irrigated calendar.

All six cells pass finite/nonnegative rainfall, wet-day and dry-spell bounds,
Rx1day/Rx5day ordering, exact crop/calendar identity, complete declared years,
and stage-to-season reconciliation. Five cells contain 5,488 seasonal and
16,464 stage rows. Second-season rice has 3,264 seasonal and 9,792 stage rows;
the validator records rather than hides that lower calendar support.

SSP5-8.5-minus-SSP1-2.6 mean seasonal rainfall changes range from -38.27 mm
for winter wheat to +19.05 mm for second-season rice. Mean maximum-dry-spell
changes range from +0.46 to +9.56 days across rainfed crops. Rx5day changes
range from -3.26 to +10.37 mm, and precipitation-timing-centroid changes also
differ in sign across crops. These fixed-cell differences demonstrate that a
maize-only feature gate cannot stand in for global multi-crop support.

The paired soybean calendar sensitivity retains 5,488 exact spatial/year
keys in each scenario. Irrigated-calendar minus rainfed-calendar exposure is
-16.94 mm rainfall and -0.83 maximum-dry-spell days under SSP1-2.6, and
-12.43 mm and -0.80 days under SSP5-8.5. This is a calendar contrast, not an
irrigation treatment effect; it supplies no irrigated/rainfed yield response.

The frozen configuration is
`config/isimip3b_ukesm_multicrop_midcentury_support_v1.toml`; the executable is
`scripts/audit_isimip3b_multicrop_support.py`; and the deterministic receipt is
`data/provenance/isimip3b_ukesm_multicrop_midcentury_support_20260901.json`.
This is one ESM, one period, two scenarios, and two latitude rows. It does not
promote the adverse affine emulator, estimate a causal yield response, validate
rainfed/irrigated outcomes, calculate damages, or authorize an SCC input.
