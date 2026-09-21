# Registered U.S. county-average crop-year weather features

## Purpose and estimand boundary

Build a **new, separate** daily-weather feature route for the 1981–2025 U.S.
corn-grain and soybean county validation. This route uses the acquired
[NOAA nClimGrid-Daily](https://www.ncei.noaa.gov/products/land-based-station/nclimgrid-daily)
county *area averages*, not the earlier polygon-weighted cell-first weather.
It allows historical and 2020–2025 outcomes to be evaluated against the same
weather measurement. County area-average weather is not crop-field weather;
nonlinear county-average features are not equivalent to averages of nonlinear
cell features. This is a distinct measurement sensitivity, not a silent update
to earlier estimates or a globally transportable crop response.

## Frozen source and calendar rules before outcome join

Require the complete 90-batch, 540-month 1981–2025 NOAA acquisition summary,
its exact 2,700 source objects, every batch result/hash, unchanged 3,107 FIPS
county set, four daily variables and version texts. Recheck each source hash
before a year's features are built. Use the fixed, visually source-audited
[USDA NASS 2010 field-crop usual dates](https://www.nass.usda.gov/Publications/Todays_Reports/reports/fcdate10.pdf)
for corn grain and soybeans: primary midpoint of the most-active planting and
harvest intervals; published planting-begin through harvest-end is a *separate*
broad-window sensitivity. Rebuild a 1981–2025 calendar from the pinned PDF in
a fresh ignored path, and require the overlapping 1981–2022 rows to reproduce
the previously validated calendar exactly before use. The fixed 2010 calendar
does not track realized year-specific planting, adaptation or within-state
heterogeneity. Never select a window using 2020–2025 yield performance.
Use NOAA's published date labels without shifting the 24-hour precipitation
window; the source's [early-morning end-time metadata](https://www.ncei.noaa.gov/thredds/dodsC/nclimgrid-daily/2025/ncdd-202503-grd-scaled.nc.html)
makes a one-day boundary shift a later explicit calendar sensitivity, not an
unrecorded correction.

## Feature families and validation

For each state/crop/year fixed window and each eligible NOAA county, retain
`precip_mm` as the parsimonious quantity baseline; daily TAVG season mean and
TMAX degree-day/count heat measures are confounder controls. Competing
moisture representations are wet-day count (PRCP>=1mm), longest dry run
(PRCP<1mm), maximum five-day PRCP, three stage rainfall totals/shares on
fixed 0–30–70–100% duration partitions, and precipitation concentration.
This mirrors the project's already documented engineering basis but applies
it *after* NOAA county averaging. Stage shares are zero with an explicit
zero-total indicator when seasonal rain equals zero; stage totals must sum to
season total and shares to one otherwise. Stage labels are duration proxies,
not observed phenology. Preserve both rainfall total and distribution in
research; a distribution term is not privileged unless it adds robust
incremental out-of-sample value. PDSI/scPDSI/SPEI are separate competing
moisture-stress families, not unplanned additive rain/temperature controls.

Features are outcome-free and partitioned by harvest year with SHA-256
receipts, source/version/calendar identities, county counts, missingness,
finite/range checks, exact daily date continuity, fixed 3,107-county input
support, and no duplicated crop/county/year. Inputs are read one year at a
time; the bounded worker permits <=512MiB sampled process-group RSS, <=64MiB
new interim output, and >=130GiB free disk. A year with a missing source,
invalid crosswalk, date gap or failed feature invariant is rejected, not
imputed. The per-year partitions are not used to fit until an independent
feature validator reconstructs selected counties/years/days and the national
NASS support/irrigation-screen join passes.

## Later response and SCC gates

Historical fitting, 2020–2025 terminal prediction and NASS outcome use are
separate stages. The all-practice outcome under a fixed <=10% 2017 irrigated-
acreage screen remains a **proxy**, not observed non-irrigated yield. Holdouts
must carry prior model-selection exposure and temporal/county composition.
No U.S. predictive score alone identifies climate-change-induced
precipitation damages, adaptation, global transfer or a GIVE SCC increment.
These require separate climate forcing, attribution/temperature/CO2 controls,
economic valuation, existing-GIVE-agriculture replacement accounting and
uncertainty gates.
