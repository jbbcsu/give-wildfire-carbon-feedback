# Corn quantity/PDSI spatial protocol validation — September 28, 2026

The missing spatial-inference and geographic-influence layer is now frozen and
mechanically validated for future corn work. This step used synthetic arrays
only: zero real outcome rows were read and zero real response models were fit.

## Frozen future-fit decision

- Candidate moisture families are total-rainfall quantity and seasonal PDSI.
  They are mutually exclusive and cannot be stacked or selected by in-sample
  response significance.
- Irrigated and non-irrigated outcomes must be fit and reported separately on
  identical exposure support.
- County and state-by-year fixed effects remain unchanged. County CR1 is the
  conditional primary covariance.
- Spatial sensitivities add only cross-county, same-year score covariance with
  a Bartlett distance kernel at fixed 250 km and 500 km cutoffs. County CR1
  already supplies diagonal and within-county serial score pairs, avoiding
  double counting. Census TIGER/Line 2019 internal-point coordinates must be
  hash-bound before any real run.
- Every state must be omitted in turn. The absolute contrast shift may not
  exceed one full-sample CR1 standard error, and material full-sample contrasts
  must preserve sign across every omission.
- Development (1981–2011) and terminal (2012–2018) fits must be separate. The
  split contrast difference cannot exceed 1.96 independent pooled standard
  errors, with sign agreement when either split is at least one standard error
  from zero.
- County 48277, Texas, 2011 remains in every primary quantity and PDSI fit.
  Predeclared leave-row and leave-county checks are sensitivities only. The
  distribution family remains ineligible and cannot reenter through deletion;
  it needs an outcome-blind redesign that passes the 0.05 leverage gate on the
  unchanged full sample.

A contrast can be called spatially robust only if its pointwise normal 95%
interval excludes zero under county CR1 and both spatial cutoffs. This language
still describes a selected-sample historical association, never a national or
causal response, damage function, or SCC input.

## Mechanical evidence

All 10 synthetic tests passed. They cover the canonical contract, rejection of
opened real-fit or family-stacking gates, continued distribution-family
ineligibility, the exact spatial ordered-pair formula, same-county exclusion,
distant-county reduction to county CR1, row-order invariance, state DFBETA/sign
logic, and terminal difference/sign logic.

The test run used 96,698,368 bytes peak RSS (92.2 MiB) in 0.55 seconds. The
protocol validator used 23,003,136 bytes (21.9 MiB) in 0.03 seconds. The
validation receipt binds the protocol, validator, test module, inference
primitives, and successful resource receipt. All real-fit, coefficient,
national, causal, damage, and SCC gates remain closed.

## Files

- `us_county_validation/us_corn_quantity_pdsi_spatial_inference_v1.toml`
- `us_county_validation/US_CORN_QUANTITY_PDSI_SPATIAL_INFERENCE_PROTOCOL_20260928.md`
- `us_county_validation/scripts/us_corn_spatial_inference_primitives.py`
- `us_county_validation/scripts/test_us_corn_quantity_pdsi_spatial_protocol.py`
- `us_county_validation/scripts/validate_us_corn_quantity_pdsi_spatial_protocol.py`
- `data/provenance/us_corn_quantity_pdsi_spatial_synthetic_tests_20260928.json`
- `data/provenance/us_corn_quantity_pdsi_spatial_protocol_validation_20260928.json`
