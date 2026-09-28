# MIRCA Rice1/Rice2 outcome-crosswalk audit protocol

**Formalized 2026-09-28 after preliminary support counts were inspected.**
Accordingly, this is a transparent coverage audit, not a preregistered
hypothesis test; no threshold is presented as outcome-blind.

## Question

Do the year-2000 proportionally reconciled MIRCA Rice1/Rice2 candidate weights
map exactly to the locked 0.5-degree GDHY/GGCMI first- and second-rice outcome
and calendar panels, and what support would be lost by requiring the weights?

## Mapping

- `Rice1 -> ri1` and `Rice2 -> ri2`, following the MIRCA README's numeric
  multiple-cropping semantics and the existing locked outcome labels.
- Join only on exact 0.5-degree cell-center latitude and 0--360 longitude.
- Do not nearest-neighbor match, fill, country-average, renormalize, or move
  Rice3 into either observed season.
- Collapse the eight-year panel to one calendar row per crop cell only after
  verifying that planting day, maturity day, season length, and GDHY source
  identity are constant in the required crop/source sense.
- A positive-outcome cell is a cell with at least one strictly positive,
  explicitly observed GDHY yield during 1982--1989.

## Reported coverage

For each crop, report panel calendar cells, positive-outcome cells, weight
cells, exact matches, unmatched counts, candidate-area fractions on calendar
and positive-outcome support, and the number of weighted positive-outcome
cells. For cells with both calendars, report identical-calendar counts and
circular planting-day separation quantiles. These timing summaries are
descriptive; the numeric season names do not imply a universal January-to-
December ordering.

## Gate

The primary unrepaired MIRCA source remains blocked. The repaired table can be
described as a candidate sensitivity only. Production eligibility requires
100% exact coverage of positive-outcome cells or a separately frozen missing-
support estimand and sensitivity; this audit itself cannot choose the latter.
All response, causal, valuation, damage, and SCC gates remain closed.
