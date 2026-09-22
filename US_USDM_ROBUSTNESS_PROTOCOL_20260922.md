# U.S. USDM coefficient-robustness protocol

**Frozen:** 2026-09-22, after the primary drought/weather estimates were
reported but before any state-cluster or leave-one-state-out result was fit.

## Goal and boundary

This sensitivity asks two narrow questions about the historical
drought-plus-weather benchmark: (1) do uncertainty statements change when
residual dependence is clustered at the state rather than county level; and
(2) is any reported drought coefficient driven by deleting one state? It does
not repair the county-area versus agricultural-area exposure difference, does
not reproduce the paper's spatial HAC estimator, and does not create a causal,
damage, global-transfer, or SCC coefficient.

## Frozen design

- Use the identical 2001--2013 common panel, all-cropland irrigation
  classifier, D0--D4 calendar-year exposures, April--September NOAA weather
  controls, fixed effects, and state trends as the reported
  drought-plus-weather models.
- Reproduce each full-sample coefficient before calculating any sensitivity.
- Compute a full-sample state-cluster CR1 covariance using a Student-t
  reference with `G-1` degrees of freedom. Report every term; county-cluster
  inference remains the registered primary provisional result.
- Delete each state represented in each crop/support sample exactly once,
  refit all terms, and retain all coefficient vectors. Do not delete multiple
  states, change controls, or tune the specification after seeing results.
- For each coefficient report the full estimate, deletion minimum/median/
  maximum, maximum absolute change and responsible state, and the fraction of
  deletions with the same nonzero sign as the full estimate.
- An independent validator will solve the full and deterministic sentinel
  deletion models as one joint sparse design rather than using the production
  Frisch--Waugh path.

The supplement archive listed by the publisher could not be retrieved through
the permitted download route. Consequently, no unpublished bandwidth or mask
setting is inferred. Agricultural-area weighting and spatial-HAC inference
remain separate advancement gates.
