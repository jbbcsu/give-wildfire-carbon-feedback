# Preliminary U.S. drought--yield benchmark (calendar-year sensitivity)

**Correction notice:** A subsequent primary-source audit established that the
published exposure window is October of the preceding year through September
of the harvest year, not January--December. These results remain unchanged for
transparency but are now a timing sensitivity. The corrected primary results
are in `US_USDM_OCTSEP_RESULTS_20260922.md`.

**Status:** independently reproduced historical association; external U.S.
validation only. It is not a causal estimate, global response coefficient,
damage function, future drought projection, or SCC input.

## Goal

Test whether the project's NASS county panel reproduces the published
qualitative pattern in [Kuwayama et al. (2019)](https://doi.org/10.1093/ajae/aay037):
additional weeks of more severe U.S. Drought Monitor (USDM) conditions are
associated with lower corn and soybean yields, with larger losses on dryland
than irrigated county support.

## Frozen implementation

- 2001--2013 positive all-production-practices NASS county yields.
- County and harvest-year fixed effects plus state-specific linear trends.
- Separate corn/soybean and dryland/irrigated fits.
- Published irrigation rule reconstructed from Census all-cropland acreage:
  maximum available irrigated harvested-cropland share across 1997, 2002,
  2007, and 2012; irrigated if the maximum exceeds 15%.
- Calendar-year mutually exclusive D0--D4 area-equivalent weeks; no-drought
  weeks are omitted.
- Provisional county-cluster CR1 uncertainty.

The official four-vintage reconstruction yields 2,913 eligible counties, only
four more than the 2,909 observations summarized in the paper: 883 are
classified irrigated and 2,030 dryland. This close count is a source-validation
check, not proof of identical county membership.

The USDM REST service reports county-area shares. The published paper instead
intersected USDM maps with agricultural land. Therefore this is a transparent
approximation to the published exposure, not an exact replication. The archive
contains 533 source files and 2,055,640 standardized county-weeks. One raw row
(Chippewa County, Michigan, 2010-06-22) sums to 102.55%; it is retained
unchanged in raw storage and is the only pre-registered row proportionally
renormalized during preparation.

## Preliminary estimates

Values are exact fitted percentage changes in yield for one additional
county-area-equivalent week in a USDM category, holding the other categories
and fixed effects/trends constant.

| Crop | Support | Rows / counties | D0 | D1 | D2 | D3 | D4 |
|---|---|---:|---:|---:|---:|---:|---:|
| Corn | Dryland | 17,182 / 1,582 | -0.257% | -0.506% | -0.791% | -0.994% | -2.014% |
| Corn | Irrigated | 5,061 / 528 | -0.149% | -0.147% | -0.157% | -0.214% | -0.777% |
| Soybean | Dryland | 15,366 / 1,416 | -0.262% | -0.691% | -0.866% | -1.056% | -2.202% |
| Soybean | Irrigated | 3,391 / 343 | -0.112% | -0.199% | -0.332% | -0.639% | -0.683% |

All 20 point estimates are negative. In both crops, every dryland coefficient
is more negative than its same-category irrigated coefficient, and the adverse
association generally steepens with drought severity. The five drought terms
are jointly different from zero in all four fits under the provisional county-
cluster covariance.

This reproduces the benchmark's qualitative ordering. It does **not** reproduce
its numerical coefficients: the dryland D4 estimates here are larger than the
paper's national-average reported range. Plausible, non-mutually-exclusive
reasons include county-area rather than agricultural-area USDM weights, current
source revisions/county support, and different provisional inference. The
difference is a validation target, not something to tune away.

## Weather-control hierarchy

A second specification frozen before fitting uses identical outcomes and
support while adding independently built April--September NOAA county-average
weather: linear and quadratic rainfall, mean temperature, and crop-threshold
daily Tmax exceedance. The temperature basis is project-consistent but does not
reproduce the paper's agricultural-area moderate/extreme degree-day controls,
so this remains a structural benchmark rather than an exact table replication.

Rainfall quantity has a concave fitted association in dryland counties. In the
weather-only model, an additional 100 mm at the 25th/50th/75th rainfall
percentiles corresponds to +1.457%/+0.483%/-0.681% for dryland corn and
+4.615%/+2.756%/+0.563% for dryland soybean. Irrigated corn is near zero
(-0.229%/-0.172%/-0.123%); irrigated soybean remains positive
(+2.767%/+1.953%/+0.931%). These are conditional fitted contrasts, not causal
water-productivity estimates.

Adding weather attenuates the drought coefficients sharply:

| Crop | Support | D0 | D1 | D2 | D3 | D4 |
|---|---|---:|---:|---:|---:|---:|
| Corn | Dryland | -0.019% (p=.494) | -0.110% (p=.0018) | -0.341% (p<.001) | -0.202% (p=.012) | -0.469% (p<.001) |
| Corn | Irrigated | -0.006% (p=.865) | -0.015% (p=.655) | +0.022% (p=.562) | -0.019% (p=.696) | -0.237% (p=.005) |
| Soybean | Dryland | +0.052% (p=.050) | -0.227% (p<.001) | -0.331% (p<.001) | -0.157% (p=.020) | -0.668% (p<.001) |
| Soybean | Irrigated | +0.119% (p=.024) | +0.043% (p=.435) | -0.130% (p=.075) | -0.242% (p=.002) | +0.144% (p=.217) |

Thus, the defensible interpretation is not that every USDM category has an
independent yield effect. Most of the drought-only signal overlaps direct rain
and heat, particularly on irrigated support. Residual negative associations are
concentrated in D1--D4 dryland models, corn D4 on irrigated support, and soybean
D3 on irrigated support. This mirrors the published qualitative conclusion
that weather explains most yield variability while some composite-drought
information remains, especially for dryland crops.

## Numerical validation and next gate

An independent joint sparse-design solution (rather than the production
Frisch--Waugh residualization) reproduces all 20 coefficients. The largest
absolute difference is `1.55e-11`; covariance symmetry/positive-semidefiniteness,
reported standard errors, input hashes, row counts, and annual exposure
arithmetic also pass. The three guarded builds peaked at 173, 218, and 362 MiB
RSS; no run approached the 640 MiB cap.

Independent joint sparse-design fits reproduce all eight weather-hierarchy
models, with a maximum absolute coefficient difference of `1.22e-08`. Before
stronger interpretation, the next gates are agricultural-area USDM weighting,
the paper's heat construction, and spatial-correlation-robust uncertainty if
the required historical geometries/mask can be pinned. These historical
coefficients will never be transported directly into the global SCC model.
