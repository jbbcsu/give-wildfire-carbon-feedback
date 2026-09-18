# Preregistered PEEPS MPI same-source monthly rainfall reconstruction

**Purpose and classification.** Test how closely the published PEEPS
MPI-ESM1-2-HR SSP5-8.5 monthly `pr` coefficients reproduce their own
two-member direct-CMIP6 source on rainfed-maize center support. Because
the source scenario was used to fit those coefficients, this is an
**in-sample reconstruction diagnostic, not a predictive holdout**, not
daily rainfall, and not crop yield/damage/SCC. A later different-scenario
comparison is required for out-of-sample validation.

Freeze inputs: the twelve whole-archive-MD5-verified author coefficients,
the author absolute-GMST series, the four GCS-MD5-verified source metadata
objects, and the passed coordinate/time-bounds gate. Required manifest
SHA-256 values are: monthly coefficient receipt
`fafe91fafb0f64b1448501bb49b623e21ad86e3c882a6b65b5fb337d8b6fa753`,
author GMST receipt
`cd632ffb21d171c48787f5d4766a2ae29f22d657db56a074738a7dc2c9a2bad3`,
source metadata
`96d0057abb0776eec9dc55aa137fa5c3313622404e6afb3ce3045c77432113c0`,
coordinates
`0c77d5a44c35f5aec0d6fc14a8630e28177d038c1e81af1833a64464d955092b`.
MIRCA2000 positive rainfed-maize hectares are the same SHA-256-verified
center table used by the prior physicality screen. Map centers to native
MPI cells at the validated <=1e-10-degree grid tolerance; do not
conservatively regrid or claim crop-calendar exposure.

Preselect **all twelve months in 2015 and 2100** for each of the two
SSP5-8.5 direct precipitation members (`r1i1p1f1`, `r2i1p1f1`). This
requires only first and last time chunks per member (indices 0 and 1
for the first member, 0 and 4 for the second). Fetch/decode one climate
chunk at a time, verify its GCS MD5 if present and the Blosc header
against declared full or final-edge chunk shape, use the validated time
index and calendar-month duration, extract only the 24 requested planes,
and release the full chunk before fetching the next. Never store source
climate chunks; retain only small results and receipts. Do not read `tas`
payload: the published ensemble-mean absolute GMST series is the exact
pattern predictor for this initial diagnostic.

Build the pointwise direct **two-member arithmetic mean** for each
month/grid cell (matching the pinned author `p1` ensemble-average
implementation) and the published linear predicted level at the same
GMST/year/month. Convert flux to mm/month with exact calendar days.
For each year report direct-field negative/missing counts, published
negative crop-area share, and the crop-area-weighted month-level error
(MAE and RMSE) including the published negative levels as mathematical
errors, not clipping them. Separately report annual-total error and
month-share total-variation error only on a **fixed common physically
valid** crop-area subset with positive annual totals, always stating its
area fraction. Report results by year and by individual month so that
annual-quantity agreement cannot mask seasonal shifts. Do not discard
invalid published locations from the negative-area accounting.

Require SHA/metadata/calendar/coordinate checks and independent scalar
sentinels at selected native cells. One worker, sampled group RSS <=512
MiB, output <=64 MiB, log <=2 MiB, free disk >=130 GiB. A failure or
source drift is retained and reported, not worked around silently.
The first-model/scenario result cannot establish global multi-model
uncertainty or a GIVE SCC change.

## Transparent memory-safe v2 amendment after retained first failure

The initial monolithic worker was stopped by the monitor at sampled
537,542,656 B (>512 MiB) before accepting any output. Its failed log,
receipt and exact first implementation are retained. The compressed
first-member 2015 source chunk is 142,792,222 B and its declared decoded
chunk is 176,947,200 B; crop-data and NetCDF libraries in the same
process contributed to peak RSS. **Do not raise the 512 MiB cap.** Split
the same frozen estimand, source hashes, years/months and metrics into
three serial jobs: (1) prepare a small MIRCA-to-native-grid mapping/area
artifact; (2) decode the four climate chunks sequentially with only
NumPy/numcodecs and the mapping, retaining a small crop-center matrix;
(3) score the published author coefficients against the retained direct
matrix. Each job independently uses the original RSS/output/disk/log
caps; source chunks are never retained. The failed monolithic output is
not promoted. Preserve the same-scenario **in-sample** label.

## Transparent v3 amendment after second retained memory failure

The v2 lightweight decoder completed three source chunks but was stopped
at sampled 539,213,824 B on the fourth. Its log confirms the first
three successful decodes, but no combined direct artifact was accepted.
The likely cause is resident allocator/decompressor memory retained across
sequential chunks in one process; this is an inference from the observed
order and RSS, not a measured allocation trace. Keep its failed monitor
receipt and log. Run **one frozen source chunk per fresh worker process**,
each writing only the requested single-year crop-center matrix and chunk
hash/CRC receipt, then assemble four small artifacts in a separate job.
Each fresh worker retains <=512 MiB sampled RSS, <=64 MiB owned output,
<=2 MiB log and >=130 GiB free disk. No raw chunk is stored. Do not call
the first two failed runs climate estimates or lift their guardrails.

Primary model/data: Kravitz and Snyder (2023),
https://doi.org/10.1371/journal.pclm.0000159 and
https://doi.org/10.5281/zenodo.7557622 . The DKRZ/DWD raw-CMIP6 source
terms are preserved in the metadata manifest.
