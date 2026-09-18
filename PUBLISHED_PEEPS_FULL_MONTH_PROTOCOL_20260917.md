# Preregistered full-month published PEEPS input acquisition

Freeze before transfer: use the exact author PEEPS v1.1 `outputs.tar.gz`
(https://zenodo.org/api/records/7557622/files/outputs.tar.gz/content),
expected 3,244,457,764 bytes, MD5
`eed1a0e8a43bf915c78ec68d0f37e357`. Stream the archive once without
saving it. Within each nested `outputs/{month}_patterns.tar.gz`, retain
**only** `MPI-ESM1-2-HR_ssp585_pr_monthly_patterns_{month}.nc` for January
through December, in an ignored precipitation-project interim directory.
Never extract other variables/models/scenarios or write outside that folder.

Reject unexpected HTTP status/length, duplicate or absent months, non-NetCDF
members, any selected member above 8 MiB, total owned output above 64 MiB,
sampled worker RSS above 512 MiB, or free disk below 130 GiB. Confirm the
whole received outer archive byte count and MD5 before labeling selected
files as bitwise source-verified. Retain any failed job receipt and log; do
not use partial outputs in analysis. Record each member's SHA-256, bytes and
source metadata after a separate structure/units check.

This protocol provides **published monthly climate response inputs only**.
The previously observed negative rainfall means no raw linear level is
promoted. Next tests will compare monthly amount and shares on MIRCA crop
calendars and against an independent same-model climate trajectory, with
temperature/predictor alignment and nonnegative-rainfall screens. No yield,
damage or SCC result may be inferred from successful acquisition.
