# Drought metrics plan

## Decision

Add drought metrics as explicit, competing representations of water stress.
PDSI/scPDSI and SPEI are serious candidate predictors, especially for the U.S.
yield validation, and receive the same outer-validation priority as direct
precipitation features. They are not relegated to an after-the-fact robustness
check. The parsimonious direct-weather reference remains joint temperature plus
crop-calendar seasonal precipitation quantity; neither timing features nor a
drought index is privileged before validation.
The validated 54-column maize/soybean candidate basis contains direct-pattern
CDD, wet-day frequency and intensity, rainfall amount/timing, Rx1day, and
Rx5day. It does **not** contain SPEI or root-zone soil moisture. A separate CRU
scPDSI path now has fully validated aggregate-regime maize and soybean
candidate panels for 1982--1989 and 2012--2016, but no fitted response or future paired
drought path. CDD alone is not an
adequate drought representation because it omits antecedent moisture and
evaporative demand.

## Why PDSI is not simply another precipitation covariate

PDSI and SPEI summarize climatic water balance: both embed precipitation and
temperature-derived evaporative demand (and PDSI also uses a soil-water
accounting formulation).  Placing PDSI beside raw precipitation and
temperature in one unrestricted regression creates severe collinearity and
makes a ``precipitation-only'' attribution ambiguous. PDSI is therefore a
serious competing exposure family, not a control that is blindly stacked onto
the direct precipitation mechanism.

## Pre-specified exposure families

| Family | Main inputs | Role |
|---|---|---|
| Direct precipitation-pattern | Stage precipitation total, rainy-day frequency, conditional intensity, CDD, timing/concentration, Rx1/Rx5, joint temperature | Candidate family with joint temperature plus seasonal quantity as the parsimonious reference; add pattern terms only for stable incremental held-out value. |
| Climatic water balance | Crop-calendar-aligned SPEI at 1-, 3-, and 6-month accumulation windows; self-calibrated PDSI where coverage/resolution are adequate | Serious competing family; tests whether antecedent P-minus-PET stress predicts outcomes better and more stably than direct indicators. |
| Soil-moisture state | Root-zone/total-column soil moisture anomaly, with prior-season and stage values | Physical mediator benchmark, particularly where irrigation or stored water decouples rainfall from crop water. |
| Compound drought | Pre-specified hot-dry and wet-heat indicators, using temperature plus SPEI/soil-moisture class | Extreme-risk evaluation, not a substitute for the continuous primary response. |

## Data and construction gates

### Global grid-cell panel

1. Retain the native daily ISIMIP precipitation and temperature features.
2. Acquire a versioned potential-evapotranspiration or physically consistent
   meteorological-input set and an ISIMIP soil-moisture product appropriate to
   the historical/projection experiments.  Record units, land-model/source,
   temporal resolution, grid, license, bias-adjustment lineage, and checksum.
3. Compute SPEI from a declared monthly water-balance series and a fixed
   historical calibration period.  Align 1-, 3-, and 6-month windows to
   planting and each crop stage rather than calendar year.  Do not fit the
   standardization distribution using holdout or future data.
4. Use self-calibrated PDSI only if its spatial/temporal resolution passes a
   coverage check against the 0.5-degree crop grid. It competes with, rather
   than supplements, the direct daily crop-season representation.
5. For every index, compute the paired baseline/pulse change from the same
   climate-model member, scenario, and bias-adjustment protocol.

The executable CRU benchmark path partially implements item 4 without
estimating a response. `build_crop_stage_scpdsi_features.py` converts monthly
CRU scPDSI to day-weighted crop-stage means, stage minima, and monthly-index
day-equivalents at or below an explicit threshold. A monthly index value is
assigned to every overlapping calendar day; these are not observations of
daily drought occurrence. The builder normalizes longitude conventions but never
interpolates, requires exact 0.5-degree grid correspondence and complete
monthly coverage, and excludes an entire crop-year key if any irrigation
calendar lacks a complete stage. The validator and partition combiner retain a
machine-readable historical-only role.

`allocate_irrigation_scpdsi_basis.py` then constructs 16 seasonal/stage mean,
minimum, threshold day-equivalent, and threshold-fraction features inside each regime
before applying fixed MIRCA-2000 area shares. It emits no direct precipitation
or temperature columns. Source-bound manifests tie every partition to the raw
CRU and calendar hashes and embed the exact planting/maturity fields used by
the direct-weather panels. The candidate validator fully recomputes allocation
from those derived stage tables and checks their manifest chain; it does not
claim to recompute every monthly metric directly from raw CRU. It rejects any fit, causal,
future, or SCC authorization. The 2012--2016 output has 150,490 maize rows
(59,772 positive GDHY outcomes) and 110,336 soybean rows (26,601 outcomes).
The 1982--1989 output has 240,784 maize rows (115,758 outcomes) and 176,537
soybean rows (47,653 outcomes).
The -2 threshold remains a diagnostic construction value rather than a
selected production threshold. Use `run_scpdsi_candidate_chunk.sh` to reproduce
the partition, allocation, and validation chain. No complete SPEI,
soil-moisture, fitted drought-response, or future paired-drought product exists.
These fields are eligible only for the climatic-index benchmark family; they
are not stacked into the direct-pattern model and are not projected as SCC
inputs.

### US county validation panel

1. Derive full-period county direct-weather features from nClimGrid-Daily using
   county-polygon area weighting as the primary county-average proxy. Evaluate
   fixed-CDL crop-pixel weighting separately, with gridMET and Daymet as weather-
   product robustness routes where their support and trend limitations permit.
2. Acquire the weekly U.S. Drought Monitor (USDM) archive as an **observed
   composite-drought validation outcome**, not a future climate input. Match
   spatially aligned county drought-severity weeks to NASS yields and estimate
   a Kuwayama et al.-style fixed-effect benchmark separately for high-rainfed
   and mixed/irrigated samples.
3. Obtain the documented gridMET reference-ET and PDSI products, and calculate
   crop-year SPEI under a fixed calibration rule.  Retain source PDSI as an
   independent implementation check rather than silently substituting it for
   our calculation.
4. Link drought state to the crop calendar, including pre-plant, planting,
   vegetative, reproductive, and grain-fill windows.  This permits wet-planting
   and subsequent drought to have distinct effects.
5. Keep the initial high-rainfed-share sample.  In an irrigated extension,
   treat soil moisture/PDSI as potentially affected by irrigation and avoid
   conditioning away the irrigation mechanism without an explicit estimand.

## Linking drought occurrence to climate change

This is a two-link analysis, and both links must be estimated/validated:

1. **Climate to drought occurrence.** For each crop/grid/year and each matched
   climate-model member, derive drought exposure from the daily/monthly
   baseline path and the paired CO2-pulse path.  Examples are weeks below a
   fixed SPEI threshold, crop-stage soil-moisture percentile deficits, or
   drought severity/duration classes.  The climate-induced change is
   `D(pulse) - D(baseline)`, never a comparison of unrelated scenarios or GCM
   members.
2. **Drought occurrence to agricultural outcome.** Estimate a stage-specific,
   nonlinear yield response to the same drought exposure, with crop/location
   and time controls and the declared adaptation scenario.  For the US,
   USDM-week results are an external observed composite-drought validation;
   global SCC projections use indices reproducible from climate/hydrology
   fields, not a presumed future USDM label.

For a water-balance drought index with precipitation `P` and temperature/PET
drivers `Z`, the total climate-induced drought change is
`D(P_pulse, Z_pulse) - D(P_base, Z_base)`.  If an attribution between
precipitation and the other climate drivers is reported, use a symmetric
paired (Shapley) decomposition, e.g. average the two precipitation increments
obtained by changing `P` first and changing `P` second.  Label this an
accounting attribution, because the drought index is a joint physical
function.  Yield/SCC accounting must use either the direct
precipitation-pattern response or the drought-response pathway for the same
moisture stress; do not sum both.

### Validation gates for the climate-to-drought link

* Historical agreement: compare climate-derived U.S. drought occurrence to
  USDM severity weeks without refitting thresholds on final holdouts.
* Physical agreement: compare SPEI/PDSI/soil-moisture drought ranking and
  duration, and report their disagreement as drought-definition uncertainty.
* Projection integrity: retain GCM, scenario, calendar, and baseline/pulse IDs
  on every drought record; fail on unmatched IDs.
* Counterfactual integrity: no precipitation/temperature/PET change implies no
  climate-induced drought increment and hence no drought-pathway marginal
  damage.

## Estimation and interpretation rules

* Compare direct-pattern, SPEI/PDSI, and soil-moisture families in the same
  nested spatial/time/extreme holdouts; tune only in training folds.
* Report performance, calibration, tail behavior, and feature coverage.  Do
  not select an index because it produces a larger SCC.
* Report null and adverse comparisons. Permit the seasonal-quantity reference,
  PDSI/scPDSI, or SPEI family to lead if it is more stable and parsimonious;
  retain distribution features only where they add robust incremental
  out-of-sample value.
* The direct-pattern model supports a declared precipitation-pattern
  attribution.  Water-balance/soil-moisture models support total climate-water
  stress estimates; any precipitation-only decomposition must be recomputed
  from a paired counterfactual, not read off a coefficient.
* Retain a near-best validated model set, including drought-family uncertainty.
* Require no-climate-change, fixed-temperature/CO2, and fixed-precipitation
  pulse tests before SCC integration.

## Sources

* [Dai (2011)](https://doi.org/10.1029/2010JD015541) documents PDSI variants,
  their potential-evapotranspiration assumptions, and limitations.
* [Vicente-Serrano, Begueria, and Lopez-Moreno (2010)](https://doi.org/10.1175/2009JCLI2909.1)
  introduces SPEI as a multi-scalar water-balance drought index.
* [Fishman (2016)](https://doi.org/10.1088/1748-9326/11/2/024004) motivates
  retaining direct daily rainfall distribution independently of a drought
  summary index.
* [Kuwayama et al. (2019)](https://doi.org/10.1093/ajae/aay037) estimates
  county fixed-effect yield/farm-income responses to U.S. Drought Monitor
  severity weeks and directly motivates the US external-validation benchmark.
* [Fontes, Gorst, and Palmer (2020)](https://doi.org/10.1017/S1355770X2000011X)
  demonstrates that drought-index definition can materially change estimated
  rice losses, motivating index-family uncertainty rather than one privileged
  drought metric.
* The [CRU global scPDSI documentation](https://crudata.uea.ac.uk/cru/data/drought/)
  supplies a monthly 0.5-degree historical benchmark and states its ODbL terms;
  its 355 MB current netCDF is small enough to retain separately from the
  multi-gigabyte ISIMIP daily fields. The exact acquisition is recorded in
  `data/provenance/cru_scpdsi.toml` and a raw-data manifest.
