# Paired climate-feature driver for marginal CO2 SCC runs

## Decision

The primary implementable route is a **daily-feature response emulator**, not a
new global weather emulator and not a scenario difference treated as a one-tonne
CO2 experiment.  It learns the response of the exact crop-calendar features
used by the agricultural model from archived, bias-adjusted ISIMIP3b CMIP6
daily fields, separately by ESM.  The paired GIVE/FAIR baseline and pulse
temperature paths are then evaluated through the same ESM-specific feature
response curve with common random numbers.

This preserves the quantity and temporal-distribution information in daily
climate data at the stage where it matters (crop features), while avoiding an
unsupported claim that a new daily precipitation simulator is needed for SCC.
It is also computationally appropriate: SCC needs annual expected losses and
their marginal difference, rather than a physically realistic daily map for
every Monte Carlo draw.

The prior MESMER-M-TP + daily weather-generator chain remains a robustness
path, not the primary path.  It becomes necessary only if direct daily-feature
response curves cannot pass the validation gates below.  STITCHES remains a
sequence-preserving external benchmark.  RIG and ACE2-SOM are not primary
drivers because their small-pulse/transient behavior has not been established
for this application.

## Estimand and paired construction

For ESM/member `m`, crop-calendar cell/stage `g`, feature `k`, and model year
`t`, derive the feature directly from each archived daily field:

`X[m,g,k,t] = F_k(daily pr, tas, tasmin, tasmax; calendar[g,t])`.

`F` includes growing-season precipitation total, stage precipitation shares,
wet-day count, longest dry spell, Rx1day, Rx5day, and the jointly defined heat
features.  It therefore represents both precipitation quantity and temporal
distribution without separately claiming their effects are additive.

Fit an ESM-specific conditional response `f[m,g,k](T_global)` to the feature
series computed from historical and future CMIP6/ISIMIP3b simulations.  The
primary specification must be fixed before outcome estimation: a smooth,
low-dimensional response in global-mean temperature with scenario controls
only if held-out-scenario tests show they are necessary.  It must use the same
calendar convention as the historical estimation panel.

For a matched GIVE draw, evaluate the FAIR paths using the *same* ESM/member
and climate-feature draw:

`X_base = f[m,g,k](T_FAIR_base[t]) + e[m,g,k,t]`

`X_pulse = f[m,g,k](T_FAIR_pulse[t]) + e[m,g,k,t]`.

The shared residual is a common random number.  It prevents weather noise from
being mistaken for a one-tonne effect; it cancels in the paired difference.
The marginal feature signal is thus
`f(T_FAIR_pulse) - f(T_FAIR_base)`.  Do not independently sample residuals by
region or feature.  Any residual draw used for levels must be a joint spatial,
cross-feature draw from one ESM/member/year block.

For numerical stability, production code should evaluate both (i) the direct
difference and (ii) a centered finite-difference derivative times
`T_pulse - T_base`.  The two calculations must agree over a declared sequence
of decreasing pulse sizes.  A scenario-to-scenario difference is only training
information; it is not itself an SCC marginal experiment.

## Why this route is defensible

* It uses ISIMIP3b's direct, bias-adjusted daily climate sequences to define
  all dry-spell, wet-day, heavy-rain, and stage-timing features.  No monthly
  disaggregation is needed in the primary analysis.
* It retains ESM-level coherent spatial patterns and joint temperature--rain
  behavior.  ESMs are sampled as whole patterns rather than creating
  independent country responses.
* It targets exactly the feature vector passed to the crop response, which is
  a smaller and more testable emulation task than reproducing complete weather
  fields.
* It makes a small CO2 pulse a smooth interpolation/derivative problem and
  removes internal-weather noise from its expected value using matched draws.

This is a climate-feature emulator assembled from direct CMIP daily output.
It must be described as such, and not as an independent climate model or a
causal estimate of crop damages.

## Required ISIMIP3b acquisition and processing

Use only public, version-pinned datasets described in
`data/provenance/isimip3b_paired_feature_driver.toml`.

The repository API query schema was exercised on 25 August 2026 for the
MRI-ESM2-0 SSP3-7.0 daily precipitation dataset. It returned exactly one
public dataset (version 20210512) with dataset/file identifiers, rights,
file URLs, and SHA-512 metadata. This is a discovery/provenance check only;
no projection file has been acquired and no ensemble member has been selected.

1. Select a predeclared set of ISIMIP3b CMIP6 ESMs with daily `pr`, `tas`,
   `tasmin`, and `tasmax` over historical plus `ssp126`, `ssp370`, and
   `ssp585`.  Keep model/member identity in every file and output row.
2. Download one ESM/scenario/variable block at a time.  Build crop-year/stage
   features by latitude partition, write a compact feature table, verify it,
   and then archive or remove the raw block according to the source terms and
   local storage policy. Chronologically adjacent files are opened as one
   audited daily series: grids and units must match and the boundary must have
   exactly one-day steps without duplicates or gaps. Raw projections are not committed.
3. Join annual GMST from the *same CMIP6 realization* for fitting.  The GMST
   source, baseline period, and anomaly definition must be recorded; do not
   substitute FAIR temperatures during fitting.
4. Fit only after complete historical/future feature coverage and
   calendar-year/cross-year checks.  FAIR is used only at the paired
   evaluation boundary after the climate response is fitted.

## Validation gates

The driver cannot supply a GIVE SCC input unless all apply:

1. **Held-out climate tests:** leave out whole ESMs and whole scenarios; random
   years alone are insufficient.  Evaluate feature totals, early/middle/late
   shares, wet-day count, CDD, Rx1day, Rx5day, and joint heat--moisture metrics.
2. **Aggregate benchmark:** compare seasonal precipitation and temperature
   feature responses to OSCAR-crop's aggregate climate inputs; explain, rather
   than silently absorb, departures attributable to timing/extremes.
3. **Sequence benchmark:** compare selected direct-feature distributions with
   STITCHES and, if used, MESMER-M-TP plus a daily generator.  A daily generator
   is not promoted merely because it has realistic unconditional weather.
4. **Marginal gate:** matched paths are identical before the pulse can affect
   climate; the zero-pulse control is identical at every year; pulse-size
   convergence is shown for every feature family before response/welfare runs.
5. **Support gate:** flag FAIR-evaluated features outside the historical
   empirical support separately for baseline and pulse.  No SCC is reported
   without an explicit extrapolation rule and sensitivity.
6. **Accounting gate:** this driver feeds the replacement agriculture module
   only.  It does not create a separate flood, temperature, CO2 fertilization,
   or agricultural add-on.

## Known limitations and fallbacks

The response curve cannot represent a circulation-driven change at identical
GMST that is not captured by its ESM/scenario training set.  Test this with
held-out scenarios and preserve ESM uncertainty.  If scenario dependence is
material and cannot be modeled without extrapolation, report it as climate
structural uncertainty rather than averaging it away.

If the direct-feature model fails distributional or pulse-convergence gates,
the fallback is a separately executed MESMER-M-TP + published daily
occurrence/amount generator, with monthly-total conservation and shared
innovations.  If that also fails, pause rather than train a new ML weather
emulator without a revised, pre-registered validation plan.

## Sources

* ISIMIP3 input-data documentation: https://www.isimip.org/gettingstarted/input-data-bias-adjustment/
* Lange et al., ISIMIP3BASD: https://doi.org/10.5194/gmd-12-3055-2019
* ISIMIP3 scenario and forcing description: https://doi.org/10.5194/gmd-19-4095-2026
* STITCHES: https://doi.org/10.5194/esd-13-1557-2022
* MESMER-M-TP: https://doi.org/10.5194/gmd-17-8283-2024
* OSCAR-crop: https://doi.org/10.5194/gmd-19-5857-2026
