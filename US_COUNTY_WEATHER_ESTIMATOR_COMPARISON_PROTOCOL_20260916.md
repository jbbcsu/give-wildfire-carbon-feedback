# Source-only U.S. weather-estimator comparison, post-result

The county-average NASS prediction scores were inspected before this
comparison. This is a **weather-measurement diagnostic**, not a newly
untouched yield test. Reuse the existing 1981–2019 NOAA nClimGrid-Daily
cell-first TIGER polygon-weighted practice-specific panel and the new
NOAA county-area-average corn/soy crop-year feature partitions. Read only
the weather, key, and fixed-calendar fields from the former—never its
practice-specific yield. First require the irrigated and non-irrigated
rows to have exactly matching weather and calendar values on every old
crop/county/year key, then collapse their duplicate exposure. Audit old
key support, exact-key join to the new source, and exact season-start/end
agreement. Compute paired differences **only on exact calendar matches**;
report exclusions rather than forcing an alignment.

Freeze the candidate fields before seeing differences: seasonal rainfall
total, seasonal mean temperature, wet-day count (only if thresholds match),
maximum dry-spell duration, Rx5day, and stage-1/stage-2 rainfall shares.
For each field and crop report matched count, signed mean, median and 95th
percentile absolute difference, RMSE of the difference and correlation,
with source units. Report counts of missing/nonfinite values rather than
turning them into zeros. This is a comparison of two *different spatial
estimators* over the older regional practice-specific geography; it is not
nationally representative and not a revision correction or crop-field truth
test. Nonlinear features computed after county averaging need not equal
polygon-weighted cell-first nonlinear features.

Pin old source, new partition summary and script hashes. A separate
deterministic scalar reconstruction must validate selected rows and the
aggregate arithmetic before presenting any differences. Use a single
<=512 MiB sampled-RSS worker, <=16 MiB new ignored output and >=130 GiB
free-disk reserve. This stage supplies no new causal yield estimate,
climate-driven change, damages or SCC.
