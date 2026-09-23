# FishMIP historical paths versus global FAO marine tonnage

## Result

The four validated FishMIP historical total-catch-density paths reproduce the
broad 1950--2014 rise in provisional FAO global marine tonnage, but they track
annual changes weakly. This post-existing-evidence diagnostic therefore
supports the models as broad structural scenarios, not as calibrated annual
catch predictors.

All series are divided by their own 2005--2014 mean. The FishMIP calculation
uses the exact 40,398 grid cells jointly finite across both ecosystem models
and climate forcings. The FAO reference mean is 80.694 million reported tonnes
per year.

| Climate forcing / ecosystem model | 1950--2014 level correlation | 1950--2014 first-difference correlation | 1980--2014 level correlation | 1980--2014 first-difference correlation | 1980--2014 level RMSE |
|---|---:|---:|---:|---:|---:|
| GFDL-ESM4 / BOATS | 0.985 | 0.282 | 0.903 | 0.294 | 0.0377 |
| GFDL-ESM4 / EcoOcean | 0.953 | 0.303 | 0.778 | 0.338 | 0.1061 |
| IPSL-CM6A-LR / BOATS | 0.965 | 0.255 | 0.769 | 0.308 | 0.1225 |
| IPSL-CM6A-LR / EcoOcean | 0.958 | 0.251 | 0.726 | 0.217 | 0.0974 |

The full-period normalized linear trend is 0.01339 per year in FAO and
0.01230--0.01744 across the four model paths. Over 1980--2014, the observed
trend slows to 0.00413 per year, while modeled trends range from 0.00306 to
0.01114. First-difference sign agreement is only 59.4--75.0% over the full
period and 50.0--67.6% after 1980. The high level correlations are therefore
dominated by a shared long-run rise and must not be described as close annual
tracking.

GFDL/BOATS has the smallest 1980--2014 level RMSE in this fixed diagnostic,
but no model is selected or assigned extra probability. The outcome was known
after calculation, the FAO and FishMIP series had already been inspected in
other summaries, and annual catch discrepancies combine ecological,
management, fishing-effort, market, reporting, and model differences.

## Source and validation boundaries

The FAO input is the independently reconciled symbol-preserving headless
export, restricted to positive marine tonnes-live-weight records while
retaining missing/suppressed meanings. Its supported GUI-menu export was
subsequently reconciled on 23 September 2026, but that record-integrity result
does not promote the marine filter to a production observed panel. FishMIP
absolute levels are not averaged across
ecosystem models, and only within-path normalized values are compared.

The first xarray pass emitted a known multiple-fill-value decoding warning.
That output and receipt are preserved. The final pass reads raw encoded values,
requires both declared fill values to equal 1e20, masks them explicitly, and
is scientifically identical to the first output after removing the changed
code hash. It completed warning-free.

- Final diagnostic SHA-256:
  `24552000bf4292cc6f8f9d1c85c46cea49a904cf9c47a30b716121389e25e00f`.
- Independent validation SHA-256:
  `66970d21e423660d29c4fcfe6387a29584ff9f677996235217d7e2f349cf4a1d`.
- A separate h5netcdf/csv implementation reconstructed all 65 annual values,
  four model paths, two periods, and every metric, passing 736 checks.
- Final builder and validator sampled peak process-group RSS were 127,451,136
  and 80,560,128 bytes, respectively, below 512 MiB; the 130 GiB disk floor
  remained intact.

This result is not species-, stock-, fleet-, country-, or EEZ-level
validation. It identifies no climate effect, effort response, management
adaptation, welfare, marginal CO2 pulse, damage, or SCC.
