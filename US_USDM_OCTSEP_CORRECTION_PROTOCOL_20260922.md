# U.S. USDM October--September correction protocol

**Frozen:** 2026-09-22, after a primary-source audit identified the temporal mismatch and before acquisition of year-2000 inputs or inspection of corrected estimates.

## Why this correction is required

Kuwayama et al. (2019, *American Journal of Agricultural Economics*, DOI
10.1093/ajae/aay037) define annual drought exposure by summing weekly
agricultural-area shares from October of the preceding year through September
of the harvest year. The first implementation incorrectly used January through
December. That calendar-year implementation is retained, unchanged, as a
transparent timing sensitivity; it is no longer described as matching the
published temporal design.

## Frozen correction

- Outcomes, crops, irrigation classifier, fixed effects, state trends, weather
  controls, inference, and claim boundaries remain unchanged.
- For harvest year `y`, each county's mutually exclusive D0--D4 exposure is the
  county-area fraction integrated over every day from `y-1-10-01` through
  `y-09-30`, divided by seven to obtain area-equivalent weeks.
- The raw archive is extended to 2000 so harvest year 2001 has complete
  preceding-October coverage. All 41 outcome states remain in scope.
- Intervals must be complete, nonoverlapping, and gap-free. Category totals must
  reconcile to 365/7 or 366/7 weeks within the pre-existing rounding tolerance.
- The drought-only and April--September weather-hierarchy models are rerun on
  the corrected exposure. The weather window remains April--September because
  that is a separate direct-weather control definition.
- Corrected and calendar-year coefficients are compared without selecting a
  preferred result by sign or significance.

## Remaining non-replication

The official county-statistics service weights the full county area. The paper
intersects weekly drought maps with agricultural land, using the 2008 Cropland
Data Layer. Therefore the corrected result matches the published time window
but is still not an exact spatial exposure replication. It remains a historical,
noncausal external-validation benchmark and is not a future drought projection,
damage function, global response, or SCC input.
