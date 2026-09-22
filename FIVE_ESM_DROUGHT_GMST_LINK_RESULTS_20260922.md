# Five-ESM drought--GMST endpoint link

## Main result

The preregistered endpoint diagnostic relates each named ESM's 2092--2099
SSP3-7.0 and SSP5-8.5 crop-calendar SPEI differences from SSP1-2.6 to its
same-realization eight-year mean GMST difference. It uses an
origin-constrained, equal-endpoint-weight slope and prespecified whole-ESM and
whole-scenario holdouts.

For primary rainfed crop-season SPEI-3, the maize slope is -0.1876 SPEI K-1.
Its fitted RMSE is 0.1669 versus 0.5861 for zero change. It improves on zero
change in every whole-ESM holdout and both whole-scenario holdouts, so it
passes the frozen internal predictive rule. The soybean slope is -0.1469
SPEI K-1, with RMSE 0.2305 versus 0.4968 for zero change. It passes both
whole-scenario holdouts but fails the whole-ESM rule because the MRI holdout
worsens RMSE by 0.1855; it is therefore not a stable primary link.

| ESM | Contrast | GMST difference (K) | Maize SPEI-3 difference | Soybean SPEI-3 difference |
|---|---|---:|---:|---:|
| GFDL | SSP3-7.0 minus SSP1-2.6 | 2.081 | -0.617 | -0.536 |
| GFDL | SSP5-8.5 minus SSP1-2.6 | 2.590 | -0.885 | -0.883 |
| IPSL | SSP3-7.0 minus SSP1-2.6 | 2.947 | -0.374 | -0.276 |
| IPSL | SSP5-8.5 minus SSP1-2.6 | 4.116 | -0.828 | -0.786 |
| MPI | SSP3-7.0 minus SSP1-2.6 | 2.033 | -0.380 | -0.306 |
| MPI | SSP5-8.5 minus SSP1-2.6 | 2.644 | -0.458 | -0.442 |
| MRI | SSP3-7.0 minus SSP1-2.6 | 2.080 | -0.321 | -0.138 |
| MRI | SSP5-8.5 minus SSP1-2.6 | 2.923 | -0.438 | -0.098 |
| UKESM | SSP3-7.0 minus SSP1-2.6 | 3.227 | -0.552 | -0.374 |
| UKESM | SSP5-8.5 minus SSP1-2.6 | 4.315 | -0.701 | -0.500 |

Across all prespecified windows, SPEI scales, and fixed area bases, 37/45
maize cells and 13/45 soybean cells pass every whole-ESM and whole-scenario
holdout. All 90 cells pass both whole-scenario holdouts, so the failures arise
from transport across named climate models rather than the SSP3-7.0 versus
SSP5-8.5 split. This is evidence of a more stable endpoint temperature scaling
for maize than soybean, not evidence that either crop response is causal.

## Strict interpretation

The slope is a **multi-forcing endpoint scenario diagnostic**. It is not an
anthropogenic-attribution coefficient, a CO2-only response, a transient
emulator, or a marginal CO2-pulse response. The holdouts reuse the same five
climate models and are not an independent ensemble. Five named models are not
probability draws, so no confidence interval or probability is reported.

The maize result is a practical benchmark for the climate-to-drought link,
but it cannot yet be evaluated on GIVE's marginal FAIR path. It also cannot
be multiplied by a historical yield coefficient: the registered global
drought-response family failed its independent promotion rule, and the future
SPEI values extend beyond parts of historical support. No yield effect,
monetary damage, or SCC is calculated.

## Reproducibility

- Frozen protocol: `FIVE_ESM_DROUGHT_GMST_LINK_PROTOCOL_20260922.md`.
- Aggregate result SHA-256:
  `bc1c9877bd7a07da394365125bc5da4d642ebc891f001035c15ad6e7c87f0d78`.
- Independent validation recomputed 90 feature records and all folds in 6,893
  numeric checks; maximum disagreement was `1.11e-16`.
- Public record:
  `data/provenance/five_esm_drought_gmst_endpoint_public_evidence_20260922.json`.
- Primary implementation: `scripts/evaluate_five_esm_drought_gmst_link.py`.
- Independent implementation:
  `scripts/validate_five_esm_drought_gmst_link.py`.
- The evaluator and validator used 81.1/81.6 MB sampled peak process-group RSS,
  below the 512 MiB limit.
