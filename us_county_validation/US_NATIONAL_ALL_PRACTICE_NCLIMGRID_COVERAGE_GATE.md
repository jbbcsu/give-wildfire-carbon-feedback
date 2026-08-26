# National all-practice nClimGrid coverage gate

## Purpose and scientific boundary

This is a pre-estimation coverage audit for the national NASS all-practice
route. It asks whether each fixed-2019 TIGER county polygon is adequately
covered by cells that are valid in the reviewed January 1981 nClimGrid object.
It writes no county weights or weather features. It estimates no predictive
relationship, causal effect, agricultural damage, or SCC.

The audit is separate from the core weight builder. It uses the same polygon,
equal-area projection, grid-cell boundary construction, and validity mask, but
records a row for every one of the 2,628 outcome counties even when a gate
fails. A sub-threshold county is never assigned renormalized weights by the
audit.

## Locked primary rule

The all-practice weather contract was fixed before this audit. A county must
satisfy all three conditions:

1. projected polygon area differs from TIGER `ALAND + AWATER` by no more than
   3%;
2. the nClimGrid envelope covers at least 99.9% of the polygon; and
3. the intersection with weather-valid cells is at least 95% of TIGER
   declared land area.

The third denominator is land rather than total area so ordinary open water is
not automatically treated as missing land weather. The validity numerator is
still based on whole nClimGrid cells that are finite for precipitation and all
three temperature fields on every day in January 1981. This remains a legal
county-envelope proxy, not crop-pixel or average-farm exposure.

The primary analysis should exclude every county that fails any registered
condition. It should report the exact excluded outcome support. It must not
lower the 0.95 cutoff after observing failures. Sensitivity analysis should
instead repeat the validation on stricter 0.99 and 0.999 weather-valid-land
subsets. These restrictions address boundary/mask support; they do not solve
measurement error within the retained counties.

## Reproduction

From the precipitation project root:

```bash
./.venv/bin/python us_county_validation/scripts/test_audit_us_national_all_practice_nclimgrid_coverage.py
./.venv/bin/python us_county_validation/scripts/audit_us_national_all_practice_nclimgrid_coverage.py
```

The ignored county-level table and full audit are written under
`outputs/us_county/national_all_practice_nclimgrid_coverage_v1/`. The compact,
tracked receipt is
`data/provenance/us_national_all_practice_nclimgrid_coverage_gate_20260826.json`.
Every input and the county detail output is SHA-256 bound with project-relative
paths. The reference weather object is also checked against its reviewed
acquisition manifest and SHA-512 identity.

## Results

The completed 2026-08-26 audit evaluated all 2,628 registered counties. The
locked 0.95 primary gate retains 2,614 counties and 135,952 crop-county-year
outcomes, including 30,068 outcomes in the fixed-2017 10%-or-less-irrigated
sample. Fourteen counties fail; together they account for 587 outcomes. The
stricter 0.99 and 0.999 sensitivities retain 2,585/134,519 and 2,556/133,402
counties/outcomes, respectively. Their 10%-or-less-irrigated supports contain
29,800 and 29,416 outcomes.

The 14 primary failures are Davis UT, Northampton VA, Aransas TX, Charlevoix
MI, Trigg KY, Accomack VA, Weber UT, Leelanau MI, Ottawa OH, Ashland WI,
McCormick SC, Chippewa MI, Anne Arundel MD, and Box Elder UT. Their valid-area
fractions relative to declared land range from 0.674 to 0.943. Most are coastal,
Great Lakes, or Great Salt Lake counties where the fixed legal polygon and
weather-valid land mask interact. This supports applying the registered
exclusion, not weakening the threshold or imputing weather. Of the 587 failed
outcomes, 145 are in the primary high-rainfed sample (Northampton 67, Trigg 39,
and Accomack 39).
