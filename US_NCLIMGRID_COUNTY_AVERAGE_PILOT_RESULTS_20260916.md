# NOAA county-average daily-weather pilot: source-only result

The preregistered, outcome-blind pilot acquired January 1981, leap February
2024, and July 2025 from the official [NOAA nClimGrid-Daily county-average
archive](https://www.ncei.noaa.gov/products/land-based-station/nclimgrid-daily).
For each month, all four daily variables (PRCP, TAVG, TMIN, TMAX) and the
publisher's version text passed exact URL, HTTP identity, byte-count, SHA-256,
schema, calendar, crosswalk, county-key, nonnegative-rain, and temperature-order
checks. Each month has the same 3,107 county keys; real day counts are 31,
29, and 31. Maximum TAVG-versus-TMIN/TMAX-midpoint discrepancy is 0.015°C
in every pilot month, below the disclosed amended engineering tolerance of
0.020°C. The first run failed at its original 0.011°C tolerance; its log and
files are retained, and the amendment occurred before looking at NASS yields.

The corrected pilot receipt is
`data/interim/nclimgrid_county_average_terminal_pilot_20260916_v2/result.json`,
SHA-256 `a256aa61657f1fa7a1f445ee3f62fa595167dbe25dc2d5183e5fa1c58ba627e2`.
The fixed acquisition protocol is
`US_NCLIMGRID_COUNTY_AVERAGE_FULL_ACQUISITION_20260916.md`, SHA-256
`362a680df48eb0e16a76492d813441e14e32222c238218b97fe97c5a1d2b803f`.
The first six-month batch (2020 January–June) also passed its guards, with
26,244,616 source bytes and sampled peak group RSS 55.3 MiB.

Subsequently, all twelve 2020–2025 six-month batches completed and were
rehashed by the resumable controller: 360 exact source objects and
314,939,057 source bytes. Every recent batch passed the per-job memory,
new-output and free-disk guards. This is **acquisition only**; the historical
1981–2019 batches and full 540-month summary are still in progress at this
checkpoint. No recent crop-year features or weather/yield response has yet
been evaluated.

This validates a feasible *source and engineering route*, not a crop-weather
relationship. NOAA county averages use a distinct spatial estimator from the
previous TIGER polygon-weighted weather product; a fitted historical model
and 2020–2025 terminal test must use the same county-average route throughout.
The publisher version text also differs across sampled years, so source
revision and boundary/measurement sensitivity must be tracked. No yield
coefficient, climate-change attribution, welfare effect, or SCC has been
estimated from this pilot. See the [NOAA user guide](https://www.ncei.noaa.gov/pub/data/daily-grids/v1-0-0/nclimgrid-daily_v1-0-0_user-guide.pdf)
for variable and version definitions.
