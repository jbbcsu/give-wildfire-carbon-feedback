# Soybean global precipitation-response readiness audit (2026-09-28)

## Decision

Soybean is the strongest resident non-maize crop path. Its outcome, daily-weather, crop-calendar, fixed irrigation-share, direct-pattern, heat-control, and historical climatic-water-balance inputs are already continuous and validated for 1982–2016. Wheat was not expanded because the existing annual MIRCA Wheat maps do not identify GDHY spring versus winter wheat outcomes, whereas soybean has an identified single-season mapping and production-eligible weights.

Soybean is **not** ready for a global causal response, geographic winners/losers, damages, or SCC. Existing predictive gains are small and unstable; the country geography is a crop-footprint proxy; the response protocol is not frozen; spatial value weights remain unauthorized; and no matched marginal-CO2 baseline/pulse climate path exists.

## Exact resident chain

| Component | Exact support | Readiness boundary |
|---|---|---|
| Aggregate GDHY outcome + direct weather | 837,690 rows; 23,934 cells; every year 1982–2016; 206,087 positive outcomes in 6,001 cells; 199,457 direct-only consecutive positive pairs | GDHY is an observation-aligned modeled gridded yield, not direct farm microdata or an instrumented causal outcome |
| Direct and heat candidate panels | Both have 837,690 rows and 206,087 positive outcomes; soybean heat threshold is 30°C | One aggregate yield per cell-year; no rainfed/irrigated outcome duplication |
| Historical scPDSI alternative | 772,352 rows and 204,917 positive outcomes | Narrower support; mutually exclusive climatic-water-balance family, never stacked automatically with direct precipitation |
| GGCMI soybean calendars | `noirr` and `firr`, Phase 3 v1.01; 67,420 finite cells each; season lengths 69–224 and 69–223 days | Calendar source is ready for this single soybean season |
| MIRCA-OS 2000 exposure weights | 48,108 regime rows, 24,054 cells; shares sum to one exactly; 74,092,998.214 ha total, 6,093,136.444 irrigated and 67,999,861.770 rainfed | Fixed area shares are exposure weights, not latent regime production shares |
| Historical pair-area coverage | 89.2881% of global positive MIRCA soybean area lies in cells with a 1982–1989 consecutive observed pair | Missing 10.7119% is not renormalized or assigned zero response |
| Candidate value inputs | MapSPAM: 335,460 positive 5′ cells and 160,731,545.500 t; FAOSTAT baseline constant-dollar values in 75 countries; 98.6303% of MapSPAM soybean production is in 65 matched-value codes | Spatial value weights remain unauthorized because unmatched/missing codes remain and no renormalization is allowed |

The positive-outcome support is near 6,000 cells annually through 2010, falls to 5,468 in 2011, and reaches 4,873 in 2015 before returning to 5,468 in 2016. The known GDHY support discontinuity remains observed rather than repaired.

All nonlinear response bases are constructed within `noirr` and `firr` before fixed MIRCA weighting, preserving one outcome row. Direct precipitation, climatic-water-balance, and any future soil-moisture family remain mutually exclusive. The resident soil-moisture family is absent.

## What existing response evidence does—and does not—show

The continuous spatial audit uses 166,870 training pairs and 26,004 terminal pairs over 56 and 55 occupied 10-degree blocks. Relative to heat controls, seasonal quantity lowers pooled RMSE by `0.0009495`, but its paired block-bootstrap interval is `[-0.0023005, +0.0005352]`. Adding distribution lowers pooled RMSE by `0.0010117` relative to quantity, with interval `[-0.0025177, +0.0007341]`. Neither interval excludes zero.

The independently later-period rainfed confirmation also fails: on 21,026 pairs in 55 blocks, the full-distribution model improves point RMSE by `0.0017217`, but the interval is `[-0.0083876, +0.0031269]`, only 2 of 5 folds improve, and 41.8% of blocks improve. A nonlinear quantity extension worsens terminal pooled RMSE by `0.0037283`; its required country bootstrap is unsupported.

Country support is not a ready heterogeneity estimand. Of 166,870 training pairs, 157,003 receive exactly one crop-footprint country proxy, 7,069 are ambiguous, and 2,798 are absent. Only 21 country labels remain, and prior terminal folds contain 6/5/5/1/4 scoring countries. The singleton fold invalidates the prescribed country bootstrap. These labels are not authoritative administrative ownership and cannot establish economic winners or losers.

Historical associations are descriptive only. They use equal-weight grid pairs, observational weather variation, modeled GDHY yields, conditional fixed effects, and spatial-cluster approximations. They do not establish exogenous precipitation variation, identify latent irrigation-regime slopes, or supply causal uncertainty. The independently validated Tuninetti–Davis benchmark supports water-stress relevance but has weak and mixed spatial concordance and explicitly fails its yield-response gate.

## Single safest next computation

Freeze and run a **soybean continuous design-and-heterogeneity preflight**, without estimating yield slopes.

The preflight should use the 1982–2010 continuous soybean support, fixed-2000 MIRCA basis-before-weighting, one GDHY outcome, cell first differences, and predeclared country- or region-year controls. Seasonal direct precipitation quantity is the primary moisture family. Direct distribution and climatic-water-balance views are evaluated separately; they are never stacked. The output should contain only:

- residualized rank and condition numbers;
- within-country/block precipitation variation and common overlap;
- pair, year, cell, country, and 10-degree-block support;
- leverage and effective cluster counts; and
- the finest support-qualified geographic resolution that could be preregistered for a later response fit.

This is higher value than another immediate response regression because it directly tests the present blocker: whether a stable geographic response/heterogeneity design exists after realistic fixed effects and support restrictions. It remains outcome-blind apart from identifying positive-yield rows. A later slope fit requires a separate frozen response protocol, a declared attribution decomposition, influence and overlap gates, and a clear statement that any estimate remains observational unless a credible identification strategy is supplied.

## Reproduction and validation

- contract: `config/soybean_global_response_readiness_audit_v1.toml`
- builder: `scripts/audit_soybean_global_response_readiness.py`
- audit: `data/provenance/soybean_global_response_readiness_audit_20260928.json`
- independent validator: `scripts/validate_soybean_global_response_readiness.py`
- validation: `data/provenance/soybean_global_response_readiness_validation_20260928.json`

The independent validator streamed the continuous panel, recomputed every annual support count and all 199,457 direct-only consecutive pairs, re-read both calendars and MIRCA weights, and rechecked the response artifacts and fail-closed gates. Builder peak RSS was 502,497,280 bytes; validation peak RSS was 249,479,168 bytes, both below 536,870,912 bytes. No response was fit and no coefficient, damage, SCC, or GIVE input was produced.
