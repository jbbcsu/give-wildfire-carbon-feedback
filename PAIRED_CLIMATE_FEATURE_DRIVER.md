# Paired climate-feature driver for marginal CO2 SCC runs

## Decision

The project owner approved this direct ISIMIP3b daily-feature route as the
primary matched precipitation-pattern path on 25 August 2026. The approval
authorizes acquisition and validation work under the gates below; it does not
pre-approve a coefficient, damage function, or SCC result.

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

The official repository catalogue was frozen on 26 August 2026 before any
feature-response fitting. The selected primary matrix is the complete set of
five available ESM realizations (GFDL-ESM4, IPSL-CM6A-LR, MPI-ESM1-2-HR,
MRI-ESM2-0, and UKESM1-0-LL), four experiments, and four daily variables: 80
public, unrestricted CC0 datasets at version `20210512`, representing
1,756,959,247,729 catalogue bytes. Dataset IDs, members, sizes, year coverage,
and DOI are pinned in
`data/provenance/isimip3b_daily_catalog_selection.csv`; the executable selector
also checks every advertised file SHA-512, URL, version, size sum, and
contiguous 1850--2014 or 2015--2100 year coverage against saved official API
responses. This is metadata selection, not acquisition or climate validation.

The bounded MRI-ESM2-0 SSP3-7.0 precipitation smoke progressed from the
official sidecar/header check to the complete 1,241,058,098-byte 2015--2020
file. Its full SHA-512 matches; the decoded block has 2,192 exact daily noon
steps on the registered 360 by 720 global 0.5-degree grid, precipitation-flux
units, 568,166,400 finite values, no missing or negative values, and
215,127,839 genuine zeros. This section validates one projection input block.
The separately pinned 2011--2014 historical `pr`/`tas` files and boundary
audit now close the exact join for this MRI engineering case only; other
variables, ESMs/scenarios, fitted feature responses, and SCC use remain open.

1. Retain the frozen five-ESM/member selection with daily `pr`, `tas`,
   `tasmin`, and `tasmax` over historical plus `ssp126`, `ssp370`, and
   `ssp585`. Keep model/member identity in every file and output row; changing
   this set requires a versioned, outcome-blind amendment.
2. Download one ESM/scenario/variable block at a time.  Build crop-year/stage
   features by latitude partition, write a compact feature table, verify it,
   and then archive or remove the raw block according to the source terms and
   local storage policy. Chronologically adjacent files are opened as one
   audited daily series: grids and units must match and the boundary must have
   exactly one-day steps without duplicates or gaps. Raw projections are not committed.
3. Build annual GMST from the pinned daily `tas` files belonging to the *same
   CMIP6 ESM/member/scenario* as the feature rows. `build_same_realization_gmst.py`
   uses cos(latitude) grid weights and complete decoded calendar years. The
   source ID and Kelvin value must be unique within every ESM/member/scenario/year
   across feature families. Record any later anomaly baseline separately; do
   not substitute FAIR temperatures during fitting. Synthetic failure modes
   and one real MRI-ESM2-0 historical 2011--2014 plus SSP3-7.0 2015--2020
   `tas` content/GMST smoke have passed. The matching `pr`/`tas` files join at
   an exact 24-hour historical/future boundary; the other ESM/scenario cells
   have not passed.
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

`scripts/validate_paired_feature_emulator.py` makes the design gates
executable. It requires the complete ESM/scenario/feature training product,
same-realization finite physical GMST values and identifiers, exact whole-ESM and whole-scenario
holdout coverage, common baseline/pulse residual IDs, independently evaluated
support flags, pre-divergence and zero-pulse identity, and agreement plus
convergence across at least three decreasing positive pulse sizes. Synthetic
failure tests pass. A bounded aggregate artificial-Kelvin feature smoke passes
these mechanics over 880 rows, but is not FAIR. The pinned core GIVE/FAIR
marginal model separately passes a 2,204-row zero/pre-pulse/baseline-identity
and three-scale temperature convergence gate for a 2020 CO2 pulse. The next
gate is ESM-specific absolute-baseline alignment and feature-level support.
A version-pinned sensitivity using a 2012--2014 historical overlap mean shows
that absolute anomaly mapping and centered-coordinate evaluation are the same
affine reparameterization to a maximum `4.55e-12` disagreement over 127,160
paired rows. Only 5.95% of temperature rows and 35.90% of feature rows remain
within the bounded seven-year training support per formulation. This rejects
promotion of the current affine smoke: mapped baseline GMST first exceeds
support in 2021 for GFDL, 2027 for MPI, and 2033 for the other three ESMs. The
sensitivity does not select a production
reference window or response form. No production feature response, damage, or
SCC path has passed.

The next support expansion is outcome-blind and hash-bound in
`config/isimip3b_later_century_expansion_v1.toml`. The official live API
snapshot pins 60 exact files (124,935,312,957 bytes) for 2041--2050 and
2091--2100 across all five registered realizations, three SSPs, and `pr`/`tas`.
Only harvest years fully contained inside those blocks are eligible. Each file
must still pass its full checksum/content gate, same-realization GMST and crop-
feature reconciliation, and the joined whole-ESM/whole-scenario rerun. The
blocks are noncontiguous, and every FAIR year after 2100 remains outside direct
ISIMIP daily-feature training support.
The first registered GFDL-ESM4 SSP1-2.6 `pr`/`tas` pair for 2041--2050 now
passes full SHA-512 and decoded 3,652-day global-grid content gates. `pr` has no
missing or negative values; `tas` has no missing values and produces ten
annual same-realization GMST rows. The preregistered eight harvest years then
produce 5,488 seasonal and 16,464 stage maize/rainfed rows on the bounded two-
latitude-row smoke, with exact additive reconciliation. This closes two of 60
file gates and one feature block; joined holdouts and support remain open.

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
