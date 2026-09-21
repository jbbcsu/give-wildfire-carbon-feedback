# Post-result PDSI competitor for the U.S. all-practice terminal test

The first NOAA county-average rain-quantity/timing scores were already seen
before fixing this exact PDSI comparison. This is a **post-result competing
moisture sensitivity**, not a fresh independent confirmation or a causal
precipitation treatment. Keep the validated 1981–2025 NASS/NOAA outcome
panel, fixed 2017 <=10% irrigated-acreage share, 2019 geography gate,
2010 crop calendars and 2020–2025 terminal years unchanged.

Use only the already local, SHA-512-pinned [NOAA nClimDiv county PDSI](https://www.ncei.noaa.gov/pub/data/cirs/climdiv/)
snapshot `climdiv-pdsicy-v1.0.0-20260806`, with its retained source manifest,
county-code crosswalk and publisher documentation. The publisher's 1931–1990
calibration is fixed independently of 2020–2025 yields. Extract the needed
2020–2025 monthly county values from that *same* snapshot, preserving missing
versus zero and source identity. Reuse the historical 1981–2019 crop-calendar
PDSI feature table only after checking its source/calibration metadata and
recomputing selected historical county seasons from the pinned raw monthly
file. Compute recent seasonal PDSI as a day-weighted mean of overlapping
calendar months; retain the monthly minimum as a separate exploratory
extreme-moisture alternative. Report exact PDSI support/attrition; compare
only identical crop/county/year rows across candidate models.

For each crop, use the same county fixed effects, 1981–2019 fit,
2020–2025 test, log-yield RMSE/MAE/bias, historical 1981–2010-fit/
2012–2019 diagnostic with 2011 purged, and conditional paired state
bootstrap as the initial rain benchmark. The PDSI competitor replaces the
rainfall terms with `PDSI_season_mean` and its square, retaining the same
seasonal TAVG and 29°C heat controls. Do **not** add PDSI alongside raw rain,
dry-spell or stage-rain features. The monthly-minimum PDSI extension is
reported separately and explicitly exploratory. Repeat with one time slope
per state as post-result robustness, but do not select the better trend basis
after scoring. PDSI itself uses moisture supply/demand and temperature;
shared TAVG/heat controls serve predictive comparability but **do not**
identify the separate precipitation contribution.

All source/feature, coefficient/score and exact-support checks must pass
before reporting. Use one bounded worker at a time (512 MiB sampled RSS,
<=64 MiB newly owned ignored output, >=130 GiB free disk). No new data
download, irrigation treatment, climate-change attribution, global
transport, agriculture valuation or SCC is authorized by this comparison.
