# Post-result irrigation-screen sensitivity for the U.S. forecast comparison

The original nationwide NASS/NOAA rain-model results were inspected before
this sensitivity was implemented. It is **not** a fresh independent test.
The primary estimand remains county `ALL PRODUCTION PRACTICES` yield among
counties with a fixed 2017 crop-specific Census irrigated-acreage share
<=10%, not directly observed non-irrigated yield. This analysis tests the
sample-proxy choice specified in the earlier
`US_COUNTY_AVERAGE_RESPONSE_PREANALYSIS_20260916.md`.

Reuse the exact pinned historical 1981–2019 NASS source panel, official
2020–2025 terminal NASS snapshot, NOAA daily county-average crop-year
features, 2010 usual-date crop calendar, and 2019 TIGER geography gate.
Do not re-download, impute, change feature definitions or choose counties
using weather/yield response. For each crop, construct separate fixed
county selections using eligible numeric Census harvested and irrigated
acreage shares at <=10%, <=20%, <=30% for 2017 and 2022. Suppressed or
missing shares are never zero. Apply each selection to both historical and
terminal outcome years, and report initial, positive, selected, geography,
weather-joined, training and scored terminal counts. Require that the
2017 <=10% constructed keys and all values reproduce the validated primary
panel exactly before interpreting any alternative screen.

Fit the same county-FE, common-trend no-weather, rain-total/temperature and
expanded-pattern ladders, 1981–2019, scoring 2020–2025 and the already
examined 1981–2010 / 2012–2019 blocked diagnostic on identical keys within
each selection. Retain annual results and the fixed-forecast paired state
bootstrap; do not use a screen's better score to retroactively select a
preferred primary sample. A 2022 Census screen uses information from inside
the terminal period, and crop irrigation itself can respond to weather and
economics: treat it as a **composition diagnostic only**, never as a
prospectively fixed or causal sample. More permissive screens include more
irrigated production in all-practice yield; this is sensitivity to proxy
purity, not a measured irrigation effect. The same counties may occur under
several nested thresholds; differences in RMSE across screens are not
paired treatment contrasts because the evaluated population changes.

Run one bounded worker, <=512 MiB sampled process-group RSS, <=64 MiB new
ignored output, >=130 GiB free. Source identities and script/protocol hashes
must be in the result. Independently reconstruct sample support and scores
before any scientific claim. Nothing here establishes rainfall causality,
climate-induced precipitation change, global welfare or SCC.
