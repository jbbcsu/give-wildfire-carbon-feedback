# Daily-heat rainfall association sensitivity

Exploratory historical associations, specified before this fit. Use original
hash-validated regional direct-practice positive-yield support, 1981–2018,
county and state-year fixed effects, separately for corn/soybeans and reported
irrigated/non-irrigated practice. Retain both quantity and quantity-plus-two-
stage-share specifications. This is not a national causal estimate.

Run three control variants: original stage-mean temperature basis; add stage
daily Tmax exceedance sums and above-threshold day counts at 29 C; or add those
six terms at 30 C. Every heat control has linear and quadratic terms, following
the original fixed-effect estimator's basis. This differs from the preceding
first-difference predictive screen, which added linear daily-heat terms.
Do not include both thresholds in one regression. No specification is promoted.

Report all 24 fits and failures. Retain +100 mm contrasts at within-sample
rainfall quartiles and the partial ten-percentage-point stage3-to-stage2 shift.
All variants retain identical observations. These hypothetical partial
contrasts are not climate scenarios or joint weather perturbations. County-
clustered normal intervals are conditional descriptive uncertainty and do not
resolve wider spatial dependence, adaptation or omitted-driver confounding.

Use a scale-normalized QR estimator and cluster-score triangular solves,
avoiding the original covariance multiplication that generated runtime
warnings. Reproduce original baseline coefficients and standard errors before
using new fits. Retain original files unchanged. Use the validated daily-heat
input and bind its receipt, source hashes, implementation and this protocol.
One monitored existing-data job, no downloads or welfare/SCC conversion.
