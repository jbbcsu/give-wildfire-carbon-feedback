# U.S. Census of Agriculture direct-practice outcome support audit

## Purpose

Test a second, independent route to newer county outcomes after the NASS
state-survey route proved too sparse. The Census of Agriculture may report
production and harvested area separately for irrigated and non-irrigated corn
and soybean. If both quantities are available on common county keys, their
ratio can form an official-source practice-specific yield for 2012, 2017, and
2022. This audit queries counts only; it does not download values or calculate
yields.

## Frozen source queries

Use the USDA NASS Quick Stats count endpoint for the complete Cartesian product
of:

- source `CENSUS`, sector `CROPS`, aggregate level `COUNTY`;
- crops corn (`CORN`, utilization `GRAIN`) and soybean (`SOYBEANS`,
  utilization `BEANS`);
- production practices `IRRIGATED` and `NON-IRRIGATED`;
- Census years 2012, 2017, and 2022; and
- `AREA HARVESTED` in `ACRES` and `PRODUCTION` in `BU`.

All queries also require class `ALL CLASSES`, annual frequency, reference
period `YEAR`, and domain `TOTAL`. Store only key-free parameters and counts.
The ignored API key may never enter a URL, log, result, exception, or Git
artifact.

## Support rules fixed before counts

A crop/practice/year cell is *count-feasible* only when both the area and
production queries report at least 100 rows. This intentionally low screening
threshold only authorizes exact-record acquisition. After acquisition, a
separate preregistered gate must require at least 100 common county records
with positive numeric area and production, exact state/county identity, and
no disclosure suppression or unit mismatch. Two-wave prediction or change
analysis additionally requires common counties across the declared waves;
these count queries cannot establish that overlap.

No ratio may be constructed from state or national totals, mismatched county
sets, unpublished/suppressed values, or mixed practice definitions. Production
divided by harvested acres is a Census-year average yield proxy, not the NASS
survey yield series and not an irrigation treatment effect.

## Potential role and limits

If support passes, the three Census waves can provide a geographically broad
practice-specific benchmark for direct rainfall-pattern and drought families.
They do not provide annual terminal validation, and the sparse wave spacing
limits time-series identification. Any climate exposure must use independently
fixed crop/calendar weights. The result cannot be pooled with annual NASS
survey outcomes without an explicit source model and cannot by itself authorize
causal damages, global transfer, or SCC.
