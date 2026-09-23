# National 990 m USDM agricultural-area rebuild protocol

**Frozen:** 2026-09-23, after the preregistered 3.96 km sentinel gate failed
and before constructing or inspecting any nonsentinel 990 m exposure or
response result.

**Resource-only amendment, 2026-09-23:** after Colorado's validated state grid
reached 346,684 sparse rows, but before any Texas 990 m grid or response was
constructed, the runner added the whole-county chunk fallback described below.
The trigger uses grid row count only, retains every county and all 679 maps,
and does not inspect exposure values, yields, coefficients, signs, or fit.

## Purpose and claim boundary

Replace the rejected 3.96 km center-assignment approximation with the 990 m
resolution that closely matched native 30 m CDL support in the frozen sentinel
audit. This is a measurement-fidelity remediation. It does not change the
historical response specification and does not identify causality, project
future drought, authorize global transfer, estimate damages, or alter the SCC.

## Frozen scope

- All 2,909 continental counties in the outcome-independent reconstructed
  irrigation-classifier contract.
- The same official 2008 30 m CDL archive and the same two frozen masks:
  cultivated crops plus fallow/idle, and that mask plus Grassland/Pasture.
- The same 679 official weekly USDM vector maps and October--September harvest-
  year integration for 2001--2013.
- A `33 x 30 m = 990 m` equal-area aggregation grid, with USDM class assigned
  at each 990 m cell center and agricultural-pixel counts retained as weights.
- No county, mask, week, or response row may be removed based on the 3.96 km
  comparison, yield coefficient, fit, sign, significance, or agreement with
  published summary statistics.

## Partitioned computation

Each continental state or district is a deterministic partition. For each
partition, build and independently validate the 990 m sparse grid, prepare a
compact numeric overlay, apply all 679 maps in isolated map batches, and
independently validate annual exposure accounting. A batch exceeding 640 MiB
RSS is rejected and divided into single-map workers. If a state grid exceeds
250,000 sparse rows, it is further split in sorted county order into
deterministic whole-county chunks of at most 250,000 rows. Every chunk runs all
679 maps and its validator independently; chunk panels are accepted only when
their disjoint county support exactly reconstructs the validated state grid.
No national fine grid is resident in memory. Only validated state exposure
panels are merged.

The run halts if free disk falls below 100 GiB. Raw sources, state grids, and
batch intermediates remain ignored. Tracked receipts contain source/output
hashes, support counts, resource maxima, and validation decisions rather than
raw data.

## National acceptance gates

The merged panel must contain exactly two masks, thirteen harvest years, and
the expected 2,909 counties, with one row per county/mask/year. It must have no
duplicate or missing partition keys, no cross-partition county overlap, no
USDM class overlap, complete 365/366-day calendars, and category totals equal
to annual duration within numerical tolerance. Every state grid and exposure
validator must pass below 640 MiB.

After those gates pass, rerun the already-frozen exposure adapters,
drought-only fits, direct-weather hierarchy, state-cluster covariance, and
leave-one-state-out checks without changing terms, samples, or thresholds.
Report 990 m estimates beside whole-county and 3.96 km diagnostic results.
Independent joint-design validators must pass again. Only the 990 m results
may be described as the final agricultural-area spatial-fidelity sensitivity;
they remain historical, noncausal, and SCC-ineligible.
