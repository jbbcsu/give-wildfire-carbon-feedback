# Nationwide U.S. daily county-weather prediction: preliminary result

## What was tested

The frozen `US_COUNTY_AVERAGE_RESPONSE_PREANALYSIS_20260916.md` specified a
crop-by-crop log-yield prediction ladder: county fixed effects plus a time
trend; then crop-season precipitation amount and its square with mean
temperature and heat; then wet-day frequency, maximum dry spell, maximum
five-day rain and two within-season rain shares. The same official
[NOAA nClimGrid-Daily](https://www.ncei.noaa.gov/metadata/geoportal/rest/metadata/item/gov.noaa.ncdc%3AC01589/html)
county-average weather estimator was used for 1981–2019 fit and 2020–2025
testing. The fixed 2010
[USDA NASS crop calendar](https://www.nass.usda.gov/Publications/Todays_Reports/reports/fcdate10.pdf)
was extended to 2025 only after all 10,920 earlier 1981–2022 rows matched
exactly. NASS county yields are [Quick Stats](https://www.nass.usda.gov/Quick_Stats/)
`ALL PRODUCTION PRACTICES`, restricted by a numeric <=10% 2017 Census
irrigated-acreage share and the preexisting 2019 TIGER geography gate.
**They are not observed non-irrigated yields.**

The source acquisition contains 540 months, 2,160 daily CSVs plus 540
version texts, 3,107 source counties per month, and 2,362,010,369 bytes.
Forty-five annual feature partitions cover 254,205 crop-county-years;
independent raw-CSV reconstruction passed 608 numeric checks. The screened
NASS/weather join retains 30,213 historical and 4,075 terminal crop-county-
year rows. All terminal rows belong to counties seen historically. The
independent within-estimator reconstruction passed 68 coefficient/score
checks. Maximum sampled RSS among the downstream workers was 271.1 MiB;
the free-disk floor of 130 GiB was maintained.

## Prespecified predictive comparison

Scores are root-mean-squared error in **log yield**, on identical terminal
county-years for each crop. A positive improvement means lower forecast error;
it is neither a yield-effect coefficient nor a climate damage.

| Crop | 2020–25 rows | County/time only | Rain amount + temperature/heat | Plus timing/extremes | Increment from timing/extremes |
|---|---:|---:|---:|---:|---:|
| Corn grain | 2,086 | 0.20494 | 0.18291 | 0.18224 | 0.00067 |
| Soybeans | 1,989 | 0.18919 | 0.15546 | 0.14781 | 0.00766 |

For corn, timing/extremes improve the score in four of six terminal years,
but worsen it in 2023 and 2025. Its 1981–2010-fit/2012–2019 diagnostic
also **worsens** slightly (0.19036 quantity/temperature versus 0.19107
with timing/extremes). A paired state bootstrap conditional on the fixed
2020–2025 forecasts gives a 95% percentile interval of −0.00241 to +0.00330
log-yield RMSE points for the incremental timing/extreme gain. This does not
support promoting corn timing features over the parsimonious quantity model.

For soybeans, timing/extremes improve RMSE in all six terminal years and in
the non-pristine 2012–2019 historical diagnostic (0.17654 to 0.16668).
The paired conditional state-bootstrap interval for its terminal incremental
gain is +0.00228 to +0.01415 log-yield RMSE points. That is encouraging
**predictive** evidence for the joint moisture-pattern feature group, not
evidence that any single timing metric is causal or that the gain transports
globally. The conditional bootstrap resamples states with fitted forecasts
held fixed; it does not account for only six terminal years, source revisions,
prior model-family exploration, or all parameter/model uncertainty.

Rain amount plus temperature/heat improves terminal RMSE over the county/
time-only baseline by 0.02203 for corn and 0.03372 for soybeans. The paired
conditional state-bootstrap interval crosses zero for corn (−0.00270 to
+0.04730), but not soybean (+0.00834 to +0.05944). The 2023 corn weather
model is worse than no weather. These facts argue against an across-crop
headline effect from a single predictive metric.

## Post-result state-trend sensitivity

After seeing the primary scores, we registered a clearly labeled robustness
test that replaces the one common linear yield trend with separate historical
state trends while keeping weather terms, counties and terminal keys fixed.
This is **not** independent confirmation. With state trends, corn's no-weather/
quantity-plus-temperature/+pattern RMSEs are 0.19582/0.17633/0.17525;
the pattern increment remains small, with a conditional paired state-bootstrap
interval of −0.00320 to +0.00517 and two years worsening. Soybean's analogous
scores are 0.19001/0.15742/0.14769; its joint pattern group improves all
six terminal years, with a conditional interval of +0.00287 to +0.01474.
The blocked historical diagnostic also improves for soybeans (0.17190 to
0.16261) but worsens for corn (0.18630 to 0.18786). An independent pandas
within-estimator reconstruction passes 36 numerical score checks. This
reduces concern that the soybean predictive increment is solely an artifact
of a common national time trend, but does not address omitted yield drivers,
weather measurement, causal identification or global transport.

## Scientific boundary and next tests

The weather model changes rain and temperature terms jointly; these scores
do **not** isolate precipitation from temperature, CO2, adaptation or other
climate drivers. County-average precipitation and its daily extremes may
smooth crop-field exposure; fixed 2010 planting/harvest windows are not
realized yearly phenology. The 2017 irrigation screen is a sample proxy,
not annual practice classification. Historical holdouts and model families
were previously examined, so the 2020–2025 block is an additional temporal
stress test, not a pristine discovery sample. The common linear time trend
is extrapolated beyond 2019 for every terminal observation; non-time weather
features have almost no marginal min/max extrapolation. These are U.S.
observational predictions, not anthropogenic precipitation attribution,
global agriculture damages, monetary losses, GIVE integration or SCC.

Next: (1) stress-test state-specific trends, 2017-share thresholds, county
composition and crop-field versus county-average exposure; (2) compare the
registered PDSI/scPDSI/SPEI moisture-index alternatives without additive
double counting; (3) explore which prespecified moisture-pattern subgroup
drives soybean predictive gain, explicitly labeled as **post-result
exploration**; (4) compare direct non-irrigated historical NASS series with
the all-practice proxy; (5) keep global climate-forcing, crop-response,
economic replacement and SCC gates separate. Any revised primary model must
be fixed and independently validated before publication claims.

## Reproduction and hashes

- Full ignored NOAA acquisition summary: SHA-256
  `8bac1b3f3f661a5fc34bcb6cafa75dc18440183ee885f5555a25dad1923e1f69`.
- Calendar extension result: `a15ea5aa01d6ca49a1b09ef33122caf287cc6ac550669ed599b4c72a3bf28d84`.
- Annual feature summary: `128755a065353759ad53bc4bc5625609daf9e6c83e0a1379d8c7adba48b13243`.
- Independent feature check: `ae19edd2cd21569ad517118e2397952af1a715e9b0c23e6f45b149104b82af4f`.
- NASS/weather panel receipt: `5d65c9b8261d21945108df3fda881b5503b5ec265df08b7ba1b802139e26a730`.
- Prediction receipt: `1b4bba219b2d63cb4b14c57054ec8b0f5f9057bfd5d6c56aeba34fef691c1247`.
- Independent prediction check: `96409ae8524dac7d06ac284afa4650f54a2fe97a21c760fe73e40b4e5092e6e4`.
- Post-result state-trend sensitivity: `0f2830ca3c1d10513ef4733e2ea87fa56798a5a48e55e65f12c59592d96f1248`;
  independent reconstruction: `ceb09572900eb8b2607d72e5e47289005c29bfe4b6510d2cad747b2502371190`.

All these results and source CSVs are in Git-ignored `data/interim/` paths;
only code, protocols, this aggregate report and safe manifests are candidates
for a reviewed Git push. The run entry point is
`scripts/continue_us_county_average_analysis.py`, which enforces the above
sequence and stops on failed integrity/resource gates.
