# Supported-range U.S. rainfall association curves

Registered before this calculation. Re-express, do not reselect, all 24
completed direct-practice association fits: two crops, two reported irrigation
practices, quantity/quantity-plus-timing, and baseline/29°C/30°C heat controls.
Preserve each specification, sample, county/state-year fixed effects, and
county-cluster covariance convention. These are regional historical partial
associations, not causal effects, future losses, national estimates or SCC.

The existing receipt saves coefficient estimates, standard errors and selected
contrasts, but not the full covariance. Refit the exact validated panel solely
to recover the rainfall-coefficient covariance. Require agreement with every
saved coefficient and standard error (rtol1e-7, atol1e-10) and identical sample
counts before reporting any curve. Preserve original files and promotion gates.

For each crop/practice use observed rainfall percentiles5,10,25,50,75,90,95
(linear interpolation, unweighted county-year observations). Evaluate 91
equally spaced points from percentile5 to95, plus these percentile anchors.
Reference is the crop/practice median. For scaled rainfall p=P/100 and p0,
the log-yield contrast is beta1*(p-p0)+beta2*(p-p0)*(p+p0). Other regressors,
county and year effects are held fixed. Propagate the complete2×2 rainfall
covariance through this contrast; never infer covariance from marginal SEs.
Report 100*expm1(contrast) and transformed pointwise normal95% intervals.
These are ratios on the fitted log-yield scale, not unconditional expected
yield changes; support percentiles and the model are treated as fixed.

Pooled percentile bounds are only marginal rainfall support. For each point
also report the number/fraction of counties whose observed rainfall min–max
range contains both that rainfall value and the pooled median. This range
diagnostic does not establish joint weather support, dense sampling, or causal
identification. Do not trim/refit based on the diagnostic. Irrigated and
non-irrigated outcomes are not interchangeable or randomly assigned.

Show all forms and heat variants in the aggregate artifact. If visualizing,
use separate baseline/29°C/30°C figures with four crop/practice panels, both
rainfall specifications per panel, zero and median reference lines, and
pointwise bands. Do not identify a new primary model from these curves or
select a favorable threshold. Existing predictive nulls/failures remain.

Synthetic tests cover quadratic contrasts, full covariance propagation,
reference zero, reverse contrasts, invalid inputs, and county-range counts.
One existing-data analysis job at a time, numerical threads one, at most1GiB
sampled process-group memory; small output, no downloads or rehydration.
