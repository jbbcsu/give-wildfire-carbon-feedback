# NASS state direct-practice terminal support: infeasible

## Finding

The proposed 2020--2025 state-level validation of reported non-irrigated corn
and soybean yields is not feasible from the exact USDA NASS Quick Stats survey
series. The count-only audit made 56 exact official API queries covering two
crops, two production practices, and 2012--2025. It downloaded no yield values.

| Crop / reported practice | Minimum annual count, 2012--2025 | Minimum terminal count, 2020--2025 | Terminal state-years | Frozen feasibility rule |
|---|---:|---:|---:|---|
| Corn / irrigated | 1 | 1 | 6 | Fail |
| Corn / non-irrigated | 1 | 1 | 6 | Fail |
| Soybean / irrigated | 0 | 0 | 0 | Fail |
| Soybean / non-irrigated | 0 | 0 | 0 | Fail |

Corn has four or five reported state rows annually through 2018, then only one
in every year 2019--2025. Both soybean practice-specific state queries return
zero throughout 2012--2025. This is far below the preregistered requirement of
at least eight rows in every terminal year and at least 60 terminal
state-years. We therefore do not acquire or model these state outcomes.

## Consequence for the U.S. precipitation analysis

This closes one possible path to a newer direct-practice holdout. The existing
post-2019 county test must remain labeled as an **all-practice outcome in
high-rainfed-share counties**, not observed non-irrigated yield. The regional
1981--2019 reported-practice panel remains useful historical evidence but does
not gain an independent 2020--2025 practice-specific state validation from
this source.

The result does not imply that relevant state outcomes do not exist in every
USDA product or could not be constructed from another source. It establishes
only that the exact, predeclared NASS Quick Stats survey series is too sparse.
No thresholds are relaxed and absent/suppressed observations are not recoded.

## Audit and provenance

- Count result SHA-256:
  `cb2a8c82dd04aeec135c0deb6157fc99ca453c7d1dbcfc87197d5614965412c5`.
- Structural validation SHA-256:
  `d336e58560effee4529c99e7b1c9e25f05804789b8f7680b35d120691120b253`.
- The independent structural audit passed 869 query-identity, completeness,
  arithmetic, key-exclusion, and claim-boundary checks.
- The live count audit used 32,440,320 bytes sampled peak process-group RSS;
  the validator used 212,992 bytes. Both stayed below 512 MiB and preserved
  the 130 GiB free-disk floor.
- The API key remained in the ignored secret file and is absent from query
  parameters, results, logs, and Git artifacts.

No yield response, weather relationship, damage, or SCC result follows from
this support audit.
