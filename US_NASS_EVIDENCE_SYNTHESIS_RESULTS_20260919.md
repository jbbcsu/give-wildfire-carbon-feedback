# U.S. NASS precipitation and drought evidence synthesis

## Main finding

The U.S. county evidence supports the user's emphasis on non-irrigated crops,
but it does not yet supply a causal or globally transferable damage function.
Within county-specific rainfall ranges, lower rainfall has a negative fitted
association for non-irrigated corn and soybean under both nClimGrid and GSWP
weather. The corresponding reported-irrigated intervals include zero under
both sources.

| Crop / practice | Mean rainfall reduction | nClimGrid fitted yield response | GSWP fitted yield response |
|---|---:|---:|---:|
| Corn / non-irrigated | 105.31 mm | -4.27% [-5.21, -3.33] | -8.34% [-9.44, -7.25] |
| Corn / irrigated | 105.31 mm | +0.20% [-0.28, +0.68] | -0.27% [-0.80, +0.26] |
| Soy / non-irrigated | 114.44 mm | -4.00% [-5.20, -2.79] | -6.71% [-7.96, -5.46] |
| Soy / irrigated | 114.44 mm | -0.05% [-0.67, +0.57] | -0.20% [-0.88, +0.48] |

These are equal-county partial fitted responses over county-specific changes,
not a uniform shock or irrigation treatment effect. The source spread is
material and must remain part of uncertainty.

## Distribution versus drought prediction

On the pooled non-irrigated development holdout, adding precipitation
distribution lowers RMSE relative to quantity by 0.00633 for corn and 0.01115
for soybean. Seasonal PDSI lowers it by 0.01633 and 0.00610, respectively; all
four conditional county-bootstrap intervals exclude zero. This is predictive,
not causal, evidence.

The geographic and temperature-control checks qualify the pooled result:

- Non-irrigated corn distribution improves four of five baseline eligible
  states but reverses in South Dakota, so it fails the frozen uniform-state
  gate under both baseline and richer stage-Tmax controls.
- Non-irrigated soybean distribution passes the baseline state/materiality
  gate, but fails it after adding richer stage-Tmax controls even though mean,
  terminal, and extreme point improvements remain positive.
- Seasonal PDSI is the strongest non-irrigated-corn validation priority: it
  beats quantity in all five baseline states and in terminal prediction. With
  richer Tmax controls it still wins four of five states and the terminal test,
  but South Dakota reverses.
- For non-irrigated soybean, PDSI wins two of three baseline states and all
  three with richer Tmax controls, plus both terminal comparisons.

Thus distribution and drought contain useful information beyond annual
quantity in the U.S., but neither is stable enough to become the global damage
function. PDSI for non-irrigated corn deserves the next independent validation;
distribution remains a secondary competing specification. The families must
not be stacked without an attribution design that avoids double counting.

A later 2020--2025 terminal comparison provides an important, different
qualification. It uses all-practice NASS outcomes rather than the reported-
practice panel and was specified after rain-model scores were known. Direct
rain-pattern features have the lowest RMSE for both crops under common and
state-specific trends: 0.18224/0.17525 for corn and 0.14781/0.14769 for soy.
Seasonal-mean PDSI scores 0.18469/0.18282 and 0.15307/0.15679. This weakens any
claim that PDSI is generally the best U.S. predictor, while not directly
refuting its stronger non-irrigated-corn result because practice and validation
design differ. It strengthens the case for treating PDSI and direct rain
patterns as competing validation targets.

## Reproduction and limits

The synthesis reads only five already-audited aggregate artifacts. It reads
no county yield rows, coefficients, predictions, or raw weather. An independent
implementation rehashes all sources and repeats 136 aggregate identity,
arithmetic, sign, and boundary checks; all pass. The analysis does not estimate
anthropogenic attribution, future PDSI, adaptation, national production loss,
global transfer, welfare, damages, or SCC.

- Protocol: `US_NASS_EVIDENCE_SYNTHESIS_PROTOCOL_20260919.md`
- Builder: `scripts/build_us_nass_evidence_synthesis.py`
- Independent audit: `scripts/validate_us_nass_evidence_synthesis.py`
- Ignored corrected result: `data/interim/us_nass_evidence_synthesis_v2_20260919.json`
- Corrected result SHA-256: `1d0194b4b440cc66ad51165c4cb2deafe68a740154a7f5b67e993f49f49a3933`
- The corrected builder and audit each used less than 3 MiB sampled RSS.
