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
latitude-row smoke, with exact additive reconciliation. The matching 2091--
2100 pair and 2092--2099 feature block pass the same gates. The GFDL SSP3-7.0
2041--2050 pair now also passes those gates. Relative to the matched SSP1-2.6
cells, its 2042--2049 smoke is 0.574 C warmer and has 18.33 mm less seasonal
rain, 1.11 fewer wet days, and a 3.20-day longer maximum dry spell on average;
these are descriptive climate differences, not a response estimate. The
registered GFDL SSP5-8.5 2041--2050 pair and its bounded feature block also
pass. The SSP3-7.0 and SSP5-8.5 2091--2100 pairs and bounded 2092--2099 feature
blocks pass. The next IPSL-CM6A-LR SSP1-2.6 2041--2050 and 2091--2100 pairs
pass the same gates with their exact model-specific 12:00 daily timestamps,
followed by the IPSL SSP3-7.0 2041--2050 and 2091--2100 pairs and bounded
feature blocks. Both IPSL SSP5-8.5 pairs and bounded feature blocks also pass,
closing 24 of 60 file gates and twelve feature blocks. The MPI-ESM1-2-HR
SSP1-2.6 2041--2050 and 2091--2100 `pr`/`tas` pairs then pass exact
byte/SHA-512, 3,652-step 12:00 decoded-content, same-realization GMST, and
bounded feature/reconciliation gates, bringing progress to 28 of 60 file gates
and fourteen bounded feature blocks. The MPI SSP5-8.5 2041--2050 pair and
bounded feature block also pass. Together with the separately registered MRI
SSP1-2.6 2041--2050 block, progress is 32 of 60 file gates and sixteen feature
blocks. Relative to exact-key MPI SSP1-2.6 cells, the SSP5-8.5
means are +0.237 C, +17.88 mm seasonal rain, +1.37 wet days, -1.00 maximum
dry-spell days, +1.71 mm Rx1day, and +6.75 mm Rx5day. No MPI whole-scenario or
whole-ESM inference is made from these three later-century cells.
The MRI SSP3-7.0 2041--2050 pair now passes exact checksum, full decoded
content, same-realization GMST, and bounded feature/reconciliation gates. Its
matched SSP3-7.0-minus-SSP1-2.6 means are +0.369 C, -11.02 mm rain, -1.07 wet
days, +0.23 maximum dry-spell days, -0.32 mm Rx1day, and +0.26 mm Rx5day.
Tracked progress is 34 of 60 file gates and seventeen feature blocks. A third
MRI SSP and both remaining end-century MRI scenario cells are still required
before whole-scenario or expanded whole-ESM inference.
The MRI SSP5-8.5 midcentury pair subsequently closes the three-scenario MRI
midcentury matrix at 36/60 file gates and eighteen feature blocks. Its matched
SSP5-8.5-minus-SSP1-2.6 means are +0.777 C, -8.81 mm rain, +0.28 wet days,
-2.83 maximum-dry-spell days, -1.50 mm Rx1day, and -2.68 mm Rx5day. The
181,104-row whole-scenario audit improves 15/33 comparisons (median RMSE ratio
1.00027; maximum 1.04233), including 4/11 for held-out SSP5-8.5, while
21,236 values (11.73%) fall outside the two-scenario support envelope. This is
adverse engineering evidence; end-century, whole-ESM, FAIR feature-support,
response, damage, and SCC gates remain open.
The MRI SSP1-2.6 and SSP3-7.0 end-century cells now also pass complete-file,
same-realization GMST, feature, and exact-reconciliation gates. Their matched
SSP3-7.0-minus-SSP1-2.6 means are +2.928 C, +2.24 mm seasonal rain, -0.97 wet
days, +2.41 maximum-dry-spell days, +0.25 mm Rx1day, and +1.15 mm Rx5day.
The MRI SSP5-8.5 end-century pair and bounded block now pass the same gates,
raising tracked progress to 42/60 files and twenty-one bounded blocks. Its
matched SSP5-8.5-minus-SSP1-2.6 means are +4.591 C, -13.23 mm seasonal rain,
-2.62 wet days, +5.44 maximum-dry-spell days, +0.75 mm Rx1day, and +0.56 mm
Rx5day. The 181,104-row MRI end-century whole-scenario audit improves 16/33
comparisons (median RMSE ratio 1.00006; maximum 1.06514), including 9/11 for
held-out SSP5-8.5, and flags 27,090 values (14.96%) outside support. This
mixed, adverse result does not authorize a response, damage function, or SCC
input; whole-ESM and FAIR feature-support gates remain open.
The remaining frozen MPI-ESM1-2-HR SSP3-7.0 mid- and end-century pairs and
SSP5-8.5 end-century pair now pass exact bytes/SHA-512, decoded content,
same-realization GMST, bounded maize/rainfed feature, and exact reconciliation
gates, raising tracked progress to 48/60 files and twenty-four blocks. Relative
to matched SSP1-2.6 cells, SSP3-7.0 changes from +0.447 C, -4.38 mm rain,
-0.36 wet days, and +2.53 maximum-dry-spell days at midcentury to +3.273 C,
-17.02 mm, -1.61 days, and +2.54 days at end century. End-century SSP5-8.5
changes are +4.251 C, -13.20 mm, -1.43 wet days, and +2.18 dry-spell days.
These are descriptive feature-cell contrasts. Whole-scenario, whole-ESM,
FAIR feature-support, response, damage, and SCC authorization remain open.
The registered 181,104-row MPI whole-scenario audits are also adverse. At
midcentury, GMST adjustment improves 14/33 comparisons (median/maximum RMSE
ratios 1.00163/1.05542) and 21,100 values (11.65%) are outside support. At end
century it improves 15/33 (1.00028/1.09814) and 27,605 values (15.24%) are
outside support. Neither result promotes the emulator.
The registered four-ESM whole-ESM evaluator joins GFDL, IPSL, MPI, and MRI
across the three SSPs. Each period has 724,416 rows and 44 whole-ESM
comparisons. Midcentury improves 27/44 versus the cell-mean benchmark
(median/maximum RMSE ratios 0.99954/1.00969) with 8.34% outside exact
three-ESM support. End century improves only 12/44 (1.00040/1.06362) with
9.47% outside support. UKESM is absent, so this adverse four-of-five audit
does not complete the frozen whole-ESM gate or authorize FAIR feature support,
a response, damage, or SCC input.
The first frozen UKESM1-0-LL later-century pair, SSP1-2.6 at midcentury, now
passes exact bytes/SHA-512, complete decoded-content, same-realization GMST,
bounded maize/rainfed feature, and exact reconciliation gates. Unlike the
other four ESM products, both UKESM fields are timestamped at 00:00 UTC; the
version-pinned validator's explicit midnight path passes and its default noon
path rejects the files. Tracked expansion is therefore 50/60 files and
twenty-five bounded blocks. The remaining five UKESM pairs and a complete
five-ESM holdout are still absent, so no production, response, damage,
welfare, or SCC gate is opened.
The matching UKESM SSP1-2.6 end-century pair then passes the same gates and
reproduces GMST, 5,488 seasonal rows, 16,464 stage rows, and reconciliation
byte-for-byte. End-century minus midcentury means over the separate fixed
maize slices are +0.849 C, -3.19 mm rain, +0.33 wet days, +0.49 maximum-dry-
spell days, +0.69 mm Rx1day, and +2.48 mm Rx5day. These are descriptive
period means, not an exact-key response. Coverage is 52/60 files and twenty-
six blocks; four UKESM pairs and all production gates remain open.
The matching UKESM SSP3-7.0 midcentury pair passes exact catalogue bytes and
SHA-512, explicit-midnight decoded content, same-realization GMST, and exact
5,488-season/16,464-stage reconciliation. Its exact-key SSP3-7.0-minus-
SSP1-2.6 means are +0.876 C, -6.76 mm rain, -0.72 wet days, +2.66 maximum-
dry-spell days, -0.53 mm Rx1day, and +1.60 mm Rx5day. Coverage is 54/60 files
and twenty-seven blocks. This is a climate-feature support diagnostic only;
three UKESM pairs and all production gates remain open.
Relative to matched IPSL SSP1-2.6 cells, mean SSP3-7.0 differences at
midcentury are +0.365 C, +13.22 mm seasonal rain, +0.93 wet days, -1.36
maximum dry-spell days, +2.18 mm Rx1day, and +3.84 mm Rx5day. The end-century
matched differences are +4.146 C, +25.70 mm seasonal rain, +2.85 wet days,
-2.26 maximum dry-spell days, +3.12 mm Rx1day, and +4.47 mm Rx5day. These are
descriptive climate differences, not a response estimate. The preregistered
IPSL midcentury comparison finds SSP5-8.5-minus-SSP1-2.6 means of +0.607 C,
+19.88 mm seasonal rain, +2.07 wet days, -0.77 maximum dry-spell days, +2.01
mm Rx1day, and +3.13 mm Rx5day. Its 181,104-row three-SSP whole-scenario audit
improves only 15/33 comparisons versus the cell-mean benchmark (median RMSE
ratio 1.00028; maximum 1.02568), including 3/11 for held-out SSP5-8.5;
20,529/181,104 values (11.34%) are outside the two-scenario envelope. The
matching IPSL end-century audit improves only 10/33 comparisons (median RMSE
ratio 1.00275; maximum 1.27466), including 2/11 for held-out SSP5-8.5, while
30,619/181,104 values (16.91%) are outside the two-scenario envelope. The
preregistered GFDL three-SSP midcentury product contains 181,104 rows. Its whole-scenario GMST
adjustment improves 14/33 feature comparisons versus the cell-mean benchmark,
with median RMSE ratio 1.00036 and maximum 1.06410; the SSP5-8.5 holdout
improves only 1/11. Exact held-out cell/feature flags place 20,562/181,104
values (11.35%) outside the two-scenario training envelope. The matching
end-century product also has 181,104 rows: the GMST adjustment improves 13/33
comparisons (median RMSE ratio 1.00110; maximum 1.23350), and 27,260 values
(15.05%) are outside the two-scenario envelope. This is adverse engineering
evidence, not a response. Reclassifying the validated FAIR paths against the
expanded 287.659--291.189 K GFDL GMST envelope moves the last within-
temperature-support baseline year from 2020 through 2300 while revalidating
common-random-number, zero/pre-divergence, and decreasing-pulse gates. Whole-ESM and FAIR
baseline/pulse feature-support gates remain open, so the emulator is not
promoted.

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
