# Twenty-year source-matched monthly rainfall climatologies

This is an independently audited **in-sample climate-input diagnostic** of
the [published PEEPS monthly patterns](https://doi.org/10.1371/journal.pclm.0000159)
and [author release](https://doi.org/10.5281/zenodo.7557622) against their
own MPI-ESM1-2-HR SSP5-8.5 precipitation source. It does not validate a
different ESM/scenario, crop-year sequence, agricultural impact, damage,
or SCC. The fixed early and late calendar-year windows are 2015–2034
and 2081–2100. Each is the equal-weighted monthly mean across twenty years
and the same two direct MPI members. The fixed MIRCA2000 rainfed-maize
nearest-center mapping has 30,821 positive-area cells, representing
108.086 million mapped hectares; it is not exact crop-field overlap.

| Late minus early 20-year climatology | Direct MPI | Published PEEPS | Published minus direct |
|---|---:|---:|---:|
| Area-weighted mean annual-rainfall change | +36.933 mm | +38.798 mm | +1.865 mm |
| Spatial annual-change error | — | — | 21.731 mm RMSE; 16.703 mm MAE |
| Annual-change sign agreement | — | — | 96.268% of mapped area |

The all-area monthly-climatology-change RMSE is 5.374 mm per month.
Its orthogonal components are 1.811 mm per month for annual-amount
error and 5.060 mm for within-year calendar-month redistribution error;
their squares reconcile to numerical precision. Thus the small
area-mean annual bias does not imply an equally small pattern error.
The twelve direct/published monthly mean changes and full metrics are
retained in the ignored primary JSON.

Physicality still fails: the raw published early and late monthly
climatologies contain at least one negative month on **1.406%** and
**6.131%** of mapped crop area, respectively (1,063 and 4,234 negative
month-center values). The minimum monthly climatologies are −1.192 and
−5.560 mm. On one fixed **92.814%** area positive for both periods,
the monthly-share total-variation distances are 0.020301 early and
0.017310 late. The original v1 score used different positive supports
for the two periods (98.594% and 93.869%); those original figures and
receipt are retained. The v2 fixed-support extension was declared in
`PEEPS_MPI_20YR_CLIMATOLOGY_PROTOCOL_20260918.md` and does not select a
model or change all-area errors. Neither the lower climatology errors
relative to one-year endpoints nor the restricted month-share scores
make the raw linear levels valid rainfall forcing.

Six GCS Blosc chunks were streamed in six fresh serial workers, with
source CRC32C and MD5 headers verified. They cover two members and every
month in both periods; each member/period has exactly 20 observations
per calendar month. No raw chunk was retained. The largest sampled
worker RSS was 353.80 MB, and each retained partial is approximately
1 MB, below the 512 MiB and 64 MiB gates; the >=130 GiB disk floor was
checked on every run and is now close enough to constrain further data
acquisition. The independently coded audit reassembled all six
source-partial arrays, reconstructed the twelve published monthly
coefficients from the author GMST series and month lengths, and passed
four full-matrix, 14 physical-level, and 72 change-score comparisons.
Two extraction and two scoring synthetic tests passed.

The v2 primary result SHA-256 is
`13efa4a8d6f1b2643c562e7300d89ceaa28d1fd183c6cd653c479189dabf8b79`;
its saved matrix SHA-256 is
`7bcb67dba20fa0a0eaeeb012b00ff5361562bb50743570139d6f9b892d641d6d`.
Raw/derived arrays and receipts remain ignored under `data/interim/`;
the protocol, implementation, synthetic tests and this report are
safe to version. The scripts are
`scripts/extract_peeps_mpi_20yr_crop_climatology.py`,
`scripts/score_peeps_mpi_20yr_climatology.py`, and
`scripts/audit_peeps_mpi_20yr_climatology.py`.

**Decision:** retain PEEPS as a source-bound climatological benchmark,
not GIVE forcing. Direct daily ISIMIP remains the physically valid
crop-feature source pending a separately validated and pulse-compatible
positive precipitation emulator. No yield, welfare or SCC calculation
is implied.
