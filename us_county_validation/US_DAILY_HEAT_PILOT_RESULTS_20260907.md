# Daily heat controls: first real-data construction passed

Existing Cuming County, Nebraska, 1981 weather and fixed corn/soy calendars
produced eight crop/practice/threshold records. All six monthly climate files
passed full acquisition SHA-512 checks; coordinates, units, day alignment,
weights, stage means and stage/season reconciliation passed. No downloads.

The county-area-weighted seasonal daily Tmax exceedance is 141.862 C-days
above 29 C and 96.130 C-days above 30 C. Area-weighted counts are 51.607 and
38.483 days, respectively; fractional counts arise from spatial weighting.
Both crop calendars include the same above-threshold days in this pilot.
These are weather measurements, not optimal thresholds or crop losses.

Applying the threshold after averaging daily temperature across the county
instead yields 141.586 and 95.621 C-days. The small pilot gaps demonstrate
why the implementation preserves cell-first nonlinear transformation; their
size is not a national bias estimate. Irrigated and non-irrigated records
share polygon weather exposure and do not identify adaptation differences.

The daily threshold basis is distinct from the stage-average Tmax controls
used in the September 5 response/prediction sensitivity. It is also distinct
from hourly heat degree days inferred from daily temperature ranges.

Run `us_county_validation/scripts/build_daily_heat_pilot.py --out NEW.json`
through the bounded job launcher. Canonical output:
`data/provenance/us_daily_heat_pilot_20260907.json`. Synthetic tests in
`test_daily_heat_pilot.py` check threshold equality, convexity/aggregation
order and invalid weights. The real-data run took 3.96 seconds and peaked
at 210,862,080 bytes (201.1 MiB) sampled process-group RSS.

## Next substantive step

Generalize to the hash-validated direct-practice county/year support, using
one county-year or bounded county group per checkpoint, existing calendars
and local monthly files. Preserve the original panel and write a separate
heat-only keyed input with provenance. Reuse each month's verified identity
within a run while detecting file changes; do not rehash all months for every
county. Keep the 1 GiB monitor, small outputs and disk preflight. Expand and
verify support before rerunning the competing rainfall/PDSI predictive
comparison and fixed-effect response sensitivity with daily heat controls.
Do not require a future-climate generator or another unrelated audit first.
No national response or SCC inference follows from this single-county pilot.
