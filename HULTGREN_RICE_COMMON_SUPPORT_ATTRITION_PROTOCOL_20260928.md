# Rice common-support attrition audit protocol

**Frozen 2026-09-28 before computing attrition contrasts.**

## Estimand under review

The candidate sensitivity estimand would restrict each rice outcome separately
to positive observed 1982--1989 GDHY crop-cell-years whose exact crop cell has
a proportionally reconciled MIRCA Rice1 or Rice2 weight. It would not fill
unmatched cells, transfer weights across rice seasons, or renormalize Rice3.

## Audit population and measures

For first rice and second rice separately:

- retain crop-cell-years with `yield_observed=true` and strictly positive yield;
- mark exact MIRCA weight support using the validated crosswalk;
- compare retained and excluded groups on yield, seasonal mean temperature,
  seasonal precipitation, wet days, maximum consecutive dry days, Rx1day, and
  Rx5day;
- report group means, pooled-standard-deviation standardized mean differences,
  positive-cell and cell-year retention, and year-specific retention;
- report latitude-band and unique MapSPAM-country-proxy distributions without
  inferring national representativeness.

The fixed latitude bands are below 30 S, 30--15 S, 15 S--equator,
equator--15 N, 15--30 N, and above 30 N. Country labels are used only when the
proxy assigns exactly one country; ambiguous/missing cells remain explicit.

## Diagnostic thresholds

This is a representativeness screen, not a statistical significance test. A
candidate common-support estimand is described as low-attrition only if, for
each crop, it retains at least 95% of positive observed cells, retains at least
90% of positive observed cell-years in every year, and all seven absolute
standardized mean differences are at most 0.25. Failure does not authorize
imputation; it requires either a restricted-estimand sensitivity with explicit
scope or a better season-weight source.

No response coefficient, causal interpretation, geographic winner/loser,
valuation, damage, or SCC calculation is authorized by this audit.
