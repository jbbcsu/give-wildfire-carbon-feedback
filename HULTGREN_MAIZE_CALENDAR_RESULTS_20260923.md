# Published maize crop-calendar audit

## Result

The source-exact maize crop-calendar transformation is now reproduced for all
412,282 rows of the recovered Hultgren et al. historical regression input. Of
these, 377,973 rows have complete calendar values and 34,309 do not, matching
the prior historical-response audit.

Across every complete row, an independent Python implementation exactly
reproduces:

- conversion of median planting and harvest day values to the source's fixed
  calendar-month thresholds;
- the inclusive local season length, including cross-calendar-year seasons;
- the one-based month-of-season ordering; and
- the published maize phase partition: month 1, months 2--4, and month 5
  through local harvest.

The complete rows contain 27 distinct planting-month/harvest-month/length
configurations. There are 225,589 same-calendar-year rows and 152,384
cross-calendar-year rows; 11,155 complete rows are for India and therefore use
the source's explicit agricultural-reporting-year convention. No mismatch was
found in planting month, harvest month, season length, or phase partition.

## Interpretation

This closes the crop-calendar bookkeeping portion of the published-response
projection contract. It does **not** yet reproduce daily GMFD weather, validate
administrative-unit versus grid-cell aggregation, establish future climate
features, or estimate agricultural damages or SCC.

The next empirical gate is to apply this exact calendar logic to primitive
historical precipitation and daily maximum temperature, then compare the
constructed monthly rainfall/GDD/KDD features against source-compatible
historical checkpoints. The locally available GSWP3-W5E5 daily archive can test
the implementation and historical aggregation choice, but it is a different
weather product from the paper's GMFD input and cannot be described as exact
GMFD replication.

## Reproduction

Run:

```bash
./.venv/bin/python scripts/test_hultgren_crop_calendar.py
./.venv/bin/python scripts/validate_hultgren_maize_calendar.py
```

The full-source validator reads six columns in 50,000-row chunks. Its
hash-bound output is
`data/provenance/hultgren_maize_calendar_validation_20260923.json`. Raw source
data remain ignored and are not redistributed.
