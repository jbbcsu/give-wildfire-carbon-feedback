# Paired weather-support diagnostic: prospective protocol

Registered before running this diagnostic. This is a descriptive check, not
a crop-response estimator, causal-overlap certificate, or SCC calculation.
It does not authorize export or use of any earlier diagnostic coefficients.

## Inputs and cohort

Use the validated, hash-bound GSWP3-W5E5 obsclim and ATTRICI counterclim
products built under FACTUAL_COUNTERCLIM_PILOT_PROTOCOL_20260908.md. Verify
their receipts and the successful paired-comparison receipt, including its
retained observed-assembly identities. Do not redo daily construction or the
completed legacy-precision audit. Both new climate products use float64 sums.

For each crop, select exactly the positive, observed-yield keys used by the
retained assembly in 1982–2010 at 39.25/39.75 degrees N. Expected maize:
8,465 rows, 292 cells; soybean: 4,321 rows, 149 cells. This selection defines
weather support, not a new yield regression. The factual reference excludes
years with unavailable yields, even when their climate features exist.

Three feature sets, specified without selecting on the diagnostic results:

1. Quantity: log(1 + seasonal precipitation in mm).
2. Joint quantity/heat: quantity plus the three stage mean temperatures and
   three stage Tmax degree-day integrals above 29 C (maize) or 30 C (soy).
3. Joint quantity/heat/distribution: set 2 plus maximum dry-spell length,
   Rx5day, stage 1 and 2 precipitation shares, and across-stage HHI. Stage 3
   share is omitted because the three shares sum to one. HHI is derived and
   correlated with the shares; this metric does not pretend otherwise.

Set 3 excludes an entire cell if any irrigation regime has a zero-rain season
in either path over the full 1982–2010 interval, matching the paired diagnostic
rule. Report its smaller cohort explicitly; do not attribute cross-cohort
differences exclusively to adding features.

## Calculation

Process one crop and cell at a time. Require exact factual/counterclim keys,
unique records, finite selected features, and at least three factual years.
For each feature, standardize distances by that cell's factual sample standard
deviation (ddof=1). Drop dimensions with standard deviation <= 1e-12 from the
distance calculation; separately flag a counterclim departure from a constant
feature greater than 1e-10 in native units. Do not invert a covariance matrix.

Distance is the root mean square of standardized coordinate differences.
For each factual year, calculate its nearest OTHER factual-year distance.
Use the empirical 95th percentile (NumPy linear interpolation) of these
leave-one-year-out distances as a descriptive cell threshold. For each
counterclim year, calculate its nearest factual-year distance. Flag a distance
greater than the threshold plus 1e-10. If all features are constant, distances
and threshold are zero; constant-feature violations remain separate flags.

Also check whether each counterclim feature is outside its factual cell
minimum/maximum by more than 1e-10 in native units. Report marginal violations,
joint-distance violations, their union with constant-feature violations, and
points inside ALL marginal ranges but beyond the distance threshold. Report
the factual leave-one-out exceedance rate as a descriptive reference, not an
expected false-positive rate. The counterclim nearest neighbor can include
the associated factual year: this tests empirical coverage, not independence.

Report counts, pooled row fractions and equal-cell average fractions for all
flags, feature-level marginal flags, dimensions retained, and cells with zero
thresholds. Do not call pooled cell-years independent observations or attach
binomial confidence intervals. Do not use a support-based exclusion to estimate
effects here. There is no imputation, outcome prediction, fit, download, or
new climate emulator in this step.

## Interpretation and resource limits

Distances in 1, 7, and 12 dimensions are different diagnostics, not comparable
loss functions or model-selection evidence. Sparse 29-year samples, serial
dependence, scaling and correlated coordinates limit interpretation. A flag
does not prove an impossible climate state; no flag does not establish causal
identification, density overlap, or validity under a future emissions pulse.
This pilot is not a representative global agricultural sample.

Run synthetic tests first: diagonal versus off-diagonal joint support,
constant dimensions, nonfinite records, key mismatch/duplicates, exact-match
counterclimate, and changed prior source identities. Then run a single bounded
existing-data job: one numerical thread, sampled 1,024 MiB RAM ceiling,
64 MiB owned new-disk cap, 130 GiB whole-volume free-space floor. Record source,
script and protocol hashes, failures and the resource receipt. Preserve the
original inputs and all preexisting scientific promotion gates.
