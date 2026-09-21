# Paired NASS irrigation-practice association: NOAA weather-route sensitivity

This is a **post-result historical measurement sensitivity**, not a new
causal irrigation estimate. The old NASS directly reported irrigated and
non-irrigated corn/soy yield pairs (1981–2018) are unchanged: 11,857
county-crop-year pairs, including 7,013 corn/361 counties and 4,844
soybean/255 counties. The older NOAA gridded cell-first polygon weather
features are replaced by official NOAA county-area-average features on
exact crop/county/year/calendar keys. The old model forms, fixed effects,
temperature controls, and county-clustered uncertainty are unchanged.

The fitted change in the *irrigated-to-non-irrigated yield ratio* associated
with +100 mm seasonal rainfall at the crop-specific median is:

| Crop | Form | Old polygon/cell-first | New county average |
|---|---|---:|---:|
| Corn | Rain quantity (previous primary) | −7.550% | −7.525% |
| Corn | Rain quantity + stage shares | −7.630% | −7.606% |
| Soybeans | Rain quantity | −4.047% | −4.033% |
| Soybeans | Rain quantity + stage shares (previous primary) | −4.324% | −4.306% |

In the secondary 10-percentage-point middle-for-late rainfall-share
contrast, the fitted ratio changes are −4.120% versus −4.112% for corn,
and −4.721% versus −4.694% for soybean (old versus new route). These are
*partial model contrasts*: correlated dry spells and heavy rain are held
fixed algebraically, not regenerated as a physical rainfall sequence.
The point estimates shift by only about 0.01–0.03 percentage points here;
the routes share outcomes and weather information, so this is not an
independent replication or a formal test of equality. A separate Arrow-
source, fixed-effect-projection, QR and county-cluster-sandwich
reconstruction passed **151** support, coefficient, standard-error and
contrast checks (maximum difference 6.93×10⁻¹⁴). Workers sampled 214
and 225 MiB RSS, below the 512 MiB guard. Source and result JSON remain
ignored; no row predictions were emitted.

Agreement on this old regional matched sample is useful measurement
robustness for the *historical conditional association*. It does not say
which county weather estimator is closer to field exposure, isolate an
irrigation treatment effect, validate the new national all-practice
2020–2025 forecasts, identify climate-induced precipitation changes, or
produce agricultural welfare/SCC damages. Practice reporting and adoption
are selected, both practices share county weather proxies, and the old
result's own causal and geographic caveats remain.

Protocol: `US_PAIRED_PRACTICE_WEATHER_ROUTE_SENSITIVITY_20260916.md`.
Code: `scripts/evaluate_us_paired_practice_weather_route.py` and
`scripts/validate_us_paired_practice_weather_route.py`. Ignored result and
validation SHA-256: `1ff7732ecfcaaf548fe105b40e23448117fb68f7ae93b02e773afd5ef7c269b9`
and `0aaa568bd1a1d8eff3de9cd2c957c5420807dc283c18c454b8d556cb62da7506`.
