# U.S. direct-practice daily heat expansion

## Purpose and frozen support

Expand the validated single-county daily-Tmax pilot to the exact corn and
soybean county/crop/year support already present in the completed direct-
practice nClimGrid feature partitions for 1981--2019.  This is a separate
heat-only input.  It must not modify the existing weather or yield panels.
Weather exposure remains a fixed 2019 county-polygon proxy shared exactly
between irrigated and non-irrigated outcomes.

## Construction

Process one harvest year per checkpoint through `scripts/run_bounded_job.py`
with a 1 GiB sampled process-group RSS limit, one numerical thread, a small
log and a run-specific disk floor no lower than freshly measured free space
minus 64 MiB.  Use only local, previously acquired nClimGrid daily files and
validated county-weight partitions.  Never download or rehydrate a missing
file.

Within a year, verify each required monthly payload once against the reviewed
acquisition manifest, retain that verified identity in memory, and reuse the
loaded selected-cell arrays across all counties and crop calendars.  Detect a
changed file before emitting the checkpoint.  Apply `max(Tmax-threshold,0)`
and `Tmax>threshold` at each grid cell before county-area weighting.  Calculate
season and fixed equal-duration stage values at 29 and 30 C.  Retain the
county-mean-temperature-first exceedance only as an aggregation-order audit.

Every checkpoint must reconcile exact county/crop/year keys, calendar dates,
stage days, stage-to-season exceedance totals, linear Tmax means, climate
payload identities and county-weight hashes to its source year receipt.  The
final assembly must contain exactly one heat row per county/crop/year and must
join one-to-many without changing either irrigation-practice outcome.

## Interpretation and gates

The thresholds are inherited sensitivity bases, not fitted crop optima.  The
features are historical weather measurements, not yield responses.  No
coefficient, row prediction, model promotion, causal attribution, future
projection, FAIR run, damage, welfare or SCC use is authorized by this step.
The separate moisture-model sensitivity may begin only after all 39 year
checkpoints and their aggregate receipt pass validation.  Null and adverse
results must be retained.
