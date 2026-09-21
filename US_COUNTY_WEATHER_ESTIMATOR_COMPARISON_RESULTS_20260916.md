# U.S. NOAA weather-estimator comparison on identical crop seasons

This post-result **source-only** comparison reads no yield values. It joins
the older cell-first TIGER polygon-weighted nClimGrid-Daily weather to the
new official NOAA county-area-average crop-year weather on exact corn/soy
county/harvest-year and calendar dates. The old practice-specific table has
two irrigation-practice rows per key but identical weather/calendars across
them; they are collapsed to one exposure. All **11,861** distinct old keys
(7,016 corn, 4,845 soybean) match a new feature row and the exact fixed
start/end dates. This is the older regional practice-specific geography,
not a nationwide matched sample. Wet-day thresholds are both 1 mm; calendar
source/vintage and stage definitions match. Original NOAA gridded weather
and NOAA county-average source revisions/spatial estimators remain distinct.

For the same matched weather keys, paired absolute differences between the
new county-average and older polygon/cell-first estimates are:

| Crop | Seasonal rain median / p95 | Mean temp median / p95 | Wet days median / p95 | Max dry spell median / p95 | Rx5 median / p95 |
|---|---:|---:|---:|---:|---:|
| Corn | 0.621 / 2.604 mm | 0.005 / 0.019 °C | 0.923 / 3.062 days | 0.523 / 4.774 days | 0.703 / 5.648 mm |
| Soybeans | 0.713 / 2.849 mm | 0.005 / 0.019 °C | 0.879 / 2.941 days | 0.450 / 4.707 days | 0.725 / 5.654 mm |

The new-minus-old mean difference in maximum dry spell is −0.271 corn and
−0.383 soybean days; in Rx5 it is −1.413 and −1.358 mm. Stage-1/stage-2
rain-share median absolute differences are about 0.001, with 95th
percentiles about 0.004. Full signed means, RMSEs and correlations for all
seven registered fields are preserved in the ignored result JSON. A separate
Arrow-source reconstruction passed **191** exact-key, fixed-anchor and
aggregate-statistic checks. Jobs peaked at 247 and 230 MiB sampled RSS.

The small difference in additive seasonal rain and mean temperature does
not imply interchangeable drought/extreme features. Computing nonlinear
dry-spell/Rx5 measures after county averaging need not equal first computing
them per grid cell and then aggregating; source revision and polygon support
can also matter. This comparison does not partition those mechanisms.
Neither estimator is identified as crop-field truth, and the regional
matched footprint cannot certify nationwide 2020–2025 weather-measurement
robustness. No yield response, climate-attributable change, damages or SCC
was estimated here.

Protocol: `US_COUNTY_WEATHER_ESTIMATOR_COMPARISON_PROTOCOL_20260916.md`.
Code: `scripts/compare_us_county_weather_estimators.py` and
`scripts/validate_us_county_weather_estimators.py`. Ignored result and
validation SHA-256: `3259b19bd70ac7f37d19ef91f8939ed4a7fc553e0d503a6cffd4ebae11000efe`
and `e5c8553643e898dcb64bc20d8c87babf24daadab3dccfa928dbead1cc185a7f3`.
