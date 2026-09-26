# Rice direct-practice zero-count diagnostic

**Frozen:** 2026-09-25 after the primary exact-series screen returned zero
all-years counts for both rice practices and before any broader rice count.

The sole question is whether the primary zero reflects an overly narrow
class, utilization, domain, or unit descriptor, or the absence of county
`SURVEY` rice `YIELD` records labeled by production practice. Query the USDA
NASS Quick Stats count endpoint only, over all years, with source `SURVEY`,
sector `CROPS`, commodity `RICE`, statistic `YIELD`, aggregation `COUNTY`,
annual frequency, reference period `YEAR`, and JSON format. Make exactly three
queries: one with no production-practice filter, one with
`prodn_practice_desc=IRRIGATED`, and one with
`prodn_practice_desc=NON-IRRIGATED`. Deliberately omit class, utilization,
domain, and unit from all three.

If the broad unstratified count is positive while both broad practice counts
are zero, classify rice as blocked because the county survey yield series is
not practice-labeled, rather than because the primary unit/class filters were
too narrow. If either practice count is positive, the primary exact series is
mis-specified and requires a separately frozen descriptor audit. This
diagnostic never calls the data endpoint, downloads values, or changes the
primary count-feasibility threshold.
