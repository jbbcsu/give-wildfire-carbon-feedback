# Paired uncertainty for direct precipitation versus historical scPDSI

## Purpose and status

This isolated nonproduction sensitivity asks whether the small differences in
spatial out-of-fold predictive loss in the validated direct-quantity versus
historical-scPDSI diagnostic are stable to resampling geographic groups. It
does not change the original five-fold metrics or choose a production model.

The design below was frozen before calculating the real-data intervals. An
exact base revalidation must pass before the sensitivity can run. Missing,
changed, or internally inconsistent base artifacts fail closed.

## Estimand and registered comparisons

For each crop separately, every crop-grid-year first-difference pair receives
one held-out score from the same five spatial-fold OLS design already used by
the validated diagnostic. The sensitivity compares candidate-minus-reference
differences in pooled out-of-fold RMSE and MAE. Negative differences therefore
favor the candidate on that loss measure.

Seven comparisons are registered without a selection rule:

1. direct seasonal precipitation quantity versus controls only;
2. seasonal-mean scPDSI versus controls only;
3. seasonal-summary scPDSI versus controls only;
4. stage-mean scPDSI versus controls only;
5. seasonal-mean scPDSI versus direct quantity;
6. seasonal-summary scPDSI versus direct quantity; and
7. stage-mean scPDSI versus direct quantity.

Direct precipitation and scPDSI remain mutually exclusive. The sensitivity
does not stack moisture representations and does not add new predictors.

## Paired geographic cluster bootstrap

The primary resampling unit is an occupied crop-specific 10-degree latitude by
10-degree longitude cell. All grid points, years, adjacent first differences,
and both historical episodes in a cell stay together. This choice protects
against treating serially linked first differences or nearby grid cells
inside the cell as independent. It also uses a coarser unit than the five-
degree fold block. Maize has 126 occupied cells and soybean has 56, with
inverse-Herfindahl effective cluster counts of 65.26 and 26.66; the largest
cell contains 2.71% and 6.23% of the respective crop pairs. The run requires
at least 30 occupied cells and rejects a crop if any cell exceeds 10% of its
pairs. The lower effective count for soybean is a material precision
limitation despite its 56 occupied cells.

For each crop, 5,000 deterministic bootstrap replicates sample the occupied
cells with replacement. The same cell multiplicities are used for the
candidate and reference in every comparison, preserving the paired loss
contrast. RMSE and MAE are recomputed from resampled cluster-level squared- and
absolute-error sums and the resampled pair count. The reported interval is the
2.5th to 97.5th percentile of the paired candidate-minus-reference loss
difference. The point value remains the equal-pair-weighted pooled OOF loss
difference on the observed support.

The random seed is 20260826 for maize and 20260827 for soybean. Row scores,
row losses, fitted parameters, and bootstrap draws remain internal and are
never written. Only aggregate point differences, percentile bounds, and
cluster-support diagnostics are emitted.

## What the interval does and does not mean

The interval is a descriptive paired geographic-resampling sensitivity for
held-out loss, conditional on:

- the observed global-gridded maize or soybean support;
- the fixed feature construction and historical climate products;
- the existing outcome-blind fold assignment; and
- the fitted five-fold models.

It does not refit a model inside each bootstrap replicate. It therefore does
not capture training-sample estimation uncertainty, feature or model-choice
uncertainty, crop-calendar or climate-input uncertainty, or uncertainty from
alternative folds. Ten-degree cells are not a random sample from a formally
defined target population, and dependence can remain across cell boundaries
or at distances longer than ten degrees. The percentile bounds must not be
reported as causal-effect confidence intervals or hypothesis-test p-values.

Nothing in this sensitivity identifies precipitation or drought effects. It
does not validate future scPDSI, estimate a structural crop response, produce
response draws, calculate agricultural damages, or calculate an SCC. It also
does not resolve the separate limitation that adjacent five-degree blocks can
cross the original train/test boundary. A buffered or leave-region transfer
design remains a distinct future sensitivity and requires a separately frozen
distance/region convention.

## Validated historical predictive-loss result

The complete run reproduced every one of the 50 underlying crop-model-fold
metrics before calculating any interval. The table reports
candidate-minus-reference loss differences followed by the paired 2.5--97.5%
bootstrap interval. These are conditional predictive-loss sensitivities under
the boundary above, not effect estimates or formal population confidence
intervals.

The point values pool squared or absolute held-out errors over all five folds
before calculating RMSE or MAE. They therefore differ slightly from the
previous table's arithmetic mean of five fold-specific RMSE or MAE values,
because fold sizes differ and RMSE is nonlinear. This sensitivity does not
replace or alter the earlier mean-fold table; the pooled ranking is unchanged.

| Crop | Comparison | RMSE difference [interval] | MAE difference [interval] |
|---|---|---:|---:|
| maize | direct quantity - controls | -0.001784 [-0.002724, -0.000751] | -0.000275 [-0.001174, 0.000717] |
| maize | scPDSI mean - controls | -0.001321 [-0.002199, -0.000415] | 0.000561 [-0.000424, 0.001594] |
| maize | scPDSI seasonal summary - controls | -0.001669 [-0.002682, -0.000655] | 0.000423 [-0.000603, 0.001508] |
| maize | scPDSI stage means - controls | -0.001194 [-0.002091, -0.000281] | 0.000678 [-0.000327, 0.001720] |
| maize | scPDSI mean - direct quantity | 0.000464 [-0.000532, 0.001358] | 0.000836 [-0.000169, 0.001745] |
| maize | scPDSI seasonal summary - direct quantity | 0.000115 [-0.000979, 0.001135] | 0.000698 [-0.000332, 0.001667] |
| maize | scPDSI stage means - direct quantity | 0.000590 [-0.000432, 0.001501] | 0.000953 [-0.000075, 0.001884] |
| soybean | direct quantity - controls | -0.001576 [-0.003137, 0.000001] | -0.000008 [-0.001405, 0.001362] |
| soybean | scPDSI mean - controls | -0.000379 [-0.001175, 0.000379] | 0.000174 [-0.000586, 0.000868] |
| soybean | scPDSI seasonal summary - controls | -0.001113 [-0.002264, 0.000114] | -0.000312 [-0.001370, 0.000871] |
| soybean | scPDSI stage means - controls | -0.000352 [-0.001146, 0.000430] | 0.000192 [-0.000583, 0.000916] |
| soybean | scPDSI mean - direct quantity | 0.001197 [-0.000121, 0.002466] | 0.000182 [-0.001014, 0.001353] |
| soybean | scPDSI seasonal summary - direct quantity | 0.000463 [-0.000718, 0.001745] | -0.000304 [-0.001295, 0.000818] |
| soybean | scPDSI stage means - direct quantity | 0.001224 [-0.000232, 0.002625] | 0.000200 [-0.001148, 0.001559] |

For maize, every registered moisture model's RMSE comparison with controls has
an interval entirely below zero, whereas every MAE interval includes zero. For
soybean, every comparison with controls includes zero on both losses; the
direct-quantity RMSE upper bound is only about `+0.000001` and is therefore
Monte-Carlo-fragile near zero, although a separate 20,000-draw audit produced
no zero-inclusion classification change. Most importantly
for the moisture-family ranking, all twelve scPDSI-versus-direct intervals
(three specifications by two crops by two losses) include zero. The result
therefore does not provide a stable paired-loss basis for preferring a richer
historical scPDSI representation over the parsimonious direct-quantity model.
It performs no production selection.

The validated artifact hashes are:

- config: `f6650c5ff872c68ecc7e0649744b2138f8d8dec164085a1cb2c91d64d749024b`;
- result: `95d59680e7a1fe5f7dce5eddc4e9f01a0d34eb8af38f0c7ed1eb5555a465d65f`; and
- validation receipt: `d00f0caecedd755af3b0d9f2ef6a093f70721e627a8264dee7a65613788a94df`.

## Reproducible commands

```bash
./.venv/bin/python scripts/evaluate_direct_scpdsi_paired_loss_uncertainty.py \
  --config config/direct_scpdsi_paired_loss_uncertainty_v1.toml \
  --result-out outputs/direct_scpdsi_paired_loss_uncertainty_v1/result.json

./.venv/bin/python scripts/validate_direct_scpdsi_paired_loss_uncertainty.py \
  --config config/direct_scpdsi_paired_loss_uncertainty_v1.toml \
  --result outputs/direct_scpdsi_paired_loss_uncertainty_v1/result.json \
  --out outputs/direct_scpdsi_paired_loss_uncertainty_v1/validation.json

./.venv/bin/python scripts/test_direct_scpdsi_paired_loss_uncertainty.py
```
