# Drought metrics plan

## Decision

Add drought metrics as an explicit, competing representation of water stress.
The current feature panel contains maximum consecutive dry days (CDD),
wet-day frequency, rainfall total, and heavy-rain metrics, but it does **not**
yet contain PDSI, SPEI, or root-zone soil moisture.  CDD alone is not an
adequate drought representation because it omits antecedent moisture and
evaporative demand.

## Why PDSI is not simply another precipitation covariate

PDSI and SPEI summarize climatic water balance: both embed precipitation and
temperature-derived evaporative demand (and PDSI also uses a soil-water
accounting formulation).  Placing PDSI beside raw precipitation and
temperature in one unrestricted regression creates severe collinearity and
makes a ``precipitation-only'' attribution ambiguous.  PDSI is therefore a
robustness/benchmark exposure family, not a control that is blindly stacked
onto the direct precipitation mechanism.

## Pre-specified exposure families

| Family | Main inputs | Role |
|---|---|---|
| Direct precipitation-pattern | Stage precipitation total, rainy-day frequency, conditional intensity, CDD, timing/concentration, Rx1/Rx5, joint temperature | Primary attribution model: preserves a transparent precipitation-pattern counterfactual. |
| Climatic water balance | Crop-calendar-aligned SPEI at 1-, 3-, and 6-month accumulation windows; self-calibrated PDSI where coverage/resolution are adequate | Drought robustness model; tests whether antecedent P-minus-PET stress predicts outcomes better than direct indicators. |
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
   coverage check against the 0.5-degree crop grid.  It is an external
   robustness benchmark, not a substitute for daily crop-season exposures.
5. For every index, compute the paired baseline/pulse change from the same
   climate-model member, scenario, and bias-adjustment protocol.

### US county validation panel

1. Derive county crop-area-weighted direct weather features from gridMET and
   validate against Daymet where feasible.
2. Obtain the documented gridMET reference-ET and PDSI products, and calculate
   crop-year SPEI under a fixed calibration rule.  Retain source PDSI as an
   independent implementation check rather than silently substituting it for
   our calculation.
3. Link drought state to the crop calendar, including pre-plant, planting,
   vegetative, reproductive, and grain-fill windows.  This permits wet-planting
   and subsequent drought to have distinct effects.
4. Keep the initial high-rainfed-share sample.  In an irrigated extension,
   treat soil moisture/PDSI as potentially affected by irrigation and avoid
   conditioning away the irrigation mechanism without an explicit estimand.

## Estimation and interpretation rules

* Compare direct-pattern, SPEI/PDSI, and soil-moisture families in the same
  nested spatial/time/extreme holdouts; tune only in training folds.
* Report performance, calibration, tail behavior, and feature coverage.  Do
  not select an index because it produces a larger SCC.
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
