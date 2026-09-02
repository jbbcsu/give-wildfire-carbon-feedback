# Physical-link feature-response candidate

Status: outcome-blind preregistration; not fitted, promoted, or authorized for
crop response, damage, welfare, or SCC use.

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
