# Fixed NOAA county-average daily-weather acquisition, 1981–2025

The independently source-audited three-month pilot in
`US_NCLIMGRID_COUNTY_AVERAGE_EXTENSION_PILOT_20260916.md` established the
exact URL/schema and 3,107 identical county keys in January 1981, leap
February 2024 and July 2025. Its first failure at a 0.011°C rounded-midpoint
tolerance and disclosed 0.020°C source-only amendment remain part of the
record. The corrected pilot is at ignored
`data/interim/nclimgrid_county_average_terminal_pilot_20260916_v2/result.json`,
SHA-256 `a256aa61657f1fa7a1f445ee3f62fa595167dbe25dc2d5183e5fa1c58ba627e2`.

Acquire all 540 calendar months from January 1981 through December 2025,
**four** `scaled` county CSVs (`prcp`, `tavg`, `tmin`, `tmax`) plus one version
text each. There are 2,160 CSVs and 540 version texts, in deterministic
six-month (calendar-half-year) batches. No outcomes are read during weather
acquisition. Each fresh batch directory is ignored, isolated, and named by
year/half; prior polygon-weighted gridded NOAA files are not edited or
replaced. Pilot files serve only as source/schema references; batch downloads
use current upstream identity and preserve their own content hashes.

Per object, require official NOAA HTTPS host and exact constructed URL, HEAD
and GET HTTP 200 without redirect, identical Content-Length/ETag/
Last-Modified/Content-Type, no content encoding, <=2 MiB CSV or <=16 KiB
version text, exact body length, SHA-256, then 37-column daily CSV validation.
Require one exact month/variable, 28–31 real numeric days, publisher absent-
day fill convention, unique source/FIPS county mapping, and the **same 3,107
county key set** as the validated pilot in every variable/month. Reject a
changed crosswalk, reference pilot or URL. Across each month require PRCP>=0,
Tmin<=Tavg<=Tmax within 0.011°C and report the maximum Tavg-versus-midpoint
discrepancy; fail above the registered amended 0.020°C tolerance. Require a
version text that identifies the same complete month and nClimGrid-Daily
v1-0-0; preserve its full text and hash. Upstream revisions are recorded, not
silently mixed; each receipt includes object identities and acquisition time.

The [NOAA product page](https://www.ncei.noaa.gov/products/land-based-station/nclimgrid-daily)
documents daily CONUS precipitation/temperature and county area averages
since 1951, while the
[user guide](https://www.ncei.noaa.gov/pub/data/daily-grids/v1-0-0/nclimgrid-daily_v1-0-0_user-guide.pdf)
defines variables, scaled files and update limitations. County averages are
not field weather, and their spatial estimator is **not numerically identical**
to the project's 2019 TIGER polygon-weighted grids. Any later county response
must use the county-average estimator consistently in development and
2020–2025 terminal periods, test sensitivity to weather measurement, retain
county-boundary/vintage caveats, and refrain from national-to-global or
causal/SCC claims without separate validation.

Each network worker handles at most six months, one at a time: 512 MiB
sampled process-group RSS, 64 MiB newly owned ignored output, 1 MiB log cap,
130 GiB free-disk floor, no detached children. The expected ~2.4 GB total
is a planning estimate, not a guarantee; the disk floor is checked before
and during **every** batch. Stop on any integrity, schema, memory or disk
breach; keep failed receipts. Do not use a broadened download or relaxed
quality gate as an automatic retry. Full source/feature validation, NASS
outcome joins, response estimation, adaptation and welfare remain later
separate stages.
