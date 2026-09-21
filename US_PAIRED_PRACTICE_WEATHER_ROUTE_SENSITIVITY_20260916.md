# Post-result weather-route sensitivity of historical practice-yield gaps

The original regional NASS irrigated/non-irrigated association results and
the new nationwide all-practice forecast scores were already inspected
before this sensitivity. This is **not** an independent discovery test or
an irrigation-treatment design. Its purpose is to test whether the
existing paired-practice descriptive associations materially change when
the shared weather exposure is calculated using the newer official NOAA
county-area-average route instead of the older gridded cell-first polygon
route. The two routes have exact crop-calendar and key overlap for the
relevant regional sample, as verified in
`US_COUNTY_WEATHER_ESTIMATOR_COMPARISON_RESULTS_20260916.md`.

Use precisely the old directly reported NASS irrigated/non-irrigated
positive-yield pairs for corn and soybean in 1981–2018; exclude sparse
2019 exactly as the old contract did. Source counties, crops, practices,
years, outcome values, calendar dates, county/state identifiers and fixed
effect groups must be identical. Read *only* the replacement weather fields
from the validated NOAA county-average crop-year partitions and join by
crop/county/year after checking exact season dates. Do not use terminal
all-practice outcomes or change the primary practice pair. Require exact
paired completeness and the original crop-specific row/county counts before
fitting. The old and new route differ only in weather exposure, though
revision/estimator differences cannot be separately identified.

Reuse the immutable registered old analysis model contract: paired outcome
`log(irrigated yield)-log(non-irrigated yield)`; quantity and
quantity-plus-stage-share forms; three stage-mean temperature controls each
linear/quadratic; seasonal rainfall linear/quadratic; county and state-year
fixed effects; county-clustered sandwich uncertainty; same +100 mm at
crop-specific median and 10-point middle-versus-late share contrasts.
Report all four crop/form fits, but retain the previously selected corn
quantity and soybean quantity-plus-timing forms as primary descriptors.
Compare their coefficients/contrasts to the prior result without selecting
the route that yields a stronger association. Because both weather routes
are based on NOAA products and neither is field-level truth, agreement
would be measurement robustness *within the old selected geography* only.

Pin the old outcome panel, old frozen config and result, validated new
weather-feature summary and 39 partitions, weather-route audit and new
script hashes. A separate reconstruction must check sample identity,
weather join and fitted coefficient contrasts. Use one bounded <=512 MiB
sampled-RSS worker, <=16 MiB new ignored output and >=130 GiB free disk.
Do not emit per-row outcomes/predictions or promote historical conditional
associations to causal rainfall, adaptation, global damage or SCC claims.
