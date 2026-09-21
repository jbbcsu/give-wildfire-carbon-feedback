# U.S. county PDSI versus rain features: post-result predictive comparison

This comparison was specified **after** the nationwide rain-model terminal
scores were inspected. It is an exploratory robustness check on the *same*
all-practice NASS county-years, not a fresh independent holdout, an observed
non-irrigated-yield effect, or a climate/SCC estimate. The protocol is
`US_COUNTY_AVERAGE_PDSI_COMPETING_SENSITIVITY_20260916.md`.

The existing 40,602,276-byte [NOAA nClimDiv county PDSI](https://www.ncei.noaa.gov/pub/data/cirs/climdiv/)
snapshot (`climdiv-pdsicy-v1.0.0-20260806`) was validated against its pinned
local manifest; **no new data were downloaded**. NOAA's documented
1931–1990 drought calibration is fixed independently of the terminal yields.
The previously generated 1981–2019 crop-season PDSI table matches all
30,213 historical rows in the new panel. A fresh 2019–2025 extract has
45,612 monthly values for 543 relevant counties; 574 independently
recomputed 2019 crop seasons exactly match the old day-weighted seasonal
features (maximum absolute discrepancy 0). The recent PDSI join retains all
4,075 terminal rows; there is **no support change** relative to the rain
models. The raw/source panel assembly peaked at 463.9 MiB sampled RSS—below
the 512 MiB guard, but close enough that larger simultaneous work is
unwarranted. Raw files and fitted panels remain Git-ignored.

Each model includes historical county fixed effects, a time trend, and the
same TAVG/29°C-heat controls. The PDSI competitor uses the season's
day-weighted mean and its square *instead of* direct rainfall terms; it does
not add PDSI to rain. The monthly-minimum PDSI extension is exploratory.
The second trend variant replaces one common trend with state-specific
slopes. All models fit 1981–2019 and score identical 2020–2025 observations.
Values below are log-yield RMSE, so lower is better.

| Trend | Crop | Rain total | Rain total + timing/extremes | PDSI season mean | PDSI mean + monthly minimum |
|---|---|---:|---:|---:|---:|
| Common | Corn | 0.18291 | 0.18224 | 0.18469 | 0.18298 |
| Common | Soybeans | 0.15546 | 0.14781 | 0.15307 | 0.15173 |
| State-specific | Corn | 0.17633 | 0.17525 | 0.18282 | 0.18007 |
| State-specific | Soybeans | 0.15742 | 0.14769 | 0.15679 | 0.15573 |

PDSI mean is competitive with the simpler rain-total model for soybeans,
but the expanded direct rain-pattern group has lower error under both trend
choices. For corn, the ranking of PDSI mean against rain total changes
between historical blocked and 2020–2025 terminal tests, and PDSI is worse
in the recent block. The seasonal-minimum extension modestly helps some
recent PDSI scores, but does not overturn the soybean rain-pattern ranking;
it was not a preregistered primary model. Conditional paired state-bootstrap
intervals for PDSI mean's improvement over rain total include zero for
both crops under the common-trend specification. They also omit model-family
selection, only-six-year time uncertainty, and parameter uncertainty.
The exact rain-model scores were mechanically reconciled to the earlier
validated benchmark before comparison; a separate pandas reconstruction
passed **96** terminal/historical-blocked PDSI/rain score checks.

PDSI is a moisture supply–demand index that incorporates temperature, so
holding common temperature/heat controls is a *predictive comparison*, not
an attribution of the index coefficient to rainfall alone. The published
county monthly index is spatially and temporally coarser than the NOAA daily
rainfall basis, and its source revision differs from the daily weather files.
Neither PDSI nor rain-model forecast rankings establish anthropogenic
precipitation change, adaptation, global crop welfare, GIVE replacement
damages, or SCC. scPDSI and SPEI remain separate candidates, not implicitly
substituted for this PDSI result.

Reproducibility receipts (SHA-256) in ignored `data/interim/`:

- Exact-support PDSI panel: `26ecda06b23e54338380dbd34cd72bce547d857acd9c03134d2c30515c359621`.
- Predictive comparison: `f7b03570a54992004ec440552a5bedcd5444a258ed1c4cb9fd64bd51fbaefbf5`.
- Independent 96-check reconstruction: `27f9086cfdb6b0b1a604476e68950863fa54c12d48519e96190b127f601c6f81`.

The executable stages are `scripts/assemble_us_county_average_pdsi_competitor.py`,
`scripts/evaluate_us_county_average_pdsi_competitor.py` and
`scripts/validate_us_county_average_pdsi_competitor.py`, all called in order
by `scripts/continue_us_county_average_analysis.py` under the local
memory/output/disk guard.
