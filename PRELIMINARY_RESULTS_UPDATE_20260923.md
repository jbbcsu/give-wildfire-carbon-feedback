# Preliminary precipitation--agriculture results update

## Bottom line

Two major validation gates closed on 23 September 2026. First, the final 990 m
U.S. agricultural-area drought reconstruction is complete and confirms that the
earlier coarse spatial approximation was not driving the historical
drought--yield associations. Second, the published Hultgren et al. global maize
response can now be reproduced from a hash-locked dataset recovered from the
authors' public repository history. Neither result is yet a global damage or SCC
estimate.

## U.S. drought benchmark

The memory-bounded national build covers 48 states, 2,909 counties, 10,990,922
sparse grid rows, and 75,634 county-mask-year records. Maximum exposure-process
memory was 638.7 MiB, below the frozen 640 MiB ceiling. Six model validators,
six resource receipts, and an independent summary implementation pass.

All 20 drought-only coefficients are negative under both cultivated-cropland
and broad-agriculture masks. After adding April--September rainfall, rainfall
squared, mean temperature, and crop-threshold heat exposure, the cultivated
mask gives the following dryland estimates for one additional area-equivalent
week:

| Crop | USDM category | Yield change | State-cluster p-value |
|---|---:|---:|---:|
| Corn | D2 | -0.2550% | .0131 |
| Corn | D3 | -0.4188% | .0082 |
| Soybean | D1 | -0.2281% | .0046 |
| Soybean | D2 | -0.1622% | .0371 |

All four signs survive deletion of every represented state, and the broad mask
gives the same qualitative result. Other category/crop/irrigation coefficients
are mixed or imprecise and should not be summarized as uniformly harmful.
Relative to the rejected 3.96 km diagnostic, the maximum final-resolution
coefficient movement is only 0.00230 percentage point per week in drought-only
models and 0.00130 in weather-controlled models.

Interpretation is deliberately narrow: this establishes a robust historical
U.S. association and spatial-fidelity result. USDM is a composite drought
measure, and the regression does not identify a causal response, project future
drought, establish global transferability, monetize damages, or support SCC
integration. Full results are in
[`US_USDM_AGRICULTURAL_AREA_990M_RESULTS_20260923.md`](US_USDM_AGRICULTURAL_AREA_990M_RESULTS_20260923.md).

## Published global maize response benchmark

The current public Hultgren replication tree omits its final regression dataset
at the documented path, but the 345,639,713-byte Stata file is present in the
repository's public Git history. The local ignored copy is bound to commit
`dae5fe8d0d4a260328e4baa45b547368bd6790b3`, Git blob
`da2ac691b32db1b98dea95b8f0ff4256659c8a96`, and SHA-256
`06c2f0102580518a3eea88a6cd677af4636d40882452aa15b65ac7178cf9267a`.
It is not redistributed because no repository license was located.

The exact published 49-term regression has now been rerun. The estimation
sample (377,824), full sample (377,973), cluster counts, fixed effects, regressor
order, and dependent variable all match. The coefficient vector differs from
the published estimate by relative L2 error `2.42e-14`; covariance relative L2
error is `2.65e-6`, consistent with small numerical or installed-package
differences.

The source data also correct an important calendar interpretation. Maize growing
seasons are local four- to ten-month crop-calendar windows; ten months is the
maximum, not a fixed season. Precipitation phases are month 1, months 2--4, and
month 5 through local harvest. Across all 412,282 rows, the three phase-specific
linear and quadratic rainfall terms sum to their respective full-season terms
within single-precision tolerance. The quadratic term is the sum of squared
monthly rainfall totals, not the square of phase-total rainfall.
The same full-source audit confirms that KDD is the cumulative degree-day
measure above 31 C and GDD is cumulative degree days between 8 C and 31 C,
within single-precision storage tolerance. The Supplementary Information shows
that these exposures use Snyder sinusoidal interpolation between daily Tmin and
Tmax; a direct daily-Tmax threshold construction is not compatible.

This closes historical response and basis-arithmetic gates. It does not close
future climate transformation, moderator trajectories, agricultural valuation,
or SCC gates. The next defensible global step is to reproduce these exact local
calendar, monthly-rainfall, GDD, and KDD features from the project's historical
climate pipeline before applying the same transformation to future ESM runs.
Income, irrigation, long-run temperature, and long-run rainfall paths must then
be explicit under the approved fixed, trend, and upper-adaptation scenarios.
Full evidence and limitations are in
[`HULTGREN_MAIZE_RESPONSE_SOURCE_RESULTS_20260923.md`](HULTGREN_MAIZE_RESPONSE_SOURCE_RESULTS_20260923.md).
