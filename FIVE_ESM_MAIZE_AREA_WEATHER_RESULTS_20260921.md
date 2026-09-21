# Five-ESM crop-area-weighted rainfed-maize weather contrasts

This is a **direct daily [ISIMIP3b climate-input](https://doi.org/10.48364/ISIMIP.842396.1)
diagnostic**, not an
anthropogenic or per-kelvin precipitation response, agricultural yield
effect, damage estimate, or SCC result. Fixed [MIRCA-OS v2](https://www.hydroshare.org/resource/e4582ca0042148338bb5e0148b749ed6/)
year-2000
rainfed-maize weights retain 30,654 cells
and 99.9559% of mapped positive crop area
identically across all 120 ESM-by-scenario-by-year panels. Unsupported
cells are not imputed.

## SSP3-7.0 minus SSP1-2.6, 2092--2099 mean

| Daily-derived crop-season feature | GFDL | IPSL | MPI | MRI | UKESM | Signs |
|---|---:|---:|---:|---:|---:|---:|
| Season rainfall (mm) | -53.430 | +10.974 | -19.135 | -18.778 | +6.411 | 2 positive / 3 negative / 0 zero |
| Early-stage rainfall (mm) | -17.849 | +2.187 | -8.812 | -2.749 | -4.227 | 1 positive / 4 negative / 0 zero |
| Middle-stage rainfall (mm) | -22.786 | +2.227 | -6.046 | -15.421 | +13.342 | 2 positive / 3 negative / 0 zero |
| Late-stage rainfall (mm) | -12.795 | +6.560 | -4.277 | -0.608 | -2.705 | 1 positive / 4 negative / 0 zero |
| Wet days (days) | -3.941 | -0.203 | -2.308 | -1.638 | -0.448 | 0 positive / 5 negative / 0 zero |
| Longest dry spell (days) | +1.540 | +0.325 | +1.302 | +0.843 | +0.816 | 5 positive / 0 negative / 0 zero |
| Rx1day (mm) | +1.999 | +5.563 | +0.263 | -0.292 | +4.582 | 4 positive / 1 negative / 0 zero |
| Rx5day (mm) | -2.197 | +9.175 | +0.971 | -0.942 | +9.699 | 3 positive / 2 negative / 0 zero |
| Season mean temperature (C) | +2.616 | +3.846 | +2.754 | +2.175 | +3.985 | 5 positive / 0 negative / 0 zero |

## SSP5-8.5 minus SSP1-2.6, 2092--2099 mean

| Daily-derived crop-season feature | GFDL | IPSL | MPI | MRI | UKESM | Signs |
|---|---:|---:|---:|---:|---:|---:|
| Season rainfall (mm) | -67.679 | +5.737 | -6.940 | +10.168 | +20.124 | 3 positive / 2 negative / 0 zero |
| Early-stage rainfall (mm) | -18.884 | -5.718 | -11.289 | +8.228 | +8.192 | 2 positive / 3 negative / 0 zero |
| Middle-stage rainfall (mm) | -32.335 | -0.703 | +0.306 | -3.627 | +11.941 | 2 positive / 3 negative / 0 zero |
| Late-stage rainfall (mm) | -16.461 | +12.158 | +4.043 | +5.568 | -0.009 | 3 positive / 2 negative / 0 zero |
| Wet days (days) | -5.700 | -2.206 | -2.659 | -1.363 | -0.404 | 0 positive / 5 negative / 0 zero |
| Longest dry spell (days) | +2.133 | +1.093 | +1.653 | +0.582 | +0.739 | 5 positive / 0 negative / 0 zero |
| Rx1day (mm) | +2.482 | +7.440 | +1.754 | +3.563 | +4.950 | 5 positive / 0 negative / 0 zero |
| Rx5day (mm) | -1.210 | +10.283 | +4.211 | +7.019 | +10.359 | 4 positive / 1 negative / 0 zero |
| Season mean temperature (C) | +3.336 | +5.615 | +3.712 | +3.334 | +5.492 | 5 positive / 0 negative / 0 zero |

The sign column is a count across five named models, **not** a probability,
confidence interval, or model-weighted estimate. Scenario contrasts combine
forcing differences, non-CO2 influences, bias-adjustment behavior, and one
realization's internal variability. The eight terminal years do not define a
sampling distribution.

The independent checker rebound all 120 annual source manifests, recomputed
2,160 annual ledger values and
180 scenario contrasts, and performed
210 fixed source-tile checks. The primary
result SHA-256 is `9298eae4ad3f142cf71a9dec9e399e5d81c248af421c6bf5d98aef30ef1764ae` and the audit SHA-256 is `2c0d028cd3113313de2c10ebed88991332c16396c191461865e8f27679f55c96`.
No yield, crop price, irrigation adaptation, agricultural welfare, or GIVE
SCC pathway was evaluated by this weather-only comparison.
