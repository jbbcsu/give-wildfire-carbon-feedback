# Pilot for a consistent nationwide NOAA daily county-weather route

The post-2019 all-practice NASS support audit finds hundreds of screened
corn/soy county outcomes nationally but only tens in the project's existing
regional daily-weather geography. This pilot asks whether official
[NOAA nClimGrid-Daily county area averages](https://www.ncei.noaa.gov/products/land-based-station/nclimgrid-daily)
can provide a **separate, internally consistent** historical-plus-terminal
weather estimator. It does not assert equivalence to the existing 2019 TIGER
polygon-weighted grid estimator. The prior fixed seven-month comparison
found small but nonzero differences, so no estimator swap is silent.

Before any new county-average download, fix three outcome-blind months:
January 1981 (historical start), February 2024 (leap-day edge), and July 2025
(recent crop-season month). For each, acquire only the official `prcp`,
`tavg`, `tmin`, `tmax` `cty-scaled.csv` files plus the month version text from
`https://www.ncei.noaa.gov/data/nclimgrid-daily/access/averages/{year}/`.
The already local official NCEI-to-FIPS state-code crosswalk is an input and
will be hash-pinned. Use HEAD and GET with exact final URL, content length,
ETag, Last-Modified and type; cap CSV bodies at 2 MiB and reject redirects,
truncation or changed identity. Save files and SHA-256/HTTP receipts only in
fresh ignored interim paths. Do not overwrite prior weather snapshots.

Validate exact 37-column monthly CSV schema, one unique NOAA county code,
mapped FIPS key, variable and month per row; 28/29/30/31 real daily numeric
values and absent-day fill; identical county set across four variables/months;
nonnegative rain, Tmin<=Tavg<=Tmax allowing at most 0.011°C rounded-midpoint
error. Record source-specific county counts, version strings, hashes and any
failure. Do not use NASS outcome magnitudes, choose a county based on yield,
fit a response, estimate climate damages, or export SCC. If the pilot passes,
write a separate annual-batch historical/2020–2025 acquisition contract with
at most ~64 MiB new output per worker, 512 MiB sampled RSS and 130 GiB free
disk floor. County-average boundary/measurement and source-revision caveats
must be carried into all later comparisons.

## Amendment after first source-only pilot failure

The first pilot, before any NASS outcome use, downloaded/validated all four
January 1981 CSVs and version text but stopped at the above midpoint bound:
the maximum published county-day `|TAVG−(TMAX+TMIN)/2|` was **0.015°C**.
Minimum PRCP was 0; TAVG remained between Tmin and Tmax (minimum separation
0.11°C in the diagnostic), and no other failure was observed before stop.
The failed job/log and four source CSVs are retained. The
[NOAA user guide](https://www.ncei.noaa.gov/pub/data/daily-grids/v1-0-0/nclimgrid-daily_v1-0-0_user-guide.pdf)
defines TAVG from Tmax/Tmin, but the regional published CSVs are rounded;
the original 0.011°C gate is an analyst tolerance, not a publisher guarantee.

For a **fresh** pilot run, raise only the midpoint engineering tolerance to
0.020°C, retaining every exact HTTP/schema/count/finite/nonnegative/temperature-
order check and reporting the maximum discrepancy for every month. This is a
disclosed source-only amendment, not a chosen weather/yield relationship, and
does not authorize nationwide acquisition if any further gate fails.
