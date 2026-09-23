# Published global maize response: source and estimate audit

## What is now established

The project has pinned and hash-validated the maize estimate and the directly
relevant Stata source files from the public Hultgren et al. (2025) replication
repository at commit `3ccdffcd4e4ff6e55566ce76e2aac130ee86349a`.
The raw files remain ignored because no repository license file was located in
the reviewed pinned tree. The exact source paths, Git blob identifiers, file
sizes, and SHA-256 digests are recorded in
`config/hultgren_maize_response_source_v1.toml`.

Stata 18.5 IC successfully opened the published maize estimate and exported its
49 coefficients and complete 49-by-49 covariance matrix. Independent validation
checks coefficient identity, term order, finite values, covariance support and
symmetry, nonnegative diagonal entries, source hashes, and the estimation
metadata. The estimate reports 377,824 observations, 807 country-year clusters,
541 first-level administrative clusters, log yield as the dependent variable,
and fixed effects for spatial units, first-level-unit time trends, and
country-year.

The response specification contains growing-degree days and extreme heat plus
three within-season precipitation phases, with both linear and quadratic rainfall
terms. The official Supplementary Information and pinned code now resolve the
maize construction: daily GMFD precipitation is summed to grid-cell months
before polynomial transformation; maize uses a fixed ten-month crop season and
groups those months into phase 1 (month 1), phase 2 (months 2--4), and phase 3
(months 5+). The paper selected phase boundaries through sequential nested
F-tests of monthly marginal precipitation responses at 100, 300, and 500 mm,
then selected phased versus total-season precipitation in its second
cross-validation step. Each weather family is interacted with income, irrigation share,
long-run growing-season maximum temperature, and capped long-run precipitation.
It therefore provides a high-value published benchmark that represents both
temperature and both the quantity and timing/distribution of precipitation
within the crop season; it is not an annual-rainfall-only model. The source-bound
method validation receipt is
`data/provenance/hultgren_maize_weather_method_validation_20260923.json`.
The receipt also records the official Europe PMC retrieval endpoint and the
article's CC BY-NC-ND 4.0 terms. The supplementary archive remains in ignored
raw storage and is not redistributed; the pinned code snapshot remains subject
to the separately recorded absence of a repository license file.

An isolated evaluator now transports the published coefficient and covariance
algebra without pretending to reconstruct missing inputs. It accepts the eight
already-constructed weather basis values (GDD, KDD, and linear/quadratic terms
for three rainfall phases), the four moderators, and the published long-run
precipitation caps. A source-bound synthetic test verifies an exact zero
contrast, finite coefficient-only uncertainty, and linear-predictor contrast
parity within `7.29e-16`. The evaluator does not construct phase polynomials
from daily rain and cannot be used for historical or future impacts until the
missing transform and baseline data are reproduced. Its receipt is
`data/provenance/hultgren_maize_response_evaluator_validation_20260923.json`.

## What is not yet established

The public replication code expects
`impact_data/for_regressions/corn_gmfd_v1_ready.dta`. That impact dataset is not
present in the pinned repository tree or this project's source snapshot. The
pinned and current READMEs direct users to a separate Box archive, but that URL
returned HTTP 404 when checked on 23 September 2026.

An older official GitLab commit still contains a 1.076 GB `impact_data.zip`.
The archive has now been downloaded, Git-blob- and SHA-256-validated, and read
without full extraction. It contains 114 members from January 2023, including
historical projection outputs, but **not** the required regression dataset.
It also predates the final 2025 estimate, so its projection outputs cannot be
treated as version-matched substitutes. The archive audit is recorded in
`data/provenance/hultgren_historical_impact_archive_20260923.json`.

The missing regression dataset is needed to recover the authors' baseline
covariate distributions and reproduce their local response curves exactly. It
is also needed to verify the numerical phase variables delivered to the fitted
model, even though their conceptual construction and phase boundaries are now
documented. The reviewed plotting code evaluates one temperature response for a U.S. and
Chinese location; it does not supply a standalone globally representative
precipitation response curve.

Consequently, this audit does **not** yet establish projected yield impacts,
monetary agricultural damages, or an SCC increment. Applying the coefficient
vector to the project's five-ESM climate features before reproducing the
historical transformation numerics and required baseline covariates would be
speculative. All three claim gates remain closed in the machine-readable
validation receipt.

## Defensible next route

1. Resolve the missing impact-data access route or reconstruct only those
   baseline covariates from explicitly matched, documented sources.
2. Reproduce at least one published response figure or numerical checkpoint.
3. Implement the documented crop-calendar aggregation and monthly precipitation
   transforms, then reproduce a historical checkpoint before any future
   projection; do not infer unreported baseline covariates from the estimate.
4. Treat the published-response projection as a benchmark alongside the
   project's U.S. NASS validation, not as a substitute for validation.

Primary source: [Hultgren et al. (2025)](https://doi.org/10.1038/s41586-025-09085-w)
and the [pinned replication repository](https://gitlab.com/ClimateImpactLab/cil-ag-replication-package/-/tree/3ccdffcd4e4ff6e55566ce76e2aac130ee86349a).
