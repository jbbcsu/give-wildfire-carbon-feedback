# U.S. corn/soy response-design readiness — September 28, 2026

## Decision

This outcome-blind audit supports freezing two **corn** candidate designs for a
later historical association protocol: direct rainfall quantity and seasonal
PDSI, fitted separately by reported irrigation practice. It does not authorize
either fit. The expanded corn distribution design is not ready because its
maximum residualized-design row leverage is 0.07630, above the frozen 0.05
ceiling; the common influential exposure row is county 48277 (TX), harvest
year 2011. The row remains in the data and no outcome was inspected.

No **soybean** family is ready under the complete frozen gate set. Quantity,
distribution, and PDSI are full-rank and otherwise pass, but each has only 367
terminal-period rows (2012–2018), below the frozen 500-row floor. Soybean also
has exactly five states; Nebraska supplies 46.61% of rows, and the PDSI design's
maximum state leverage share is 48.84%, close to the 50% ceiling.

SPEI remains closed. There is no validated direct-practice county-crop SPEI
panel. The national all-practice SPEI scaffold cannot be substituted: its cell
execution, crop-calendar aggregation, and response-estimation gates are closed.

## Exact support and diagnostics

The hash-bound direct-weather and PDSI sources share all 23,714 practice-level
rows through 2018, or 11,857 exact irrigated/non-irrigated exposure pairs.
No outcome column was read. Because exposures are identical within every
practice pair, the diagnostics below are identical for irrigated and
non-irrigated designs; the table reports the non-irrigated copy.

| Crop | Family | Rows / counties / states | 2012–18 rows | Rank / columns | Condition no. | Max VIF | Max row leverage | Worst leave-state rows / counties / condition | Decision |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Corn | Quantity | 7,013 / 361 / 10 | 640 | 8 / 8 | 17.80 | 52.69 | 0.03937 | 4,005 / 258 / 18.89 | passes |
| Corn | Distribution | 7,013 / 361 / 10 | 640 | 16 / 16 | 21.62 | 71.55 | 0.07630 | 4,005 / 258 / 24.09 | fails row-leverage gate |
| Corn | PDSI | 7,013 / 361 / 10 | 640 | 8 / 8 | 17.42 | 52.38 | 0.03396 | 4,005 / 258 / 18.52 | passes |
| Soybean | Quantity | 4,844 / 255 / 5 | 367 | 8 / 8 | 20.71 | 68.05 | 0.02061 | 2,586 / 152 / 27.65 | fails terminal-support gate |
| Soybean | Distribution | 4,844 / 255 / 5 | 367 | 16 / 16 | 25.72 | 98.58 | 0.03556 | 2,586 / 152 / 33.26 | fails terminal-support gate |
| Soybean | PDSI | 4,844 / 255 / 5 | 367 | 8 / 8 | 20.25 | 67.15 | 0.02284 | 2,586 / 152 / 27.11 | fails terminal-support gate |

Every full and leave-one-state design is full rank. Minimum residual-to-raw
standard-deviation ratios are 0.0674 for corn and 0.1101 for soybean, above the
0.01 floor. Effective county leverage counts range from 153.9 to 221.7, and
all county-leverage, top-1%-leverage, state-concentration, and leave-state
support gates pass apart from the failures stated above.

## Frozen interpretation and remaining blocker

If a later response fit is separately authorized, use county and
state-by-harvest-year fixed effects, county CR1 inference, and separate
irrigated/non-irrigated fits. Quantity, distribution, PDSI, and any future SPEI
specification remain mutually exclusive moisture families. PDSI is an
alternative moisture family, not an addition to raw rainfall. The audit does
not authorize coefficient output, causal or national interpretation, damage
calculation, or SCC use.

The largest manuscript-promotion blocker is spatial inference, not matrix
rank. County clustering is only conditional, while exposure and remaining
errors can be spatially correlated and state support is concentrated. A frozen
geographic-influence check plus an explicitly spatial-dependence covariance or
randomization sensitivity is still required. The corn distribution row must be
handled by a predeclared influence sensitivity without outcome-based deletion;
soybean needs either more independently validated terminal support or an
explicitly historical-only protocol that does not claim temporal stability.

## Reproducibility

- Protocol: `us_county_validation/us_corn_soy_response_design_readiness_v1.toml`
- Primary implementation: `us_county_validation/scripts/audit_us_corn_soy_response_design_readiness.py`
- Machine-readable result: `data/provenance/us_corn_soy_response_design_readiness_20260928.json`
- Independent sparse-dummy validation: `data/provenance/us_corn_soy_response_design_readiness_independent_validation_20260928.json`

The independent implementation reproduced 30 rank, variation, condition, VIF,
and leverage quantities with maximum absolute disagreement 1.12e-12. The
primary audit used 355,631,104 bytes peak RSS in 5.12 seconds; validation used
310,689,792 bytes in 1.14 seconds. Both remained below 512 MiB.
