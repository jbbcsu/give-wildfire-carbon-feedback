# Published-style monthly GMT–precipitation benchmark: preregistration

Status: design only, registered 2026-09-17 before fitting or inspecting any
new monthly time-series climate values. This is an **external raw-CMIP6
climate benchmark**, not a replacement for the primary bias-adjusted daily
ISIMIP3b feature route and not an agricultural damage or SCC estimate.

## Question and paper anchor

Can a parsimonious published-style pattern-scaling fit map the same ESM's
annual global mean surface temperature (GMST) to monthly precipitation
fields well enough to recover crop-season **total rain and monthly
distribution** on held-out scenarios? The benchmark follows the
ESM/scenario/calendar-month grid-cell linear construction in Kravitz and
Snyder's PEEPS paper (2023, https://doi.org/10.1371/journal.pclm.0000159).
The paper and available author code are cited as a method, not claimed as a
new invention. Do not use the already reduced two 30-year climatologies
as pseudo-annual samples: they do not contain the time variation needed to
fit a slope.

## Fixed source and model sequence

1. Begin with the twelve already metadata/coordinate-verified GFDL-ESM4 and
   IPSL-CM6A-LR `r1i1p1f1` raw-CMIP6 monthly `pr`/`tas` stores: historical,
   SSP1-2.6 and SSP5-8.5. Keep model, member, grid, version, units,
   calendar and license from the hash-bound September 8 source inventory.
   Use historical 1981–2010 to define a same-model GMST reference. Do not
   mix raw-CMIP6 GMST with the distinct ISIMIP3b daily-source GMST series.
2. First test GFDL-ESM4 alone; extend to IPSL only after source-grid area
   weights are verified. Acquire the **exact native-grid `areacella`** (or
   equivalent trustworthy cell-boundary areas) by a separately documented,
   checksum-bound metadata/source gate. If that fails, stop the fit rather
   than treating an irregular native grid as equal-area. Compute annual
   GMST from monthly `tas`, weighted by actual month length and cell area.
   Check annual 12-month completeness, finite Kelvin values, and the exact
   same ESM/member/scenario identity. Use the raw monthly time series, not
   an annualized difference of historical/future climatologies.
   The public catalog contains exact GFDL historical `gr1` and IPSL
   historical `gr` `r1i1p1f1` `fx/areacella` stores. Static-versus-Amon
   coordinate identity is tested at fixed absolute tolerance `1e-10`
   degrees (`rtol=0`): the first GFDL exact-bit comparison failed solely
   on observed `7.11e-15`-degree latitude and `5.68e-14`-degree longitude
   serialization differences. Its failed resource receipts/logs remain.
3. Freeze the primary fit to SSP5-8.5 **2015–2080**, with SSP1-2.6
   **2031–2060** as the named whole-scenario holdout. A secondary
   late-SSP5-8.5 **2081–2100** time-block holdout tests extrapolation.
   Per ESM and calendar month, fit native-grid precipitation *flux*
   `pr[y,m,g] = alpha[m,g] + beta[m,g] * (GMST[y] - historical_mean_GMST)
   + residual[y,m,g]` using float64 streaming sufficient statistics.
   Do not train on either holdout. A 20-year centered GMST diagnostic may
   be compared separately, but may not replace the declared annual fit
   after seeing scores. Keep `pr` in kg m-2 s-1 during fitting; convert
   each predicted monthly flux to mm with that source month interval only
   when calculating amount metrics. Report physically impossible negative
   predictions; never silently clip them or pass such cells onward.
4. Evaluate on exact model-native held-out gridded fields and after the
   already validated fixed rainfed-maize calendar/area transfer. Primary
   climate-only comparisons: unchanged historical calendar-month means;
   one annual-quantity adjustment preserving historical within-year month
   shares; and twelve fitted monthly patterns. Report month/grid and
   crop-area-weighted RMSE and bias for monthly flux, crop-season amount,
   month-share total variation, and rainfall-centroid displacement. The
   quantity-only comparator must use the **same** training information
   and GMST predictor as the monthly fit. Fixed MIRCA-2000 area weights
   and both harvest-year/source-calendar conventions are retained.
   Native-grid scores use the verified `areacella` weights for every
   cell-month/year and retain year-level sufficient statistics. Monthly
   and annual amount RMSE/bias use all finite source cells, including
   physically invalid *predictions* (which are separately counted, not
   repaired). Month-share total-variation scores are calculated only on
   one **common** cell-year support where actual and all three predicted
   annual totals are positive and every monthly amount is nonnegative.
   Report that support's area fraction and all physical-failure counts;
   do not compare distributions on model-specific selected samples.
5. Inspect scenario support, GMST variation, physical-domain failures,
   tropical and monsoon-region errors, and inter-ESM disagreement. A
   scenario holdout checks transfer; it is not a causal isolation of GMT
   from aerosol/forcing history or internal variability. Two ESMs are a
   limited benchmark sample, not a probabilistic CMIP6 ensemble.

## Source integrity and resource controls

Read pinned Zarr metadata and coordinate receipts before climate chunks.
Every compressed chunk must have size/hash and server checksum recorded;
verify the declared uncompressed bound before decode, process only one
chunk at a time, and retain no raw cloud chunk. Source rights: GFDL
CC-BY-SA 4.0; IPSL CC-BY-NC-SA 4.0 with producer acknowledgement. Store
derived arrays and receipts only under ignored `data/interim`, keep each
owned output <=64 MiB, use one worker with sampled process-group RSS
<=512 MiB, and require free disk >=130 GiB. Any prospective output over
the cap must be tiled, never silently truncated. No raw or restricted
climate payload enters Git.

The first GFDL historical GMST reduction passed. The first SSP5-8.5
attempt stopped at the predeclared 96 MiB compressed-transfer cap before
decoding: the same source chunk had already been checksum-verified at
107,521,299 bytes in the September 8 climatology reduction. The revised
112 MiB compressed cap retains the <=192 MiB decoded cap and sampled
512 MiB worker guard; the failed receipt/log are preserved. This is a
resource-bound correction, not a changed climate result or fitted model.

## Promotion gate

This benchmark can justify a monthly climate **comparison**, not the
crop-weather driver, unless it beats the quantity-only and no-change
comparators on named holdouts without nonphysical outputs. It cannot
establish daily wet-day frequency, dry-spell persistence, Rx1day/Rx5day,
PDSI/SPEI, stage heat–moisture covariance or a small matched FAIR/GIVE
pulse. Those require direct-daily validation and a separate paired-path
design. Even a passing monthly climate fit cannot provide an SCC until
the yield-response, adaptation, welfare-replacement, no-double-counting
and pulse-convergence gates pass. Report null or adverse comparisons.

## Fixed next step after native-grid holdouts: crop-calendar climatology check

The native-grid holdouts above were scored before this crop-specific
extension. Freeze the following **before** reading crop-cell scores.
Use only the two whole-SSP1-2.6 2031–2060 cases, because the late
SSP5-8.5 tests mostly exceed training GMT support and should not be
interpreted as reliable crop projections. For harvest-year crops that
cross January, use the existing source-verified 2030–2059 predecessor
monthly climatology as well as 2031–2060; the former requires the
additional SSP1-2.6 GMST year 2030, not a new fit. Compare each
model's saved, independently checked actual raw-CMIP6 monthly
climatologies to the three *frozen* predictions on the same native
grid: unchanged historical monthly flux, annual-quantity-only
prediction distributed by fixed historical month shares, and the
fitted month-specific flux response. For each 30-year window,
evaluate the month-specific *linear flux* predictions at the average
**same-model** annual GMST anomaly (algebraically the mean of annual
linear flux predictions). For the quantity-only comparator, compute
each year's predicted annual water from that year's GMST, multiply
by the fixed historical month share, divide by that year's actual
source month seconds, **then** take the 30-year monthly flux mean.
This respects leap-month duration and avoids ratio-of-means bias.
Do not mix ISIMIP GMST with raw-CMIP6 fields.

Use the existing fixed MIRCA-2000 rainfed-maize positive area cells,
exact source planting/harvest calendar, and the project's already
tested native-grid interpolation and season-bin functions. Retain
both harvest-year and source-calendar-year conventions. Report
excluded calendar/area support explicitly and do not impute it.
Evaluate crop-area-weighted crop-season amount RMSE/bias across all
finite actual cells, retaining and counting negative predicted
amounts. For month-share TV and rainfall-centroid error, use a
single common cell support where actual and all three predictions
have nonnegative within-season monthly amounts and positive season
totals. Report its area fraction. Save cell-level derived ledgers
for independent arithmetic audit. These are climatology-of-monthly-
rain tests, **not** mean annual crop responses or daily dry-spell /
extreme validation; no coefficient, damage or SCC may be inferred.

The first GFDL crop-calendar run computed its first 2.7 MB derived
cell ledger but stopped before acceptance because the writer tried
to make a relative path from a relative path and an absolute project
root. That failed ledger and resource/log remain in the original
ignored interim directory. The reviewed path serialization uses
`path.resolve().relative_to(ROOT)` and a fresh `v2` output directory;
no original data or fit is changed.
