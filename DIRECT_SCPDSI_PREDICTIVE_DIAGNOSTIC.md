# Direct precipitation quantity versus historical scPDSI diagnostic

## Purpose and scientific boundary

This diagnostic asks a deliberately narrow predictive question: on the same
historical maize or soybean crop-grid-year outcomes, does seasonal
precipitation quantity or historical scPDSI improve held-out first-difference
yield prediction beyond an identical temperature-and-heat control basis?

It is not a causal response estimate. It does not choose the production
agricultural response, generate response draws, project future scPDSI,
calculate damages, or calculate an SCC. Predictive ranking cannot cross any of
those boundaries without a separate identification, projection, and welfare
authorization. Model ranking by SCC magnitude is prohibited.

The diagnostic is separately authorized for nonproduction OLS fitting. Its
coefficients and row predictions are suppressed by construction. Only
aggregate out-of-sample loss metrics are written.

## Evidence-led model hierarchy

The five locked models are:

1. common controls only;
2. common controls plus one seasonal `log1p(precipitation)` first difference;
3. common controls plus one seasonal-mean scPDSI first difference;
4. an explicitly secondary seasonal scPDSI summary using mean, minimum, and
   fraction at or below -2; and
5. an explicitly secondary three-stage scPDSI-mean model.

The one-column direct-quantity and seasonal-mean scPDSI models are the primary
matched-dimension comparison. The richer scPDSI models are separate registered
alternatives, not terms added to direct precipitation. No model stacks direct
precipitation and scPDSI, and version 1 contains no moisture-by-heat
interaction. A seasonal-quantity model may remain primary if richer moisture
summaries do not provide robust held-out value. Null or worse predictive
performance must be reported plainly.

## Outcome and support

The builder revalidates all four existing direct/scPDSI common-support bundles
(maize and soybean for 1982–1989 and 2012–2016) from their immediate candidate
inputs. It also binds the SHA-256 and status/gates of the direct, scPDSI,
common-support, and heat validation receipts plus the direct/scPDSI allocation
audits. Panel and fixed-weight hashes must agree exactly across the direct,
scPDSI, and heat families. These receipt bindings do not
claim that the diagnostic reruns raw climate construction; the audit records
`raw_source_recomputation_performed=false`.

Each common bundle must be completely covered by a separate validated
heat-control table. Every heat-source key and outcome must first match its
validated direct-candidate basis. The heat source may contain additional
direct-candidate keys, but the builder retains only whole keys on
direct/scPDSI common support,
requires exact `yield_observed` and `yield_t_ha` agreement there, and audits
every heat-only row excluded. Stage mean temperatures must also agree exactly
between the heat and direct-candidate bases. Missing common keys fail. The heat table may
carry both registered 29 C and 30 C stage metrics, but the builder selects only:

- maize: stage mean temperature and stage degree days above 29 C; and
- soybean: stage mean temperature and stage degree days above 30 C.

These crop-specific thresholds are predeclared diagnostic controls, not
estimated biological optima or causal thresholds. The control table rejects
all precipitation and drought-index columns.

Both thresholds were constructed. Version 1 evaluates the crop-specific
29/30 C primary controls only; the prespecified common-30 C maize sensitivity
remains pending and cannot be described as completed.

Only finite, positive observed yields enter the outcome basis. Consecutive
years are paired within crop, grid cell, and episode, and the outcome is the
first difference in log area-weighted yield. The code never forms a
1989-to-2012 difference. Direct, scPDSI, and common controls are written as
three structurally separate views with identical pair keys and outcomes; a
fourth outcome-blind split view contains no model predictors.

## Outer validation

Every candidate uses exactly the same pair support, common controls, and outer
test rows.

- Spatial validation assigns 5-degree grid blocks to five deterministic folds
  using a hash of crop and block identity. The hash does not use yield.
  Metrics are reported pooled across episodes and separately by episode.
- The retrospective temporal comparison trains the regression on 1982–1989
  first differences and scores 2012–2016 first differences without bridging
  the gap. It is **not** a prospective scPDSI holdout: the acquired CRU file
  records a 1901–2025 self-calibration period, so later and post-test climate
  enter the index transform. This score is retained as a retrospective
  benchmark and cannot establish prospective temporal transfer. See van der
  Schrier et al. (2013), [doi:10.1002/jgrd.50355](https://doi.org/10.1002/jgrd.50355).
- Stress holdouts cover direct dry-spell duration, direct wet Rx5day, scPDSI at
  or below -2, crop-specific heat degree days, and their union. Direct dry,
  wet, and heat cutoffs are crop-specific 95th percentiles calculated from
  early-episode predictors only. The fixed scPDSI cutoff is -2. Yield is
  structurally absent from the cutoff function.

For every component and the union, training removes any pair sharing either
crop-grid-year endpoint with a test pair. The audit reports crop- and
episode-specific component and union prevalence. Because adjacent
first-difference pairs share endpoints and the union combines multiple stress
definitions, the union can cover a substantial fraction of a short panel; it
must not automatically be described as a rare-event tail.

OLS is the only version-1 estimator. Predictors are centered and scaled using
training rows only. Rank deficiency, numerical ill-conditioning, empty
train/test support, nonfinite arithmetic, support disagreement, or endpoint
overlap fails closed. There is no tuning layer.

All reported losses weight crop-grid-year pairs equally. They are not crop-
area-, production-, revenue-, or welfare-weighted global performance. Hashed
5-degree folds keep each block intact but permit adjacent blocks in training
and test; buffered-block and leave-region sensitivities remain required before
strong spatial-transfer claims.

## Validation and suppression gates

The validator rereads the locked config and all immediate sources, revalidates
the four common-support bundles, rebuilds every pair and split, verifies all
file hashes, and refits the complete crop-by-model-by-holdout product. It
checks metric arithmetic and requires identical test-key hashes across models
within a crop and holdout. It rejects coefficient-, prediction-, beta-,
marginal-effect-, response-draw-, damage-, or SCC-like result fields.

The following gates must be exactly false in config, heat inputs, emitted
views, audits, results, and the final validation receipt:

- family stacking;
- coefficient export;
- causal interpretation;
- production model selection and production fitting;
- response draws;
- damage calculation;
- future projection;
- SCC use; and
- selection by SCC magnitude.

Synthetic tests cover candidate/receipt/audit hash tampering, cross-family
panel and weight lineage, threshold drift, heat/direct temperature mismatch,
unequal outcomes,
cross-period pairing, family stacking and feature leakage, common-control
disagreement, endpoint overlap, a missing result, metric tampering,
authorization tampering, and coefficient-field injection. They also require
the stress-cutoff function to reject any outcome column.

## Commands and current run boundary

The tracked config points to ignored project data and output paths. The four
heat-control tables now exist, and the complete real-data version-1 run has
passed exact recomputation validation. Missing inputs still fail explicitly;
no data are synthesized or substituted. Aggregate results and their claim
boundary are recorded in `GLOBAL_DIRECT_SCPDSI_DIAGNOSTIC_RESULTS.md`.

```bash
./.venv/bin/python scripts/build_direct_scpdsi_diagnostic_inputs.py \
  --config config/direct_scpdsi_predictive_diagnostic_v1.toml \
  --output-dir data/interim/direct_scpdsi_predictive_diagnostic_v1 \
  --audit-out outputs/direct_scpdsi_predictive_diagnostic_v1/input_audit.json

./.venv/bin/python scripts/evaluate_direct_scpdsi_predictive_diagnostic.py \
  --config config/direct_scpdsi_predictive_diagnostic_v1.toml \
  --input-audit outputs/direct_scpdsi_predictive_diagnostic_v1/input_audit.json \
  --direct-view data/interim/direct_scpdsi_predictive_diagnostic_v1/direct_view.parquet \
  --scpdsi-view data/interim/direct_scpdsi_predictive_diagnostic_v1/scpdsi_view.parquet \
  --common-view data/interim/direct_scpdsi_predictive_diagnostic_v1/common_view.parquet \
  --split-view data/interim/direct_scpdsi_predictive_diagnostic_v1/split_view.parquet \
  --result-out outputs/direct_scpdsi_predictive_diagnostic_v1/result.json

./.venv/bin/python scripts/validate_direct_scpdsi_predictive_diagnostic.py \
  --config config/direct_scpdsi_predictive_diagnostic_v1.toml \
  --input-audit outputs/direct_scpdsi_predictive_diagnostic_v1/input_audit.json \
  --direct-view data/interim/direct_scpdsi_predictive_diagnostic_v1/direct_view.parquet \
  --scpdsi-view data/interim/direct_scpdsi_predictive_diagnostic_v1/scpdsi_view.parquet \
  --common-view data/interim/direct_scpdsi_predictive_diagnostic_v1/common_view.parquet \
  --split-view data/interim/direct_scpdsi_predictive_diagnostic_v1/split_view.parquet \
  --result outputs/direct_scpdsi_predictive_diagnostic_v1/result.json \
  --out outputs/direct_scpdsi_predictive_diagnostic_v1/validation.json

./.venv/bin/python scripts/test_direct_scpdsi_predictive_diagnostic.py
```

Passing this diagnostic would establish only that the reported held-out
predictive comparison is reproducible under the locked historical design. It
would not establish a precipitation effect, drought damage, future climate
response, or SCC contribution.
