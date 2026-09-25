# Timing/distribution does not pass the marginal-SCC promotion gate

## Question

Can the within-season precipitation-distribution increment in the validated
five-ESM Hultgren maize transport be represented as a stable response to global
mean temperature and added to the annual-quantity SCC?

## Result

No. The calculation uses the fixed-practice, MapSPAM-production-weighted
SSP5-8.5 minus SSP1-2.6 response for GFDL-ESM4, IPSL-CM6A-LR,
MPI-ESM1-2-HR, MRI-ESM2-0, and UKESM1-0-LL. Each response is paired with the
same-realization late-century GMST difference. Origin-constrained slopes are:

| Response component | Log-yield response per K | Endpoint sign stability | Whole-ESM holdouts improving on zero change |
|---|---:|---:|---:|
| Net precipitation | -0.005368 | 5/5 negative | 3/5 |
| Quantity reference path | -0.004094 | 5/5 negative | 3/5 |
| Timing/distribution increment | -0.001275 | 4/5 negative | 2/5 |

The pooled timing slope is 31.15% of the absolute quantity slope, so timing is
potentially material. It is not robust: MPI has the opposite endpoint sign,
and a timing slope fitted on the other four ESMs beats a zero-change prediction
for only two held-out models. Net precipitation and quantity are sign-stable,
but their endpoint-per-kelvin fits also fail the stricter five-of-five holdout
rule.

## Decision

The timing/distribution increment is **not promoted** into the marginal damage
path or SCC. The present paired GIVE estimate remains the annual-quantity
benchmark. Timing remains a reported sensitivity and an important omitted
mechanism; the result is not evidence that timing is unimportant.

The next acceptable route is a transient crop-phase precipitation emulator or
published monthly/daily pattern product evaluated across multiple scenarios
and warming levels, followed by the same whole-ESM prediction gate. Scaling the
current single late-century scenario contrast down to a FAIR carbon pulse would
be numerically easy but scientifically underidentified.

## Claim boundary and verification

This screen is production-weighted global maize yield response, not a causal
decomposition, monetary damage estimate, climate probability distribution, or
SCC. The distribution term is the actual phase-specific response minus a
reference path that changes total rainfall while holding phase shares fixed.

- Result: `data/provenance/hultgren_timing_gmst_promotion_gate_20260925.json`
- Independent audit: `data/provenance/hultgren_timing_gmst_promotion_gate_validation_20260925.json`
- Evaluator: `scripts/evaluate_hultgren_timing_gmst_promotion_gate.py`
- Validator: `scripts/validate_hultgren_timing_gmst_promotion_gate.py`
- Unit tests: `scripts/test_evaluate_hultgren_timing_gmst_promotion_gate.py`

The independent implementation reproduces 40 numerical quantities with zero
disagreement. Peak memory is negligible relative to the project's 512 MiB
bounded-job ceiling.
