# Published rice response recovered and source-validated

Date: 2026-09-25

## Finding

The pinned Hultgren et al. (2025) replication repository contains a published
rice estimate in addition to the already-audited maize estimate. The 52,460-byte
Stata file matches repository Git blob
`685a6413df39eefef1de090f9a4897e50fbafe31` and SHA-256
`cd21c4e010a346375928bf98dd367708f4bd0b1d0f50ff5465fe8b6d3c301d0c`.
It remains in ignored raw storage because the reviewed repository has no
located license file.

Stata 18.5 IC exports 46 coefficients and the complete 46-by-46 covariance
matrix. The estimate uses 166,174 observations (166,354 full observations),
656 country-year clusters, 581 first-level administrative clusters, log yield,
and the same spatial-unit, first-level time-trend, and country-year fixed-effect
architecture as the maize model. The validator confirms finite coefficients,
a symmetric covariance matrix with nonnegative diagonal, exact term order,
source hashes, and estimation metadata.

## Response structure

Rice has GDD, KDD, and minimum-temperature terms plus three within-season
precipitation phases. Each phase has linear and quadratic monthly-rainfall
basis terms. Every weather term is moderated by log GDP per capita, irrigated
share, long-run crop temperature, and a weather-specific capped long-run
precipitation measure. The pinned source declares a 14 C GDD base, 30 C KDD
threshold, a maximum 12-month crop season, and precipitation phase lengths
`[2, 3, 7]` before the published response transformation.

This is a major-crop expansion opportunity because it provides a published
response and full coefficient covariance rather than requiring a speculative
cross-crop scaling of maize. It also raises additional implementation duties:
rice calendars include first and second seasons, minimum-temperature exposure,
and up to twelve monthly precipitation inputs, all of which must be constructed
and validated separately for rainfed and irrigated regimes.

## Gates that remain closed

This source recovery is not a projected rice effect, damage estimate, or SCC.
The project has not yet built a five-ESM, matched-scenario rice weather basis
compatible with the exact published transformations; the historical rice
regression dataset is not locally recovered; and crop-specific production
value, market interaction, adaptation, and pulse paths remain to be validated.
The rice response must not be combined with maize until those steps pass and
cross-crop market substitution is handled explicitly.

Configuration: `config/hultgren_rice_response_source_v1.toml`.
Validator: `scripts/validate_hultgren_rice_response_source.py`.
Receipt: `data/provenance/hultgren_rice_response_source_validation_20260925.json`.

