# National U.S. corn/PDSI spatial-robustness results

## Purpose and design

This analysis strengthens the U.S. drought-yield evidence using the national
1981--2019 NASS county panel rather than the selected ten-state
reported-practice panel. The primary sample contains all-practice corn yield
in counties whose fixed 2017 irrigated harvested-area share is at most 10%.
It includes 15,660 county-years, 424 counties, and 28 states. This is a
high-rainfed-county proxy, not directly reported non-irrigated yield.

The model relates log yield to growing-season PDSI and PDSI squared, with
county and state-by-year fixed effects. PDSI is a competing moisture-balance
representation and is not stacked with precipitation. Inference uses county
CR1 plus same-year cross-county Bartlett spatial covariance at 250 and 500 km.

## Results

Relative to PDSI zero, fitted historical yield differences are:

| Drought contrast | Yield difference | 500 km spatial interval |
|---|---:|---:|
| PDSI -1 vs 0 | -3.70% | -4.31% to -3.09% |
| PDSI -2 vs 0 | -8.32% | -9.63% to -6.98% |
| PDSI -4 vs 0 | -19.67% | -22.59% to -16.64% |

All three contrasts exclude zero under county-clustered, 250 km, and 500 km
covariance. The central -2 contrast is similar across time: -8.60% in
1981--2011 and -7.08% in 2012--2019; the preregistered standardized temporal
difference is 1.19 and passes the 1.96 gate.

All 28 leave-state-out estimates retain the negative sign. The strict
influence gate nevertheless fails because omitting Kansas changes the -2
contrast from -8.32% to -7.71%, or 1.40 full-sample county-CR1 standard
errors, above the preregistered threshold of one. Omitting Minnesota or Iowa
produces -8.73% and -8.71%, respectively. This is materially more stable than
the direct-rainfall response in sign, but it is not invariant to geography.

## Interpretation and claim boundary

The result shows a large, spatially robust historical association between
drought balance and corn yields on broader U.S. support. It helps explain why
a small global precipitation SCC cannot be interpreted as evidence that U.S.
agricultural moisture damages are negligible.

It is not yet a climate-change damage estimate. PDSI combines precipitation
supply with temperature-driven atmospheric demand, the outcome mixes
irrigated and non-irrigated production within low-irrigation counties, and the
2017 irrigation selector is applied retrospectively. Most importantly, this
analysis does not supply the change in PDSI caused by marginal warming. A
bias-adjusted multi-model climate-to-PDSI bridge is required before monetary
damage or SCC calculation.

## Reproduction

- `us_county_validation/scripts/estimate_us_national_corn_pdsi_spatial.py`
- `us_county_validation/scripts/validate_us_national_corn_pdsi_spatial.py`
- `data/provenance/us_national_corn_pdsi_spatial_20261012.json`
- `data/provenance/us_national_corn_pdsi_spatial_validation_20261012.json`
- bounded peak memory: 390.1 MiB
