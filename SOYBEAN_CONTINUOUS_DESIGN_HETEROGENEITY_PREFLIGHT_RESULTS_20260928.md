# Soybean continuous design and heterogeneity preflight — 2026-09-28

## Decision

The frozen, outcome-blind 1982–2010 soybean preflight passes a **pooled global design-support gate** but fails the predeclared **country-proxy response-resolution gate**. The finest support-qualified resolution is therefore `pooled_global`. This is not a fitted production response and does not identify geographic or economic winners and losers.

All downstream gates remain closed: no outcome slope, response coefficient, causal effect, yield effect, damage, SCC, or GIVE integration was computed or authorized.

## Frozen design

- One GDHY soybean outcome per cell-year; the outcome was read only to retain observed, strictly positive-yield levels. Outcome magnitudes were discarded immediately after masking.
- Training levels: 1982–2010. Consecutive cell first differences: pair end-years 1983–2010.
- Fixed-2000 MIRCA rainfed/irrigated basis constructed before area weighting; the source reports `regime_basis_before_fixed_area_weighting`. Soybean MIRCA support has 48,108 regime rows and 24,054 cells, with maximum absolute cell share-sum error 0.
- Every family includes the same six stage temperature/heat controls.
- Primary family: seasonal `log1p_precip_mm` quantity. Direct distribution and scPDSI are separate alternatives. Direct precipitation and scPDSI are never stacked.
- Controls were frozen as global end-year, singleton country-proxy × end-year, and 10-degree block × end-year demeaning alternatives.
- Country proxies are crop-footprint labels, not authoritative political boundaries. Ten-degree blocks are spatial support/clusters, not economic units or response strata.

## Support

The direct/heat sample has 173,871 positive levels and 167,841 consecutive pairs in 6,001 cells across all 28 pair end-years. It spans 56 ten-degree blocks. Of those pairs, 157,868 have a unique country proxy in 21 labels, 7,125 are ambiguous, and 2,848 are absent. Pair-share effective cluster counts are 27.463 ten-degree blocks and only 5.445 country proxies; the largest singleton country contains 29.284% of singleton pairs.

The scPDSI/heat alternative has 172,878 positive levels and 166,870 consecutive pairs in 5,967 cells. It has 157,003 singleton-country pairs, 7,069 ambiguous pairs, 2,798 absent pairs, 56 blocks, 27.433 effective block clusters, and 5.430 effective country clusters.

Primary quantity changes have global p05/p50/p95 of -0.59618 / 0.00366 / 0.60389 and standard deviation 0.36946. All 21 singleton country proxies and all 56 blocks have p05 below zero and p95 above zero. Their fractions within the global p05–p95 interval range from 0.6565–1.0000 for countries and 0.6165–1.0000 for blocks. This establishes variation and overlap only; it says nothing about yield-response direction.

## Residualized design results

| Family | Control alternative | Pairs | Rank / columns | Scaled condition | Max leverage | Effective leverage rows |
|---|---:|---:|---:|---:|---:|---:|
| Quantity | Global-year | 167,841 | 7 / 7 | 3.325 | 0.001198 | 89,516 |
| Quantity | Country-year | 157,868 | 7 / 7 | 2.592 | 0.001340 | 77,464 |
| Quantity | Block-year | 167,841 | 7 / 7 | 2.386 | 0.001140 | 71,251 |
| Distribution | Global-year | 167,841 | 12 / 12 | 3.519 | 0.002499 | 92,660 |
| Distribution | Country-year | 157,868 | 12 / 12 | 2.806 | 0.002280 | 85,481 |
| Distribution | Block-year | 167,841 | 12 / 12 | 2.697 | 0.002567 | 85,597 |
| Seasonal scPDSI | Global-year | 166,870 | 7 / 7 | 3.300 | 0.000575 | 91,170 |
| Seasonal scPDSI | Country-year | 157,003 | 7 / 7 | 2.568 | 0.000745 | 78,134 |
| Seasonal scPDSI | Block-year | 166,870 | 7 / 7 | 2.403 | 0.001142 | 71,596 |
| Stage scPDSI | Global-year | 166,870 | 9 / 9 | 5.847 | 0.000579 | 101,321 |
| Stage scPDSI | Country-year | 157,003 | 9 / 9 | 5.286 | 0.000752 | 88,429 |
| Stage scPDSI | Block-year | 166,870 | 9 / 9 | 4.741 | 0.001150 | 84,953 |

All 12 prespecified family/control designs are full rank. Conditions are 2.386–5.847. The pooled country-year quantity design has p99 leverage 0.000214 and the top 1% of rows carries 6.496% of total leverage. These diagnostics support a pooled design but are not evidence that any family predicts or causally affects yield.

## Geographic-resolution gate

Country qualification required at least 1,000 pairs, 20 pair end-years, 50 cells, eight occupied ten-degree blocks, two-sided quantity variation, at least 50% global-range overlap, full quantity-design rank, condition no greater than 10,000, maximum leverage no greater than 0.01, and top-1% leverage share no greater than 0.20.

Only `CHN` and `USA` pass every country-level condition. Together they cover 84,982 of 157,868 singleton-country pairs (53.831%), and China accounts for 54.400% of qualifying pairs. The family-level gate required at least 10 countries, at least 80% singleton-pair coverage, and no qualifying country above 25%; all three conditions fail. Several otherwise sizable country proxies lack eight independent ten-degree blocks: Argentina has 4, Brazil 7, South Africa 5, and India 6. Ten-degree-block response strata remain unauthorized because each such stratum would supply only one prespecified spatial block cluster for inference.

Accordingly, country-specific response heterogeneity and winner/loser claims remain unsupported. The safe next gate is external review and freezing of a pooled-only response/inference protocol, including the outcome scale and spatial clustering rule, before any slope is estimated.

## Reproducibility and validation

- Frozen config: `config/soybean_continuous_design_heterogeneity_preflight_v1.toml` (`c086163b71fb141f60d11acd6b8ddc08f02f5b4be664b93c362e59bb6223cb49`)
- Audit/provenance: `data/provenance/soybean_continuous_design_heterogeneity_preflight_20260928.json` (`d562654aeeec6e9d14be2438e335586468ad309d761449a0c8293cdbb591e8b2`)
- Independent validation: `data/provenance/soybean_continuous_design_heterogeneity_preflight_validation_20260928.json` (`0436e534e386ff61fe92b13988fa7ce02ee3b8ba286ea295c723769ca1e83581`)
- Audit maximum RSS, including short-lived design workers: 458,620,928 bytes (< 512 MiB).
- Independent validator maximum RSS: 383,877,120 bytes (< 512 MiB).
