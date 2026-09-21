# U.S. irrigation-share screen sensitivity: post-result forecast robustness

This analysis implements the <=20/30% and 2022-vintage sample screens stated
in the earlier nationwide pre-analysis record, **after** the <=10% main
scores had been inspected. It is not independent confirmation. The outcome
at every cutoff remains USDA NASS county `ALL PRODUCTION PRACTICES` yield,
not directly observed non-irrigated yield. The denominator, county mix, and
yield distribution change across screens; cross-screen RMSEs must not be
interpreted as effects of irrigation.

The fixed 2017 <=10% screen exactly reproduces the validated primary
34,288-row NASS/NOAA panel and model scores. All six screens use the same
1981–2019 fitting years, 2020–2025 test years, county fixed effects,
common time trend, NOAA crop-year weather estimator and three prespecified
models. Shares must be numeric and source-eligible. A separate source-panel
and pandas within-OLS reconstruction passed **498** sample-key, coefficient,
terminal-score and historical-blocked-score checks. The first attempt
correctly stopped before fitting because the Census share file includes
non-corn/soy crops; the selector was restricted to the registered crops
before the successful run. Both retained job logs show NumPy matrix-
operation runtime warnings in some repeated fits. All reported coefficients,
forecasts and scores are finite; rank, condition (maximum 63.19), residual
orthogonality and independent numerical checks pass. The warnings are
disclosed rather than silently suppressed. The successful fit and validator
sampled 448 and 452 MiB RSS, below their 512 MiB guards; raw/interim
artifacts remain ignored.

Terminal log-yield RMSE (lower is better) on each screen's identical
quantity and pattern-model rows:

| Census screen | Corn scored rows | Corn total+temperature | Corn +pattern/extremes | Soy scored rows | Soy total+temperature | Soy +pattern/extremes |
|---|---:|---:|---:|---:|---:|---:|
| 2017 <=10% (primary) | 2,086 | 0.18291 | 0.18224 | 1,989 | 0.15546 | 0.14781 |
| 2017 <=20% | 2,625 | 0.19161 | 0.19123 | 2,315 | 0.16609 | 0.15836 |
| 2017 <=30% | 2,892 | 0.20525 | 0.20512 | 2,463 | 0.17085 | 0.16491 |
| 2022 <=10% | 2,386 | 0.17425 | 0.17479 | 2,442 | 0.15173 | 0.14517 |
| 2022 <=20% | 2,919 | 0.18867 | 0.18883 | 2,796 | 0.15904 | 0.15216 |
| 2022 <=30% | 3,219 | 0.19886 | 0.19941 | 2,937 | 0.16389 | 0.15745 |

At each fixed-2017 threshold, soybean's *joint* wet-day/dry-run/Rx5/stage-
share extension improves pooled recent prediction. Its six annual signs
are positive at <=10/20%; at <=30%, 2023 is essentially zero/slightly
negative. The conditional paired state-bootstrap 95% interval for the
quantity-minus-pattern RMSE difference remains positive at all fixed-2017
screens: [0.00228,0.01415], [0.00281,0.01346], and [0.00085,0.01143].
These intervals condition on fitted forecasts, do not account for the
post-result screen comparison or only six test years, and are not causal
confidence intervals. Corn's corresponding increments are only
0.00067, 0.00038 and 0.00013, with mixed annual signs and intervals crossing
zero. In the 2022-vintage composition screens, soybean's pooled pattern
increment remains positive, but 2021's annual sign reverses; the 10%
bootstrap interval includes zero. Corn's pooled pattern increment reverses
sign at all three 2022 thresholds. The historical blocked results and full
annual and conditional-bootstrap ledger remain in the ignored result JSON.

The 2022 Census selector uses information from *within* the 2020–2025 test
period and crop irrigation can itself respond to weather/economic outcomes;
it is therefore not a prospectively fixed validation cohort. Widening any
screen admits more irrigated acreage into an all-practice county outcome.
These findings support the narrow conclusion that soybean pattern features
retain predictive value under alternative low-irrigation-share proxies,
while corn does not show a robust incremental gain. They do **not** identify
an irrigation effect, isolate precipitation from temperature, establish
climate-driven pattern change, transfer globally, value agricultural losses,
or alter GIVE's SCC.

Reproduction: `US_COUNTY_AVERAGE_IRRIGATION_SCREEN_SENSITIVITY_20260916.md`,
`scripts/evaluate_us_county_average_irrigation_screens.py`, and
`scripts/validate_us_county_average_irrigation_screens.py`. SHA-256 receipts
for ignored result and independent validation JSON are respectively
`f5a1effbbe647772ffc8fb34b53eed585490c2b0fdc70a27cc1c0b70ee38536b`
and `7e47618c2f238504ac2233488c4fe238ae1405a073aa14c4ed4e749e5822c0ee`.
