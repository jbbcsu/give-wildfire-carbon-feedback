# Conditional drought signal on the GIVE/FAIR pulse path

## Numerical result

The validated rainfed-maize endpoint slope (-0.187585 SPEI K-1) was applied
linearly to the matched core-GIVE FAIR pulse-minus-baseline temperature path.
For the largest numerical test pulse, 0.0001 GtC in 2020, the conditional
SPEI-3 differences are:

| Year | Temperature difference (K) | Conditional SPEI difference |
|---|---:|---:|
| 2021 | 1.585e-8 | -2.973e-9 |
| 2030 | 1.831e-7 | -3.434e-8 |
| 2050 | 1.632e-7 | -3.062e-8 |
| 2100 | 1.481e-7 | -2.777e-8 |
| 2200 | 1.519e-7 | -2.850e-8 |
| 2300 | 1.570e-7 | -2.944e-8 |

The maximum absolute conditional signal over 1750--2300 is `3.44564e-8`
SPEI for the 0.0001-GtC pulse, `1.72284e-8` for 0.00005 GtC, and
`8.61420e-9` for 0.000025 GtC. The maximum normalized full-slope signal is
`3.44568e-4` SPEI per GtC. Five leave-one-ESM-out maize slopes span
-0.198124 to -0.168442 SPEI K-1; these named sensitivities are not a
confidence interval.

The zero-pulse and every pre-2021 conditional SPEI difference are exactly
zero. The two smallest positive pulses pass normalized convergence. A separate
implementation recomputed all 13,224 row--slope products and summaries in
52,933 numeric checks; maximum disagreement was `8.88e-16`. The first
implementation/audit disagreement is preserved: it used the stored FAIR
temperature-difference column while the independent validator recomputed
pulse minus baseline. The corrected version uses the latter, as preregistered.

## Scientific boundary

This is a **conditional linear sensitivity**, not a validated drought response
to a marginal emission. The source maize slope is fitted from multi-forcing
late-century SSP endpoints, not CO2-only experiments or a transient climate
emulator. Multiplying it by a FAIR temperature perturbation demonstrates the
software and scaling interface but does not solve attribution. The test pulse
is a numerical convergence scale, not a claim that its raw SPEI value is an
SCC.

No crop-yield response is applied. The global empirical drought-yield family
failed its promotion gate, and the endpoint slope does not provide spatial
crop-cell changes needed for welfare accounting. Therefore this calculation
produces no yield loss, monetary damage, adaptation result, or SCC.

## Reproducibility

- Protocol: `FIVE_ESM_DROUGHT_FAIR_SENSITIVITY_PROTOCOL_20260922.md`.
- Corrected result SHA-256:
  `5a0c4ea5b7c41b30550d4b3dff888a43c79d59ad579fb02aeb7ea13aac39e85e`.
- Public evidence:
  `data/provenance/five_esm_drought_fair_conditional_public_evidence_20260922.json`.
- Evaluator: `scripts/evaluate_five_esm_drought_fair_sensitivity.py`.
- Independent validator:
  `scripts/validate_five_esm_drought_fair_sensitivity.py`.
- Sampled evaluator/validator peak process-group RSS was 88.4/89.3 MB, below
  the 512 MiB limit.
