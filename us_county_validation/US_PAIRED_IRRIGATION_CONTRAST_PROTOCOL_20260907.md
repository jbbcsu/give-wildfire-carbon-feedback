# Paired irrigation-practice rainfall-association differences

Exploratory extension registered before estimating its uncertainty, after
seeing the separate-practice curves. Do not call this a preregistered test of
an unknown direction. The separate fits suggest different rainfall sensitivity;
this calculation asks whether that contrast persists when its uncertainty
accounts for paired county/year observations.

Use exactly the same positive-yield, direct-practice panel and baseline/29°C/
30°C controls, both crop types and both rainfall forms. Require an exact
irrigated/non-irrigated outcome pair at every original crop/county/year and
identical weather/design rows, not a new common subset selected after fitting.
If pairs or design identity fail, stop; do not fill or infer a counterpart.

For each crop and specification, regress log(Y_irrigated)-log(Y_non_irrigated)
on the unchanged county and state-year fixed effects and weather design.
Identical-design linearity implies beta_difference=beta_irrigated-beta_non_irrigated;
require agreement with the saved fits. Estimate covariance from paired outcome
differences clustered by county. Do not add independent-model variances:
the two outcomes share county/year conditions and errors can be correlated.

Report all12 fits. Express rainfall contrasts against median rainfall at the
same5/10/25/50/75/90/95 percentiles as the curve analysis. Also retain +100mm
contrasts at the original quartiles, labeled outside the central5–95% range
when applicable. For log contrast d,100*expm1(d) is the percent change in the
irrigated/non-irrigated fitted yield ratio, **not a percentage-point difference
between yield changes**, irrigation's causal effect, or irrigation's benefit.
Include log-scale estimates and county-clustered pointwise normal intervals.

Both outcomes are observed aggregates from different farms/fields. Soil,
management, crop selection and other practice differences can remain; shared
county weather is not field-level exposure. Pairing does not identify adoption,
water availability, irrigation cost, future adaptation or welfare. Keep all
causal, predictive-promotion, adaptation-value and SCC gates closed. Preserve
the inherited covariance convention and disclose that it is conditional; this
is not a correction for every spatial dependency or absorbed-FE degree of freedom.

Synthetic tests verify paired-slope linearity and direct clustered covariance,
including rejection of unmatched pairs and changed regressors. One small
monitored job, no downloads, no raw-data access and no changed original files.
