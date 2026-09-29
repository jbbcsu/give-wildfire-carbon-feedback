# Pooled-only soybean precipitation-response and inference protocol

Date frozen: 2026-09-28
Contract: `soybean_pooled_response_inference_protocol_v1`

## Scope and boundary

This protocol defines a possible next response fit; it does not perform one. Protocol validation may read only frozen aggregate audits and synthetic data. It may not read real GDHY outcome magnitudes, estimate a real response coefficient, compute yield effects, label geographic or economic winners and losers, calculate damages or SCC, or integrate with GIVE.

The design preflight supports only a pooled global response. Country-, block-, cell-, and irrigation-specific slopes are prohibited. Country proxies may enter only as group-by-year controls. Ten-degree blocks may enter only as group-by-year controls, dependence clusters, overlap units, or influence-deletion units.

## Estimand and sample

The future primary regression outcome is the cell first difference in natural log soybean yield:

`Δ log(yield_it) = log(yield_it) - log(yield_i,t-1)`.

There is no offset, winsorization, or production/value weighting. A pair is eligible only when both consecutive GDHY levels are observed, strictly positive, and all covariates for the evaluated family are finite. The exposure basis remains fixed-2000 MIRCA rainfed/irrigated regime construction before fixed-area weighting. Estimation is equal-weighted by cell-pair; production or value weights belong only in a later economic aggregation protocol.

Training levels are 1982–2010 and pair end-years are 1983–2010. The year 2011 is an excluded buffer. Years 2012–2016 are locked for a terminal transport stress test. The primary sample requires a unique country proxy and is expected to contain 157,868 direct/heat pairs, 28 pair end-years, at least 5,600 cells, 21 country proxies, and at least 55 ten-degree blocks. Exact direct–scPDSI common support is expected to contain 157,003 pairs.

## Model and controls

Every family contains six temperature/heat controls: stage 1–3 mean temperature and stage 1–3 degree-days above 30°C. Cell fixed effects are removed by first differences.

The primary control specification demeans the differenced outcome and every differenced regressor within singleton-country-proxy × pair-end-year groups, then fits without an intercept. The global-year and ten-degree-block × year alternatives are mandatory sensitivities on the same singleton-country finite-pair support. No extra trend, post-treatment control, nonlinear term, or selected interaction may be added in v1.

The sole confirmatory moisture family is seasonal `log1p_precip_mm` quantity. The direct distribution challenger adds stage 1 and 2 precipitation shares (stage 3 is the reference), maximum consecutive dry days, Rx5day, and concentration HHI. The climatic-water-balance challenger contains seasonal mean scPDSI. Distribution and scPDSI are mutually exclusive, and neither may be stacked with the other or substituted automatically for quantity.

## Spatial dependence and inference

Primary uncertainty uses ten-degree spatial blocks, allowing arbitrary dependence across cells and years within each block and assuming independence only across blocks. Report both CR2 cluster-robust inference with Satterthwaite degrees of freedom and a restricted-null, studentized wild-cluster bootstrap-t with Webb six-point weights, 9,999 draws, seed 20260928, and two-sided α = 0.05. Heteroskedastic-only or country-clustered inference cannot serve as primary inference.

The quantity coefficient has no predeclared sign. Promotion requires a finite coefficient, positive finite CR2 standard error, two-sided CR2 and wild-bootstrap p-values no greater than 0.05, and both 95% intervals excluding zero. Directional or post hoc sign selection is prohibited.

## Prefit, overlap, and influence gates

Before real outcomes may be read for fitting, the exact primary support must have at least 150,000 pairs, 28 pair end-years, 5,500 cells, 50 raw blocks, 25 effective blocks, and 5 effective country proxies. No block may exceed 10% of pairs. Each design must be full rank, have scaled condition no greater than 10, maximum row leverage no greater than 0.005, p99 leverage no greater than 0.001, and top-1% leverage share no greater than 0.10.

Every occupied block must have quantity-change p05 below zero and p95 above zero, and at least half its quantity changes must lie inside the global p05–p95 interval.

Postfit influence checks require leave-one-block-out sign concordance of at least 90%, maximum leave-one-block-out coefficient movement no greater than 0.5 primary CR2 standard errors, no block above 20% of the score contribution, and no block above 20% of squared residuals. The primary sign must agree under both control sensitivities, and neither sensitivity may move by more than one primary CR2 standard error.

Any required-gate failure closes promotion. The result remains a diagnostic; a challenger is not substituted.

## Locked later-period validation

The terminal exercise is a within-country-year anomaly transport test, not an absolute-yield forecast. Training coefficients are applied unchanged to 2012–2016 covariates after terminal outcomes and covariates are independently demeaned within singleton-country × year. No response coefficient is re-estimated on terminal outcomes.

Quantity is compared with heat-only; distribution is compared with quantity; scPDSI is compared with quantity on exact common support. The paired loss is candidate RMSE minus reference RMSE, so negative values favor the candidate. A gate requires at least 20,000 terminal pairs, 40 blocks, a negative point loss difference, a ten-degree-block bootstrap 95% upper bound below zero using 9,999 draws and seed 20260928, and improvement in at least four of five terminal years.

The quantity-versus-heat test is primary. Distribution-versus-quantity and scPDSI-versus-quantity form a two-test Holm family at 5%. A passing challenger is only evidence for a new preregistered protocol version; it cannot replace quantity in v1.

The terminal period has already been inspected, so it is a binding stress test rather than fresh confirmation. Existing evidence is not promotable under the frozen rule: quantity-versus-heat has a bootstrap upper bound above zero; the later rainfed distribution confirmation fails; and scPDSI is worse than quantity in the existing terminal comparison. Those facts cannot be erased by refitting or retuning.

## Adaptation interface

Historical coefficients implicitly include realized adaptation but do not separately identify it. The primary projection interface is therefore `no_additional_adaptation`, with multiplier 1.0.

A separately labeled sensitivity may supply a globally uniform, exogenous attenuation path in `[0,1]`. It multiplies the projected weather-induced log-yield change after response evaluation and before economic aggregation. It may vary over time but not by country, block, cell, irrigation regime, income, or estimated response sign. It cannot alter the historical coefficient, modify MIRCA shares, be labeled empirical, or enter the primary result.

## Promotion states

1. `protocol_mechanically_validated` requires source hashes, internal contract checks, all synthetic tests, boundary checks, and the 512 MiB memory gate.
2. Reading real outcome magnitudes and fitting requires a separate explicit authorization after protocol validation.
3. `associational_fit_diagnostic` requires every prefit, inference, influence, and control-sensitivity gate.
4. `predictive_response_candidate` additionally requires the quantity terminal validation gate.
5. Neither state authorizes causal language. A causal response needs separate identification evidence.
6. Damage application needs a separate transport and economic-weight protocol. SCC use additionally needs a matched marginal-CO2 climate perturbation and GIVE integration protocol.

Thus even a completely passing future fit remains pooled and associational. It cannot support country/block response heterogeneity or winner/loser claims.
