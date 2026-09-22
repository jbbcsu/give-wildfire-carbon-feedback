# Corrected U.S. October--September drought--yield benchmark

**Status:** completed and independently validated historical association. This
corrects the temporal window used in the initial calendar-year sensitivity. It
is not a causal estimate, global response coefficient, damage function, future
drought projection, or SCC input.

## Correction and data

The primary article defines drought exposure from October of the preceding
year through September of the harvest year. The earlier implementation used
January--December. After discovering that mismatch, the correction was frozen
before acquiring the additional year-2000 inputs or inspecting corrected
estimates. The old result is retained unchanged as a timing sensitivity.

The corrected archive contains 574 official state-year responses for 41 states
over 2000--2013 and 2,209,813 standardized county-weeks. Integrating exact
validity intervals yields 78,598 crop-county-years (39,299 unique county-years,
3,023 counties) for harvest years 2001--2013. The mean county-area-equivalent
weeks are D0 8.603, D1 5.739, D2 3.906, D3 2.287, and D4 0.821. The published
agricultural-area means are 8.47, 5.66, 3.87, 2.26, and 0.80 on 40,040
county-years. The descriptive similarity is a useful source check, not proof
of spatial replication: the official REST series weights whole-county area,
whereas the paper intersects drought maps with agricultural land.

## Drought-only associations

Values below are exact fitted yield percentage changes for one additional
county-area-equivalent week in the indicated mutually exclusive category,
holding the other categories, county and year fixed effects, and state trends
constant.

| Crop | Support | Rows / counties | D0 | D1 | D2 | D3 | D4 |
|---|---|---:|---:|---:|---:|---:|---:|
| Corn | Dryland | 17,182 / 1,582 | -0.136% | -0.309% | -0.614% | -1.072% | -1.141% |
| Corn | Irrigated | 5,061 / 528 | -0.086% | -0.041% | -0.123% | -0.123% | -0.488% |
| Soybean | Dryland | 15,366 / 1,416 | -0.175% | -0.589% | -0.575% | -0.839% | -0.619% |
| Soybean | Irrigated | 3,391 / 343 | -0.002% | -0.211% | -0.290% | -0.399% | -0.070% |

All 20 estimates remain negative, and every same-crop/category dryland estimate
is more negative than its irrigated counterpart. Correcting the time window
generally reduces absolute magnitudes, especially D4: relative to the calendar-
year sensitivity, dryland D4 changes from -2.014% to -1.141% for corn and from
-2.202% to -0.619% for soybean. The dryland/irrigated qualitative ordering is
therefore stable, but numerical severity gradients depend materially on the
window.

## Direct-weather hierarchy

The pre-specified weather-controlled family retains April--September rainfall,
rainfall squared, mean temperature, and crop-threshold Tmax exceedance. It asks
whether USDM contains residual information after direct weather; it is not an
additive drought damage channel.

| Crop | Support | D0 | D1 | D2 | D3 | D4 |
|---|---|---:|---:|---:|---:|---:|
| Corn | Dryland | +0.044% | -0.011% | -0.261% | -0.414% | -0.172% |
| Corn | Irrigated | +0.049% | +0.058% | +0.035% | -0.018% | -0.103% |
| Soybean | Dryland | +0.026% | -0.227% | -0.168% | -0.094% | +0.320% |
| Soybean | Irrigated | +0.175% | -0.039% | -0.126% | -0.184% | +0.372% |

Attenuation is substantial, signs are not monotonic in drought severity, and
some severe-category terms become positive. With state-cluster CR1 inference,
corn-dryland D2/D3 and soybean-dryland D1/D2 are below .05; the other dryland
terms are not. The positive irrigated-soybean D4 coefficient is also precise,
which is a warning against reading individual mutually exclusive category
coefficients as structural marginal damages.

Leave-one-state-out results reinforce that caution. Corn-dryland D2--D4 and
soybean-dryland D1--D3 retain negative signs after every represented-state
deletion. Corn D1 changes sign in 4 of 34 deletions; soybean D4 changes sign in
1 of 31. Thus the corrected result supports a broad drought/yield and irrigation-
heterogeneity validation, but not a stable category-by-category scalar suitable
for global transport.

## Validation and resource bound

Independent joint sparse-design fits reproduce drought-only coefficients within
`1.46e-11` and all eight weather-hierarchy fits within `1.23e-08`. The
state-robustness validator reproduces full coefficients within `1.23e-08`,
covariance entries within `4.69e-10`, and sentinel state deletions within
`1.24e-08`. Every numerical task remained below the 640 MiB ceiling; the
largest peak RSS was 454,574,080 bytes (about 434 MiB).

The next fidelity gate is spatial, not another coefficient fit: reproduce the
paper's agricultural-area weighting with pinned historical USDM geometries and
the 2008 Cropland Data Layer. Until that gate and a defensible future drought
projection pass, no USDM coefficient enters the global agriculture replacement
or the SCC calculation.
