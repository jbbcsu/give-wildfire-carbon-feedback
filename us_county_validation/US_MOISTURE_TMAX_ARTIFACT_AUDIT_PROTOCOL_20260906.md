# Preregistered moisture/Tmax artifact audit

## Purpose

Independently validate the saved aggregate artifact behind
`US_MOISTURE_TMAX_RESULTS_20260905.md` without reopening the retained county
panels or refitting any model. This is a storage-light integrity and claim
reconciliation step for the precipitation-first U.S. validation track.

## Frozen inputs

- `data/provenance/us_moisture_tmax_sensitivity_verified_20260905.json`
  (SHA-256 `49aa943d48dddfb2f5e6b946525127d50fe695783e6272d580bddccedf1524dd`)
- `data/provenance/us_competing_moisture_independent_audit_20260826.json`
- `us_county_validation/scripts/evaluate_moisture_tmax_sensitivity.py`
- `us_county_validation/scripts/evaluate_us_competing_moisture.py`
- `us_county_validation/US_MOISTURE_TMAX_PROTOCOL_20260905.md`
- `us_county_validation/us_competing_moisture_predictive_v1.toml`

The audit must verify the hashes already stored in the sensitivity artifact
against the current tracked files and the independent-audit hash ledger. It
must not substitute the untracked first-attempt output.

## Prespecified checks

1. Require the exact artifact schema, top-level fields, baseline and
   additional-stage-Tmax labels, six named added controls, and false
   causal/damage/SCC authorization gates.
2. Require 120 unique aggregate metric keys per specification: corn and
   soybean, irrigated and non-irrigated, five mutually exclusive moisture
   models, the exact eligible leave-state-out groups, one terminal-time split,
   and one precipitation-tail split. The two specifications must have
   identical scored support.
3. Require finite aggregate metrics, positive train/test sizes, exact
   first-difference endpoint-disjoint flags, and full-rank retained designs.
   Model-invariant sample counts must agree within every scored split. The
   added-Tmax specification must add exactly six candidate features to every
   matched baseline model.
4. Recompute every distribution-versus-quantity RMSE improvement, materiality
   floor, excess over the floor, mean geographic improvement, terminal and
   tail improvement, and quantity-versus-seasonal-PDSI comparison directly
   from the saved metric rows. Require exact agreement within `1e-12`.
5. Require the registered qualitative result: soybean distribution passes the
   frozen geographic promotion rule with baseline controls and fails with the
   richer Tmax controls; corn fails under both specifications. Confirm that
   non-irrigated soybean distribution still improves RMSE in AR, KS, and NE
   under the richer controls, with only NE below its materiality floor.
6. Reconstruct the non-irrigated terminal RMSE table for all five model
   families under both specifications. The audit output may contain only
   aggregate checks and derived summary values, never coefficients or
   row-level predictions.

## Fixed output and interpretation

Write `data/provenance/us_moisture_tmax_artifact_audit_20260906.json` with
input hashes, support counts, maximum reconciliation errors, promotion states,
the aggregate terminal table, and explicit false causal, damage, welfare, and
SCC gates. Add tiny synthetic tamper tests for hashes, metric keys, support,
rank, sample-count consistency, summary arithmetic, and semantic gates.

Passing this audit would establish internal reproducibility of the saved
aggregate artifact and its written summary only. It would not independently
replicate the climate exposure, sample construction, model fit, causal
identification, damage function, welfare accounting, or SCC calculation.
