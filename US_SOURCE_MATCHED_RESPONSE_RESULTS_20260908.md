# Regional climate and source-matched U.S. associations

Completed September 8, 2026. These are historical climate-input comparisons
and exploratory yield associations, not causal precipitation damages or SCC.
Aggregate: `data/provenance/us_source_matched_response_20260908.json`.

## What advanced

All 54 regional daily climate cutouts validated. The persistent chain then
immediately constructed county-season features and compared them, without a
new manual launch between those stages. It finished at 07:53:22 UTC after
starting at 07:29:04 UTC. The next source-matched study was registered while
acquisition ran, then implemented, input-bound, estimated and numerically
checked after that chain finished. No simultaneous analysis jobs were used.

The wider geography retains 6,092 corn county-years in 345 counties and 4,308
soybean county-years in 252 counties, 1982–2010. Those are weather keys; each
has both irrigation-practice outcomes. One corn county, GEOID 48355, contributes
two excluded county-years because its polygon is only partly in the finite
climate domain. No sample threshold was reduced. The 687 selected daily cells
produce 10,400 rows per climate path. Both original 573-row pilot parities
pass the unchanged tolerance; largest residual is 3.91e-14 C.

## Climate comparisons on the wider retained sample

Equal-county means, not national or production-weighted means:

| Seasonal feature | Corn factual minus counterclim | Soy factual minus counterclim | Corn GSWP factual minus nClimGrid | Soy GSWP factual minus nClimGrid |
|---|---:|---:|---:|---:|
| Precipitation, mm | +22.83 | +23.17 | +32.56 | +26.08 |
| Longest dry spell, days | -2.11 | -2.29 | -1.81 | -2.09 |
| Maximum five-day precipitation, mm | -0.21 | -1.34 | +1.93 | +0.95 |
| Stage 2 mean temperature, C | +0.575 | +0.277 | +0.352 | +0.393 |
| Stage 2 Tmax exceedance, C days; corn 29 C / soy 30 C | +11.01 | -5.44 | +37.72 | +33.03 |

The soybean threshold-heat contrast is negative here, unlike the earlier
narrow pilot. Do not substitute the narrow-pilot sign for this wider result.
Feature differences do not imply a net yield benefit or loss. Factual versus
ATTRICI counterclim is a conditional historical trend comparison, not an
anthropogenic forcing attribution or a marginal CO2-pulse experiment.
No zero-rain rows are excluded from the regional shape comparison.

## Same outcomes, two independently fitted factual weather sources

All 32 registered fits completed: two sources, two crops, two practices, two
moisture forms, two heat thresholds. No zero-rain sample sensitivity was
needed. Outcomes, county-years and fixed NASS calendars are identical across
weather-source fits. Quantity is primary, with stage means and daily threshold
heat controlled linearly and quadratically. County and state-year fixed
effects are included. Timing is an exploratory incremental candidate, not
promoted by in-sample fit.

Primary-threshold quantity coefficients below multiply P/100 and (P/100)^2
in the log-yield equation. They are NOT percent effects of a 100 mm increase:
the response to an increment depends on starting rainfall and both terms.

| Crop / practice | nClimGrid linear | nClimGrid quadratic | GSWP linear | GSWP quadratic |
|---|---:|---:|---:|---:|
| Corn / non-irrigated | 0.16916 | -0.01376 | 0.24804 | -0.01778 |
| Corn / irrigated | 0.03436 | -0.00391 | 0.03853 | -0.00388 |
| Soy / non-irrigated | 0.18484 | -0.01682 | 0.23276 | -0.01939 |
| Soy / irrigated | 0.03212 | -0.00358 | 0.03295 | -0.00352 |

Both sources give a concave fitted amount relationship. The non-irrigated
coefficient pairs change appreciably with source, whereas irrigated pairs
are closer in this comparison. This is not a formal source-difference test,
an irrigation treatment effect, or proof that either weather source is true.
The aggregate preserves all 32 coefficient and standard-error vectors, not
just these eight fits. Their county-cluster uncertainty convention does not
fully adjust for absorbed-effect degrees of freedom or cross-county error
dependence. No interval-overlap test of source differences is performed.

Neither the same inspected historical years nor in-sample residual RMSE is a
new independent validation. No counterclim yields, adaptation responses,
global damages or SCC increments have been calculated with these coefficients.
Next useful calculation: predeclare common-reference rainfall contrasts and
their source-specific support, then a paired source-difference uncertainty
calculation; do not choose source-specific percentiles and call them matched.

## Numerical and resource audit

Four synthetic tests passed. All 32 fits passed unchanged sample, residual-
scale and QR gates; maximum scaled condition number 43.9513. Numerical
replication independently reconstructed bases and used SVD plus a cross-
product cluster sandwich, while explicitly sharing the tested fixed-effect
residualizer. Maximum coefficient discrepancy 4.44e-15; covariance discrepancy
5.06e-14; maximum scaled residualized group mean 3.14e-14. This checks numerical
implementation, not identification or independent outcome validation.

The first replication emitted floating-point warnings at matrix multiplication
although its saved numerical comparisons were finite and passed. That run,
log and source revision 79e367d are preserved. A separate rerun replaced those
reductions with explicit einsum operations, enabled floating-error exceptions
and required finite diagnostic moments. It passed all 32 comparisons without
warnings. No original fit, data, tolerance or inference gate was changed;
the underlying cause of the first warnings has not been established here.

Across 225 recorded regional acquisition/test/build/response jobs, the highest
sampled RSS was 779.09 MiB during feature construction. Source fitting peaked
at 282.86 MiB and took 4.46 seconds. Regional acquisitions, requests, climate
features and response artifacts retained 918.66 MiB cumulatively before export;
this excludes previous pilots and resource logs, not all project storage.
Free disk was 157.25 GiB at export. The 531,151-byte public summary contains
no raw climate, NASS yield rows, full county weights or coefficient covariances.

An initial export invocation was rejected before execution because owned-disk
accounting only allows ignored interim paths. It was rerun to an ignored
interim file for subsequent publication; that guard was not relaxed. Complete
ignored originals remain under `data/interim/us_regional_county_climate_20260908/`
and `data/interim/us_source_matched_response_20260908/`.
