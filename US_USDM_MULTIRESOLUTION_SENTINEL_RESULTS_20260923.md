# USDM agricultural-area multi-resolution sentinel results

**Status:** completed, independently reproduced, and **failed the frozen
3.96 km advancement gate**. The failure is retained without changing the
sentinels or thresholds. This is a spatial-measurement result, not a causal
yield, damage, future-drought, global-transfer, or SCC result.

## Design

Before constructing a finer grid, the protocol selected eight counties using
only 3.96 km cultivated-area support and USDM boundary ambiguity. Counties span
eight equal-count agricultural-area strata and eight states. Within each
county, the three most ambiguous USDM weeks separated by at least 28 days were
fixed, yielding 24 county-weeks and 48 mask-specific comparisons. No yield,
coefficient, fit, significance, damage, or SCC information entered selection.

Two comparisons were then run:

- all 679 weekly maps and all 13 harvest years were recomputed at 990 m for the
  eight counties and compared with 3.96 km annual exposures; and
- all agricultural 30 m CDL pixel centers were classified directly for the 24
  frozen county-weeks, providing a native reference for both 3.96 km and 990 m.

The 990 m grid contains 81,471 rows and 63,809 unique support cells. Grid,
exposure, and native-worker peak RSS values were 488,521,728, 512,442,368, and
587,120,640 bytes, respectively, all below the 640 MiB ceiling. All weights,
exclusive categories, 679-map coverage, annual calendars, source identities,
and native pixel counts passed independent checks.

## Results

Total variation distance (TVD) is one half the sum of absolute differences
across the six mutually exclusive none/D0/.../D4 shares.

| Comparison | N | Median | 90th percentile | Maximum |
|---|---:|---:|---:|---:|
| 3.96 km versus native 30 m weekly TVD | 48 | 0.0070 | 0.0409 | 0.1779 |
| 990 m versus native 30 m weekly TVD | 48 | 0.00149 | 0.00537 | 0.01145 |
| 3.96 km versus 990 m annual absolute category difference (weeks) | 1,040 | 0.0064 | 0.1084 | 1.5174 |

The typical-error gates pass by wide margins, and 990 m is materially closer
to native 30 m. The two frozen maximum-error gates fail:

- Webb County, Texas (`48479`), cultivated mask, 13 February 2007 has 3.96 km
  TVD 0.1779 versus the 0.15 limit. Its 990 m TVD is 0.01145.
- Webb County, cultivated mask, harvest-year 2013 D3 exposure differs by
  1.5174 equivalent weeks between 3.96 km and 990 m versus the 1.00-week limit.

Webb County has only 42.59 km2 of cultivated support in the frozen 2008 mask.
Its sparse cultivated cells make center assignment at 3.96 km particularly
sensitive to drought boundaries. The failure is concentrated rather than
typical, but the protocol explicitly requires the maximum thresholds as well
as median and 90th-percentile thresholds; therefore concentration does not
justify overriding it.

## Decision

The 3.96 km national exposure is retained as a transparent diagnostic, but it
is rejected as the final agricultural-area reconstruction. Its already-fitted
historical coefficients remain useful evidence that the broad U.S. conclusion
is not driven by whole-county weighting; they are not promoted as final
spatial-fidelity estimates.

The defensible remediation is a partitioned national 990 m rebuild. The
sentinel evidence supports 990 m as a close approximation to native 30 m while
remaining computationally feasible. The rebuild must process county/state
partitions independently so no national fine grid is resident in memory, then
merge only validated annual exposures. Response models must be rerun unchanged
after that reconstruction. No causal, global, damage, or SCC bridge opens as a
result of either this audit or its remediation.

The complete frozen selection, 48 weekly comparisons, 1,040 annual-category
comparisons, thresholds, decisions, hashes, and independent validation are in
`data/provenance/usdm_multiresolution_sentinel_selection_20260923.json`,
`data/provenance/usdm_multiresolution_sentinel_results_20260923.json`, and
`data/provenance/usdm_multiresolution_sentinel_validation_20260923.json`.
