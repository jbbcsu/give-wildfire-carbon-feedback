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
before polynomial transformation; maize uses local crop-calendar seasons of
four to ten months and groups them into phase 1 (month 1), phase 2 (months
2--4), and phase 3 (month 5 through local harvest). The code's ten-month value
is the maximum represented season, not a fixed duration. The paper selected
phase boundaries through sequential nested
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
algebra without pretending to reconstruct primitive future inputs. It accepts
the eight
already-constructed weather basis values (GDD, KDD, and linear/quadratic terms
for three rainfall phases), the four moderators, and the published long-run
precipitation caps. A source-bound synthetic test verifies an exact zero
contrast, finite coefficient-only uncertainty, and linear-predictor contrast
parity within `7.29e-16`. The evaluator does not itself construct phase
polynomials from daily rain. Its receipt is
`data/provenance/hultgren_maize_response_evaluator_validation_20260923.json`.

## Historical response reproduction now established

The current public replication code expects
`impact_data/for_regressions/corn_gmfd_v1_ready.dta`. That impact dataset is not
present at that path in the pinned current tree. The
pinned and current READMEs direct users to a separate Box archive, but that URL
returned HTTP 404 when checked on 23 September 2026.

The dataset is recoverable from the repository's public Git history. Commit
`dae5fe8d0d4a260328e4baa45b547368bd6790b3` contains the 345,639,713-byte Stata
file as blob `da2ac691b32db1b98dea95b8f0ff4256659c8a96` (SHA-256
`06c2f0102580518a3eea88a6cd677af4636d40882452aa15b65ac7178cf9267a`).
It remains in ignored raw storage and is not redistributed because no repository
license was located.

Running the published 49-term `reghdfe` specification against this historical
blob reproduces the published sample exactly: 377,824 estimation observations,
377,973 full observations, 807 country-year clusters, 541 first-level
administrative clusters, and the same regressors, fixed effects, clustering,
and dependent variable. The coefficient vector matches to maximum absolute
error `1.76e-13` and relative L2 error `2.42e-14`. The covariance matrix matches
to relative L2 error `2.65e-6` (maximum absolute error `2.55e-7`), consistent
with minor numerical or installed-package-version differences. R-squared
statistics match within `5.49e-14`.

A bounded audit reads only fifteen columns in 50,000-row chunks across all 412,282
source observations. In each row, the three phase-specific linear precipitation
terms sum to the full-season linear term, and the three phase-specific quadratic
terms sum to the full-season quadratic term, within single-precision storage
tolerance (maximum scaled errors `1.38e-7` and `1.53e-7`). Thus the fitted
quadratic basis is a sum of monthly squared-rainfall terms within each phase,
not the square of phase-total rainfall. The strict receipt is
`data/provenance/hultgren_maize_historical_replication_validation_20260923.json`.
The same audit establishes 377,973 rows with valid local crop calendars: 62,662
four-month, 51,309 five-month, 211,696 six-month, 51,165 seven-month, 588
eight-month, and 553 ten-month seasons.
The same full-source audit confirms `KDD = CDD31` exactly and
`GDD = CDD8 - CDD31` within single-precision tolerance (maximum scaled error
`5.96e-8`). This binds the fitted temperature terms to the 8 C and 31 C daily
maximum-temperature thresholds used by the new primitive-basis adapter.

An older official GitLab commit still contains a 1.076 GB `impact_data.zip`.
The archive has now been downloaded, Git-blob- and SHA-256-validated, and read
without full extraction. It contains 114 members from January 2023, including
historical projection outputs, but **not** the required regression dataset.
It also predates the final 2025 estimate, so its projection outputs cannot be
treated as version-matched substitutes. The archive audit is recorded in
`data/provenance/hultgren_historical_impact_archive_20260923.json`.

## Published local-response checkpoint now established

The paper's Iroquois County, USA temperature-response example is now reproduced
through two software paths. A Stata calculation using the pinned `.ster`
estimate and the source code's 59-observation local moderator means agrees with
the isolated Python evaluator at all integer temperatures from 1 through 40 C.
Maximum absolute response and coefficient-only-standard-error discrepancies are
`1.32e-9` and `1.84e-10`, respectively. This validates local-response transport
algebra at an author-selected location; it is not a future, precipitation,
damage, or SCC result. Full values and limits are in
`HULTGREN_IROQUOIS_CURVE_RESULTS_20260923.md`.

The separate full-source calendar audit also reproduces planting/harvest
day-to-month conversion, inclusive same- and cross-year seasons,
month-of-season ordering, and the three maize precipitation phases for all
377,973 complete calendar rows, with zero mismatches. This closes calendar
bookkeeping but not primitive GMFD weather or spatial aggregation. See
`HULTGREN_MAIZE_CALENDAR_RESULTS_20260923.md`.

## What is not yet established

The recovered historical regression dataset resolves historical coefficient
and phase-basis replication. It does not by itself provide version-matched
future weather projections or establish a transport rule for income,
irrigation, and long-run climate moderators. The reviewed plotting code
evaluates one temperature response for a U.S. and Chinese location; it does not
supply a standalone globally representative precipitation response curve.

Consequently, this audit still does **not** establish projected yield impacts,
monetary agricultural damages, or an SCC increment. Applying the coefficient
vector to the project's five-ESM climate features before reproducing the
future weather transformation and declaring required baseline-moderator paths
would be speculative. Those three claim gates remain closed in the
machine-readable validation receipt.

## Defensible next route

1. Implement the documented crop-calendar aggregation and monthly precipitation
   transforms on matched historical weather, then reproduce source features
   before any future projection.
2. Register explicit future paths for income, irrigation, long-run temperature,
   and long-run precipitation rather than silently holding moderators fixed.
3. Treat the published-response projection as a benchmark alongside the
   project's U.S. NASS validation, not as a substitute for validation.

Primary source: [Hultgren et al. (2025)](https://doi.org/10.1038/s41586-025-09085-w)
and the [pinned replication repository](https://gitlab.com/ClimateImpactLab/cil-ag-replication-package/-/tree/3ccdffcd4e4ff6e55566ce76e2aac130ee86349a).
