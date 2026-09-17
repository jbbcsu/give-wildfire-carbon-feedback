# PEEPS-style climate benchmark on rainfed-maize calendars: first result

This result tests **prediction of 30-year monthly precipitation
climatologies on crop calendars**, not yield response, damages or SCC.
The whole SSP1-2.6 2031–2060 scenario was held out from the fixed
SSP5-8.5 2015–2080 GFDL and IPSL monthly-rainfall-versus-GMST fits.
Crop seasons spanning January use the separately verified 2030–2059
predecessor monthly climatology and same-realization annual GMST.
Each model is evaluated on the exact same fixed MIRCA-2000 rainfed-maize
area and source planting/harvest dates. An annual-quantity-only model
with the same training information is the key comparator; both source-
calendar and harvest-year conventions were frozen before scoring.

| ESM / calendar convention | Quantity-only season-amount RMSE (mm) | Monthly-pattern RMSE (mm) | Quantity-only month-share TV | Monthly-pattern TV | Negative predicted crop-cell months |
|---|---:|---:|---:|---:|---:|
| GFDL / source-calendar year | 48.211 | 45.929 | 0.04497 | 0.04053 | 9 |
| GFDL / harvest year | 48.415 | 45.799 | 0.04498 | 0.04035 | 9 |
| IPSL / source-calendar year | 36.986 | 28.556 | 0.03605 | 0.02956 | 68 |
| IPSL / harvest year | 36.871 | 28.599 | 0.03599 | 0.02949 | 68 |

Amount RMSE uses all 28,328 crop cells with valid source calendars,
climate and fixed area (99.309% of mapped rainfed-maize hectares),
retaining negative predictions in the error calculation. Month-share
TV (0–1, lower is better) uses one common physical support with no
negative monthly prediction and positive seasonal totals for all
three comparator paths: 28,319 cells in GFDL and 28,269 in IPSL.
These supports represent 99.99985% and 99.99892% of valid mapped
area respectively, so the negative forecasts are concentrated in
small-area crop cells. On that same support, absolute rainfall-
centroid error falls from 1.82–1.83 to 1.63–1.64 days in GFDL and
from 1.70 to 1.14 days in IPSL. The unchanged-historical baseline
season-amount RMSE is 49.05–49.13 mm (GFDL) and 62.29–62.38 mm
(IPSL), depending on calendar convention.

The predeclared monthly-pattern model thus improves the **crop-
footprint climate-input** comparison in both ESMs and both calendar
conventions, including season amount as well as monthly shares. It
does not pass the zero-negative-rain gate and is **not** promoted as
GIVE forcing. Moreover, this compares two 30-year monthly mean
climatologies and evaluates a linear fit at mean scenario GMST; it
does not test year-by-year crop-season variability, daily planting-
stage timing, wet-day frequency, dry spells, Rx1day/Rx5day, PDSI/SPEI,
heat–moisture covariance or a small matched CO2 pulse. The raw-CMIP6
fields are not interchangeable with bias-adjusted ISIMIP3b. Two ESMs
do not characterize global climate uncertainty. A better climate-
input forecast is also **not** evidence that precipitation timing
improves agricultural-yield prediction or produces larger SCC damages;
the separate historical yield tests retain their null/adverse timing
results.

The source/fit/holdout hashes, licenses and exclusions are in the
ignored `data/interim/pangeo_*_ssp126_maize_monthly_crop_benchmark*_20260917/`
receipts. The first GFDL job stopped after writing one derived ledger
because of a relative-path serialization error; that failed ledger and
log remain. The `v2` GFDL output and IPSL output completed under the
512 MiB/64 MiB/130 GiB resource limits (sampled RSS peaks 309.81
and 269.24 MB). An independent saved-cell-ledger check passed all 100
area, amount, share, centroid and physical-count aggregate comparisons
with zero numerical disagreement; its receipt is
`data/interim/pangeo_maize_monthly_benchmark_validation_20260917/result.json`.
This independent check does not re-decode the original CMIP6 source
chunks. No coefficient, crop loss or SCC value was exported.

Next: test whether a physically constrained published monthly model
improves crop-footprint climate prediction without negative rain and
whether daily direct-ISIMIP crop features can pass joint dependence,
whole-model/scenario and small-pulse validation. No modeling choice
from the user is required for this benchmark stage.
