# Physical-link feature-response candidate

Status: preregistered and evaluated; rejected, not promoted, and not authorized
for crop response, damage, welfare, or SCC use.

This candidate retains the frozen continuous same-realization GMST basis,
partially pooled ESM deviations, nested whole-ESM and whole-scenario holdouts,
and prohibition on scenario categorical predictors from the rejected affine
candidate. It changes only the response scale so predictions respect the
known feature domains.

- Mean temperature uses the identity link.
- Seasonal precipitation, wet-day count, maximum dry-spell duration, Rx1day,
  and Rx5day use a positive log link with a fixed `1e-6` floor.
- Precipitation timing centroid and concentration HHI use a logit link after
  clipping only exact boundary observations to `[1e-6, 1 - 1e-6]`.
- The three stage precipitation shares use one centered-log-ratio composition
  with fixed `1e-6` zero replacement and one shared ridge penalty. A genuinely
  all-zero stage vector, which marks a completely dry crop season, is mapped
  to a uniform three-part composition before zero replacement. This convention
  is explicit because a three-part composition cannot itself encode the
  separate zero-rain state; seasonal precipitation retains that state.

Nested regularization is chosen by back-transforming predictions and scoring
RMSE on the original physical scale. The three composition coordinates share
one selected penalty and are inverted jointly with a softmax, so their
predictions are in `[0, 1]` and sum to one. The cell-feature mean on the
original scale remains the benchmark; link-scale RMSE is not a promotion
criterion.

Promotion remains fail-closed: every feature must beat the benchmark in both
holdout families, the maximum and median RMSE-ratio limits remain 1.0 and
0.995, all physical bounds and stage sums must pass, and the actual FAIR
baseline/pulse route must later pass common-random-number support, zero-pulse,
pre-divergence, direct/centered, and decreasing-pulse convergence gates. The
configuration is
`config/isimip3b_physical_link_feature_response_v1.toml`.

## Locked holdout result

The real nested evaluation contains 88 feature-by-holdout comparisons. The
physical-link candidate beats the original-scale cell-mean benchmark in only
34, with median and maximum RMSE ratios of 1.00775 and 1.13855. Whole-ESM
folds improve in 17/55 and whole-scenario folds in 17/33. Temperature passes
all eight comparisons, but none of the eight comparisons for any stage share
or precipitation concentration HHI improves on the benchmark. The inverse
links produce no negative or above-one values, and the maximum stage-share sum
error is `3.33e-16`, so physical-domain gates pass while all predictive
promotion criteria fail. The actual FAIR pulse path was not evaluated.

An exact-key comparison with the rejected identity-link candidate shows that
the physical links improve only 9/88 matched RMSE ratios, rescue none of the
17 identity-link failures, and turn 37 identity-link successes into failures.
Both candidates beat the cell mean in the same 34 comparisons retained by the
physical-link fit. The domain repair is therefore not a predictive repair and
does not justify another FAIR evaluation or an outcome-adaptive link tweak.
