# Daily heat-control pilot

Implement daily Tmax threshold exposure for the existing Cuming County,
Nebraska, 1981 corn/soy fixed-calendar measurement pilot. The county/year
was used previously for feature validation; it is not selected based on the
new heat result. Use retained nClimGrid files only, with full acquisition
SHA-512 checks and existing county-polygon weights. No acquisition.

Compute sum(max(Tmax - threshold, 0)) in Celsius-days and count(Tmax >
threshold) for season and three existing stages, separately at 29 and 30 C.
These inherited global-pipeline thresholds are sensitivity features, not
estimated biological optima. Apply the nonlinear transform at each weather
cell BEFORE county-polygon area weighting. Also calculate the county-average-
temperature-first version to measure aggregation bias; it is not primary.

Reconcile stage totals, original stage Tmax means, calendar day counts and
weight coverage. This metric is daily-maximum exceedance, not hourly growing
degree days or an inferred response coefficient. County-polygon exposure is
not crop-pixel weighting. Shared weather does not identify irrigation
differences. A four-record pilot cannot estimate crop damages or SCC.

One monitored job under 1 GiB; only small aggregate JSON output. On success,
use the module in a subsequent bounded county/year expansion without changing
existing hash-bound feature files. Do not jump from this pilot to national
response estimation.
