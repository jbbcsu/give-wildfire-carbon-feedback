# U.S. weighted all-classes-wheat PDSI predictive results

**Run:** 2026-09-25 under the frozen
`US_WHEAT_PRACTICE_PDSI_PREDICTIVE_PROTOCOL_20260925.md`.

## Decision

The primary linear-PDSI predictive gate **fails for both practices**. Linear
PDSI improves RMSE in the fixed 2001--2007 terminal block, but does not clear
the prespecified materiality floor in every eligible development state.
Therefore this result supports only a regional historical predictive
diagnostic for PDSI as a separate alternative moisture family. It does not
authorize a causal drought effect, an irrigation-treatment comparison, a
national response, a future or global transfer, a damage function, or an SCC
input.

## Frozen support and splits

- The weighted level panel has 9,513 paired wheat county-years, 631 counties,
  and 14 states over 1981--2007.
- Each separately fitted practice has 8,171 consecutive-year differences,
  573 counties, and 14 states over difference-years 1982--2007.
- All 14 states meet the minimum 50-row development test threshold.
- The terminal block contains 1,602 available differences per practice; 1,585
  are scored after restricting to counties represented in development.
- The terminal fit has 6,569 candidate development rows and 6,347 after
  purging 222 differences that share a level-year endpoint with a test row.
- PDSI is not stacked with rainfall or precipitation-extreme features.

## Primary linear-PDSI result

| Practice | Development states clearing floor | States not clearing floor | Terminal trend RMSE | Terminal linear-PDSI RMSE | Terminal RMSE improvement | Terminal OOS R2, linear PDSI | Gate |
|---|---:|---|---:|---:|---:|---:|---|
| Irrigated | 8/14 | CA, ID, ND, NE, OR, WY | 0.383464 | 0.364107 | 0.019358 (5.05%) | -0.323113 | Fail |
| Non-irrigated | 11/14 | CA, ND, OR | 0.524398 | 0.446511 | 0.077887 (14.85%) | 0.199651 | Fail |

For irrigated wheat, leave-one-state-out RMSE improvements range from
-0.033527 (worse) to 0.014719; 11/14 are positive, but only 8/14 clear the
frozen floor. For non-irrigated wheat, improvements range from -0.052351 to
0.073671; 13/14 are positive, but only 11/14 clear the floor. California is
the largest reversal in both practices. Irrigated ID, NE, and WY and
non-irrigated ND and OR improve weakly but remain below the floor.

The irrigated terminal result improves on the trend-only benchmark but still
has negative out-of-sample R2 relative to the training mean. The
non-irrigated terminal result has positive out-of-sample R2 and a larger RMSE
gain, but its geographic validation gate still fails.

## Prespecified quadratic sensitivity

The quadratic-PDSI model produces terminal RMSE 0.360708 for irrigated wheat
(5.93% below trend-only) and 0.439310 for non-irrigated wheat (16.23% below
trend-only). Its leave-one-state-out performance is also nonuniform: 8/14
irrigated and 10/14 non-irrigated state tests clear the analogous floor. As
prespecified, this sensitivity cannot rescue the failed linear-primary gate.

## Independent validation and resources

An independent implementation reconstructed the first-difference support,
all 30 practice/split combinations and three models (90 result rows), endpoint
purges, training-only scaling, and aggregate metrics. It passed with maximum
absolute metric discrepancy `6.661338147750939e-16`, below the frozen
`1e-10` tolerance.

- Production peak RSS: 402,489,344 bytes.
- Independent-validation peak RSS: 405,143,552 bytes.
- Both commands completed successfully below the 512 MiB cap with one
  numerical thread.

## Artifacts

- Frozen protocol: `US_WHEAT_PRACTICE_PDSI_PREDICTIVE_PROTOCOL_20260925.md`
- Production evaluator:
  `us_county_validation/scripts/evaluate_wheat_practice_pdsi_predictive.py`
- Aggregate result:
  `data/provenance/us_wheat_practice_pdsi_predictive_20260925.json`
- Independent validator:
  `us_county_validation/scripts/validate_wheat_practice_pdsi_predictive.py`
- Validation result:
  `data/provenance/us_wheat_practice_pdsi_predictive_validation_20260925.json`
- Resource receipts:
  `data/interim/us_county/us_wheat_practice_pdsi_predictive_resource_20260925.json`
  and
  `data/interim/us_county/us_wheat_practice_pdsi_predictive_validation_resource_20260925.json`
