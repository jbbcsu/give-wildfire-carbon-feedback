# Functional-form benchmark for the US county validation track

## Purpose and source boundary

This note records how the online appendix to Blumberg (2026), Chapter 4,
*Assessing the sensitivity of climate change impacts in agriculture to the
climate--economy functional form*, informs this **US validation** component.
It is not a replication of the chapter and does not use its unpublished
estimation data or coefficients.  The chapter DOI is
https://doi.org/10.4337/9781035344970.00011.  The accessible source is the
online appendix supplied to this project on 2026-08-20.

The appendix compares seasonal means, growing-degree-day, daily-bin, and
hourly-bin weather representations, paired with alternative geographic-time
fixed-effect structures.  Its figures show that in-sample criteria and
cross-validation can favor different specifications.  It also presents an
east/west-of-100th-meridian irrigation-related heterogeneity check.  Those are
methodological inputs; they do not establish a precipitation-pattern effect or
a rainfed-crop effect for this project.

## What we adopt

1. **Functional-form uncertainty is first class.**  The primary analysis will
   compare pre-specified, interpretable specification families instead of
   declaring a single seasonal-total model correct from in-sample fit.
2. **Forecast validation matters.**  Selection is based on nested,
   outcome-held-out rolling-year and spatial-block validation.  Random K-fold
   is reported only as a descriptive comparison, because adjacent county-year
   observations are dependent.
3. **Fixed effects are a design dimension.**  County fixed effects and year
   fixed effects are the causal baseline.  State-by-year and USDA
   Farm-Resource-Region-by-year variants are robustness specifications, with
   their loss of usable weather variation reported explicitly.
4. **Irrigation is a measured selection problem.**  The 100th meridian is an
   historical descriptive split, not a rainfed classifier.  The primary sample
   remains counties passing a crop-specific irrigated-area gate.  The meridian
   result is one heterogeneity robustness check only.

## Planned comparison set

All candidates condition jointly on temperature, use the same crop calendar,
county/crop area weights, outcome sample, and training folds.  No candidate
may use holdout outcomes to choose features or tuning parameters.

| Family | Precipitation representation | Role |
|---|---|---|
| Total-only benchmark | Crop-season total and a low-order nonlinear transformation | Reference to quantify what timing/extremes add |
| Seasonal-shape model | Total plus normalized stage shares, concentration (HHI), timing centroid, wet-day frequency, and conditional wet-day intensity | Main interpretable distribution model |
| Dry/wet-extreme augmentation | Seasonal-shape model plus consecutive dry days and pre-specified Rx1/Rx5/heavy-rain metrics by crop stage | Tests exposure to deficits and excess rain beyond total quantity |
| Daily/binned robustness | Pre-specified daily precipitation and temperature bins, aggregated within crop stages | Flexible nonparametric benchmark analogous in spirit to the appendix's binned-weather alternatives |
| Penalized nonlinear robustness | Group-regularized spline/GAM or similarly constrained learner with all climate inputs grouped by mechanism | Captures smooth nonlinearities; must retain interpretable partial responses and blocked holdout results |

LSTM-style sequence models are not in the first estimating set.  They need a
larger, harmonized daily crop-weather panel and strict temporal/spatial
out-of-sample tests.  If added, they will be compared against the five
families above and process-based crop-model outputs rather than being treated
as evidence by default.

## Outcomes, estimand, and non-overlap

The first outcome is crop-specific NASS county yield for counties meeting the
irrigation gate.  This differs from the appendix's net-farm-income-per-acre
illustration.  Yield avoids conflating climate response with prices, input
costs, and non-crop activities, but is not a welfare measure.  A later,
separate value/price pass is required before SCC translation.  The US module
therefore validates response shape and heterogeneity; it does not create an
additional US agricultural SCC term alongside the global component.

The short-run weather-shock estimand is also not automatically a permanent
climate-response function.  Fixed, trend, and upper adaptation scenarios are
handled after response estimation, with a scenario label on every projection.
Temperature, CO2 fertilization, and adaptation cannot be added separately
when already embodied in a fitted response without an explicit decomposition.

## Selection and reporting protocol

1. Lock crop, years, crop mask, irrigation threshold, candidate families, and
   hyperparameter grids before opening the final holdout outcomes.
2. Tune only in inner blocked folds.  Outer tests are: future years, spatial
   blocks/states, and climate-feature-defined dry/wet extremes.
3. Report RMSE/MAE, calibration, tail errors, spatial coverage, and stability
   of marginal precipitation-pattern responses.  Report fit statistics only
   as diagnostics.
4. Retain a near-best set under a pre-specified blocked-validation tolerance
   and propagate its model uncertainty.  Do not choose a model solely because
   it generates a larger or smaller SCC.
5. Report county, crop, irrigation-gate, fixed-effect, climate-data, and GCM
   sensitivity results.  The latter applies only after historical validation
   passes and paired future baseline/pulse weather paths exist.

## Immediate implementation consequence

The NASS ingestion contract remains the first executable step.  Before an
estimation table is accepted, the project must acquire a documented
crop-specific irrigated-area source, crop-area weather weights, and a daily
weather archive.  The appendix improves the empirical design; it does not
remove those input gates.
