# U.S. corn rainfall and drought associations with spatial inference

## Purpose

This is the first authorized real-outcome run of the frozen U.S. corn spatial
protocol. It estimates the historical moisture-to-yield link in the proposed
Qiu-style chain. It does **not** estimate the separate climate-change-to-
moisture link and therefore is not yet a U.S. damage or SCC estimate.

The selected NASS reported-practice panel contains 7,013 exact county-year
exposure pairs, 361 counties, ten states, and harvest years 1981--2018. Each
pair has separate irrigated and non-irrigated reported yields and identical
nClimGrid/PDSI exposures. The states are Colorado, Delaware, Kansas, North
Dakota, Nebraska, New Mexico, Oklahoma, South Dakota, Texas, and Wyoming;
major Corn Belt states without adequate reported-practice support are absent.
The estimates must not be described as nationally representative.

## Frozen design

- Separate irrigated and non-irrigated models.
- County and state-by-harvest-year fixed effects.
- Linear and quadratic crop-stage mean-temperature controls.
- Mutually exclusive seasonal-rainfall-quantity and seasonal-PDSI families.
- County CR1 inference plus same-year cross-county Bartlett spatial
  sensitivities at 250 and 500 km.
- Full leave-one-state influence checks, separate 1981--2011 and 2012--2018
  fits, and predeclared Texas row/county influence checks.
- Raw coefficients and row predictions are not exported. Reported estimates
  are finite target contrasts at frozen full-sample exposure quantiles.

## Central historical associations

The table evaluates each contrast at the median observed moisture value.
Intervals are pointwise normal 95% intervals under the conservative 500 km
spatial covariance. Positive yield values mean higher fitted yield.

| Practice | Moisture contrast | Fitted yield change | 500 km interval | Spatially excludes zero? |
|---|---|---:|---:|---|
| Non-irrigated | +100 mm seasonal rainfall | +7.72% | +5.96% to +9.51% | Yes |
| Non-irrigated | PDSI decrease of 1 | -4.30% | -5.02% to -3.57% | Yes |
| Irrigated | +100 mm seasonal rainfall | -0.41% | -1.01% to +0.19% | No |
| Irrigated | PDSI decrease of 1 | -0.27% | -0.51% to -0.02% | Yes |

The sharp practice difference is consistent with irrigation buffering rainfall
quantity, but is not an irrigation treatment effect because farms, soils,
management, selection, and reporting can differ between practice samples.

## Heterogeneity and stability gates

The full-sample non-irrigated rainfall association is precise but fails the
strict leave-one-state influence gate at all three reference quantiles. At the
median, omitting Kansas lowers the +100 mm estimate to +6.71%, while omitting
Nebraska raises it to +8.21%; the maximum shift is 2.10 full-sample county-CR1
standard errors. Its development-period estimate is +6.93%, versus +13.18%
in 2012--2018, so it also fails the median temporal-stability gate.

The non-irrigated median PDSI contrast passes the leave-state gate: omission
estimates range only from -4.38% to -4.25%. Its development and terminal
estimates are -3.92% and -5.55%; the median temporal gate passes at 1.82 pooled
standard errors, just below the frozen 1.96 ceiling. The low-exposure PDSI
contrast fails temporal stability and the high-exposure contrast fails the
leave-state threshold, so even PDSI is not uniformly stable across the curve.

The preidentified Texas 2011 row and whole-county sensitivities pass every
frozen influence threshold. The real run peaked at 285.5 MB sampled process-
group RSS, below the 512 MiB ceiling.

## Interpretation

These results establish a large, spatially robust historical moisture--yield
association for non-irrigated corn on the selected support, with a much smaller
irrigated response. They also explain why a small one-model global average
cannot be interpreted as evidence that moisture is unimportant. But the
rainfall coefficient's geographic and temporal instability prevents promoting
one number directly into GIVE. The next defensible step is to apply multiple
climate-attributed rainfall/PDSI paths and propagate state/time heterogeneity,
not to multiply the global average by this coefficient.

## Reproducibility and gates

- Frozen real-run contract:
  `us_county_validation/us_corn_quantity_pdsi_spatial_real_v1.toml`
- Authorized implementation:
  `us_county_validation/scripts/estimate_us_corn_quantity_pdsi_spatial_real.py`
- Aggregate receipt:
  `data/provenance/us_corn_quantity_pdsi_spatial_real_v1_20261012.json`
- Full aggregate result (gitignored):
  `data/interim/us_corn_quantity_pdsi_spatial_real_v1_20261012.json`

The output authorizes selected-sample historical associations only. National,
causal, climate-attribution, damage, and SCC gates remain closed.
