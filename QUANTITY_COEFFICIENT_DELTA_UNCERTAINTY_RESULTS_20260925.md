# Published-coefficient uncertainty for the central quantity channel

## Scope

This checkpoint propagates the published 49-by-49 Hultgren et al. coefficient
covariance matrix through the equal-26-climate-model mean of the central
fixed-adaptation, uncapped, annual-maize rainfall-quantity SCC at GIVE's 2%
Ramsey schedule. It is a first-order delta-method calculation. The same
coefficient draw applies to every climate model, as required for uncertainty
in one shared empirical response rather than 26 independent response fits.

This is **not** uncertainty for a complete precipitation-agriculture SCC. It
does not probabilistically combine climate-model spread, market structure,
adaptation, response tails, climate-to-precipitation uncertainty, valuation,
transport, or omitted timing, extremes, drought, temperature, crops, and
irrigation mechanisms.

## Result

All values are 2020 USD per tCO2.

| Quantity | Value |
|---|---:|
| Central equal-model mean | -0.00610173 |
| Coefficient-only delta-method standard error | 0.00217691 |
| Normal-approximation 95% interval | [-0.01036848, -0.00183498] |

The interval excludes zero conditional on this narrow specification. It must
not be interpreted as a causal-confidence interval for total precipitation
damages or as evidence that omitted agricultural precipitation pathways are
beneficial.

The same calculation across all registered GIVE discount schedules gives:

| Schedule | Mean | Coefficient-only SE | Normal 95% interval |
|---|---:|---:|---:|
| 1.5% | -0.00882969 | 0.00315016 | [-0.01500401, -0.00265537] |
| 2.0% | -0.00610173 | 0.00217691 | [-0.01036848, -0.00183498] |
| 2.5% | -0.00454292 | 0.00162078 | [-0.00771964, -0.00136620] |
| 3.0% | -0.00359037 | 0.00128093 | [-0.00610099, -0.00107974] |

Resolving the delta calculation separately for each of the 26 climate models
gives the same qualitative count at all four schedules: 25 central estimates
are negative; 23 model-specific coefficient-only intervals are wholly
negative, two include zero, and one is wholly positive. At 2%, the descriptive
standard deviation of the 26 central estimates is $0.00285438 per tCO2. This
standard deviation is climate-model spread, not sampling uncertainty and not a
probabilistic climate distribution. The coefficient SE for the equal-model
mean uses one shared coefficient draw and is therefore not obtained by dividing
model-specific uncertainty by the square root of 26.

## Reproducibility and validation

The executable implementation is
`scripts/estimate_quantity_coefficient_delta_uncertainty.py`. It uses 36
precipitation-related terms from the 49 published coefficients and reconstructs
the central SCC mean before differentiation. The maximum reconstruction error
is `9.28e-17` USD per tCO2 and the maximum source-market formula error is
`7.11e-15` source USD. The covariance matrix's minimum numerical eigenvalue is
`-7.52e-21`, consistent with floating-point roundoff.

An independent central finite difference along the covariance matrix's largest
eigen-direction gives `-0.00078884797`, versus the analytic directional
derivative `-0.00078853841`. Their relative discrepancy is `0.00039258`, below
the disclosed `0.0005` tolerance. The successful bounded run peaked at
222,281,728 bytes sampled process-group RSS.

Machine-readable result and resource receipts:

- `data/provenance/quantity_coefficient_delta_uncertainty_20260925.json`
- `data/provenance/quantity_coefficient_delta_job_20260925.json`
- `data/provenance/quantity_coefficient_delta_uncertainty_grid_20260925.json`
- `data/provenance/quantity_coefficient_delta_grid_job_20260925.json`
- `data/provenance/quantity_coefficient_delta_by_model_20260925.json`
- `data/provenance/quantity_coefficient_delta_by_model_job_20260925.json`
