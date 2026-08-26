# Preliminary national NASS/PDSI associations

Status: reproducible historical fixed-effects association; not a causal
precipitation effect, directly observed rainfed-yield effect, damage function,
future projection, or SCC input.

## Design

The primary sample contains positive-yield county observations for which the
fixed 2017 crop-specific irrigated-area share is at most 10%. The outcome is
still NASS **all-practice** yield, so this is a high-rainfed-county proxy and
not a separately reported non-irrigated yield. The locked model regresses log
yield on growing-season PDSI and PDSI squared, with county and state-by-year
fixed effects. Standard errors are clustered by county. The broad USDA crop
window (published planting begin through harvest end) is used for this initial
PDSI sensitivity. The direct daily-weather route will provide the primary
fixed-calendar comparison.

PDSI is a stateful water-balance index driven by precipitation and temperature
demand. This regression therefore measures a historical moisture-balance
association; it does not isolate precipitation from temperature.

## Primary results

| Crop | Rows | Counties | PDSI coefficient (county-clustered SE) | PDSI-squared coefficient (SE) | Within R2 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Corn | 15,660 | 424 | 0.03207 (0.00179) | -0.005671 (0.000377) | 0.0566 |
| Soybeans | 14,553 | 390 | 0.03151 (0.00193) | -0.004807 (0.000345) | 0.0688 |

Both fitted curves are concave over the observed PDSI basis: relative to PDSI
zero, the fitted log-yield difference is increasingly negative under drought
and peaks at a moderately positive PDSI before declining under wetter values.
For scale only, the fitted difference at PDSI -2 versus zero is -8.3% for corn
and -7.9% for soybeans; at PDSI -4 it is -19.7% and -18.4%. These are
within-sample curve contrasts, not counterfactual climate damages.

The 20% and 30% irrigation-share sensitivity samples produce the same signs
and similar magnitudes. The quadratic PDSI coefficients range from 0.0310 to
0.0318 on the linear term and -0.00438 to -0.00534 on the squared term across
those thresholds and crops. The all-eligible sample has smaller magnitudes,
consistent with—but not proving—attenuation where irrigation is more common.

## Remaining gates before interpretation

1. Compare PDSI against seasonal precipitation quantity and the pre-specified
   timing/extreme extension on identical direct-weather support and holdouts.
2. Add the common temperature controls to the direct-weather models; do not
   stack PDSI and direct weather in the primary comparison.
3. Complete blocked temporal/spatial predictive validation and zero-yield,
   calendar, irrigation-threshold, and weather-coverage sensitivities.
4. Estimate a future climate response only from validated, bias-adjusted
   scenario inputs. The historical PDSI association cannot be inserted into
   GIVE or translated into SCC as it stands.

The machine-readable result is
`data/provenance/us_national_all_practice_pdsi_association_20260826.json`; the
contract and executable are
`us_national_all_practice_pdsi_association_v1.toml` and
`scripts/estimate_us_national_all_practice_pdsi_association.py`.
