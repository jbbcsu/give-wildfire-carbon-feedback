# MIRCA Rice1/Rice2 outcome-crosswalk audit results

## Decision

The proportionally reconciled MIRCA candidate maps well to first-rice positive
outcomes but incompletely to second-rice outcomes. It therefore remains a
sensitivity candidate and does not pass the strict production-weight gate.

| Outcome | Positive observed cells | Exact MIRCA matches | Match fraction | MIRCA area on any calendar support | MIRCA area on positive-outcome support |
|---|---:|---:|---:|---:|---:|
| First rice (`ri1`) | 9,564 | 9,298 | 97.22% | 99.951% | 68.51% |
| Second rice (`ri2`) | 1,587 | 1,419 | 89.41% | 99.724% | 57.48% |

There are 266 positive first-rice and 168 positive second-rice cells without an
exact season-weight match. No nearest-neighbor, country-average, or imputed
weight is used. Conversely, 153 Rice1 and 424 Rice2 weight cells lack the
corresponding locked calendar. The low fraction of all calendar cells with
weights (32.50% first rice; 27.13% second rice) mostly reflects broad climate-
calendar support outside MIRCA rice cultivation and is not treated as missing
production.

Across 31,005 cells with both locked calendars, only one has identical planting
and maturity days. The median circular difference in planting day is 99 days;
the 1st and 99th percentiles are 0 and 180 days. These are descriptive timing
checks only: Rice1/Rice2 names do not impose one universal calendar-year
ordering across hemispheres and cross-year seasons.

## Consequence

The strict requirement of complete positive-outcome coverage fails for both
crops, especially second rice. The next defensible options are to freeze an
explicit common-support estimand with attrition/area sensitivity or obtain a
publisher-consistent season map that covers the unmatched cells. This audit
does not choose between them. Season-specific moderators, future/pulse weather,
response evaluation, valuation, damage, and SCC remain closed.

The protocol explicitly discloses that preliminary support counts were viewed
before the formal audit; none of these coverage percentages is presented as a
preregistered threshold or statistical test.

## Artifacts

- Protocol: `MIRCA_RICE_OUTCOME_CROSSWALK_AUDIT_PROTOCOL_20260928.md`
- Audit: `scripts/audit_mirca_rice_outcome_crosswalk.py`
- Validator: `scripts/validate_mirca_rice_outcome_crosswalk.py`
- Receipt: `data/provenance/mirca_rice_outcome_crosswalk_audit_20260928.json`
- Validation: `data/provenance/mirca_rice_outcome_crosswalk_validation_20260928.json`
- Compact crosswalk: ignored
  `data/interim/mirca_os_v2/rice_season_outcome_crosswalk_audit_2000.parquet`
