# Final-resolution U.S. drought--yield agricultural-area results

**Status:** completed historical U.S. sensitivity at 990 m with independent numerical and resource validation. This is not a causal yield response, future drought projection, global damage function, or SCC input.

## Purpose

This analysis replaces the rejected 3.96 km agricultural-area approximation with the predeclared national 990 m reconstruction, while holding the crop outcomes, irrigation classifier, fixed effects, direct-weather hierarchy, and inference procedures unchanged.

## Construction and resource validation

The state-partitioned build covers 48 continental states, 2,909 counties, two fixed CDL masks, and 13 harvest years. The merged exposure has 75,634 county-mask-year rows. Maximum state grid and exposure RSS were 582.6 MiB and 638.7 MiB, respectively, below the frozen 640 MiB ceiling. Annual mutually exclusive drought categories reconcile within 4.57e-12 week.

## Exposure accounting

| Basis | County-years | Counties | D0 | D1 | D2 | D3 | D4 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Published Table 2 | 40,040 | -- | 8.470 | 5.660 | 3.870 | 2.260 | 0.800 |
| Whole county | 39,299 | 3,023 | 8.603 | 5.739 | 3.906 | 2.287 | 0.821 |
| Cultivated 990 m | 37,817 | 2,909 | 8.513 | 5.702 | 3.899 | 2.295 | 0.827 |
| Broad agriculture 990 m | 37,817 | 2,909 | 8.513 | 5.705 | 3.887 | 2.298 | 0.827 |

Full-support mean differences combine spatial weighting and coverage. The summary separately reports exact common county-year support; neither mask is selected by proximity to the published means.

## Historical drought-only associations

Entries are exact fitted percent changes in yield for one additional area-equivalent week, conditional on the other mutually exclusive drought categories, county and year fixed effects, and state-specific trends.

| Crop | Support | Basis | D0 | D1 | D2 | D3 | D4 |
|---|---|---|---:|---:|---:|---:|---:|
| Corn | Dryland | Whole county | -0.1365 | -0.3093 | -0.6136 | -1.0719 | -1.1413 |
| Corn | Irrigated | Whole county | -0.0858 | -0.0414 | -0.1233 | -0.1233 | -0.4881 |
| Soybean | Dryland | Whole county | -0.1747 | -0.5888 | -0.5750 | -0.8394 | -0.6190 |
| Soybean | Irrigated | Whole county | -0.0025 | -0.2108 | -0.2899 | -0.3987 | -0.0699 |
| Corn | Dryland | Cultivated 990 m | -0.1398 | -0.3055 | -0.6097 | -1.0856 | -1.1462 |
| Corn | Irrigated | Cultivated 990 m | -0.0903 | -0.0404 | -0.1339 | -0.1169 | -0.4721 |
| Soybean | Dryland | Cultivated 990 m | -0.1786 | -0.5860 | -0.5763 | -0.8454 | -0.6246 |
| Soybean | Irrigated | Cultivated 990 m | -0.0099 | -0.2133 | -0.2818 | -0.4051 | -0.0637 |
| Corn | Dryland | Broad agriculture 990 m | -0.1366 | -0.3119 | -0.6089 | -1.0796 | -1.1469 |
| Corn | Irrigated | Broad agriculture 990 m | -0.0909 | -0.0363 | -0.1352 | -0.1179 | -0.4750 |
| Soybean | Dryland | Broad agriculture 990 m | -0.1764 | -0.5886 | -0.5785 | -0.8405 | -0.6188 |
| Soybean | Irrigated | Broad agriculture 990 m | -0.0071 | -0.2111 | -0.2878 | -0.3980 | -0.0724 |

## Direct-weather hierarchy

These estimates additionally control for April--September rainfall, rainfall squared, mean temperature, and crop-threshold heat exposure. Composite drought and direct weather are treated as competing descriptions rather than additive damage channels.

| Crop | Support | Basis | D0 | D1 | D2 | D3 | D4 |
|---|---|---|---:|---:|---:|---:|---:|
| Corn | Dryland | Whole county | +0.0439 | -0.0106 | -0.2606 | -0.4135 | -0.1723 |
| Corn | Irrigated | Whole county | +0.0492 | +0.0583 | +0.0352 | -0.0175 | -0.1028 |
| Soybean | Dryland | Whole county | +0.0256 | -0.2274 | -0.1679 | -0.0942 | +0.3201 |
| Soybean | Irrigated | Whole county | +0.1746 | -0.0394 | -0.1258 | -0.1836 | +0.3720 |
| Corn | Dryland | Cultivated 990 m | +0.0434 | -0.0086 | -0.2550 | -0.4188 | -0.1816 |
| Corn | Irrigated | Cultivated 990 m | +0.0463 | +0.0572 | +0.0290 | -0.0131 | -0.0921 |
| Soybean | Dryland | Cultivated 990 m | +0.0262 | -0.2281 | -0.1622 | -0.1054 | +0.3272 |
| Soybean | Irrigated | Cultivated 990 m | +0.1686 | -0.0423 | -0.1181 | -0.1867 | +0.3718 |
| Corn | Dryland | Broad agriculture 990 m | +0.0455 | -0.0143 | -0.2539 | -0.4161 | -0.1792 |
| Corn | Irrigated | Broad agriculture 990 m | +0.0462 | +0.0620 | +0.0282 | -0.0160 | -0.0905 |
| Soybean | Dryland | Broad agriculture 990 m | +0.0266 | -0.2287 | -0.1669 | -0.0973 | +0.3274 |
| Soybean | Irrigated | Broad agriculture 990 m | +0.1706 | -0.0403 | -0.1216 | -0.1848 | +0.3685 |

## Spatial-basis movement within the final comparison

| Model | Comparison | Mean absolute movement | Maximum movement | Maximum term |
|---|---|---:|---:|---|
| drought only | county vs broad | 0.00391 | 0.01309 | corn_grain/irrigated/d4_weeks |
| drought only | county vs cultivated | 0.00592 | 0.01596 | corn_grain/irrigated/d4_weeks |
| drought only | cultivated vs broad | 0.00356 | 0.00864 | soybeans/irrigated/d4_weeks |
| drought plus weather | county vs broad | 0.00383 | 0.01238 | corn_grain/irrigated/d4_weeks |
| drought plus weather | county vs cultivated | 0.00466 | 0.01114 | soybeans/dryland/d3_weeks |
| drought plus weather | cultivated vs broad | 0.00254 | 0.00806 | soybeans/dryland/d3_weeks |

## Change from the rejected 3.96 km diagnostic

The following movements compare the final-resolution coefficients with the previously rejected coarse diagnostic. They are fidelity diagnostics, not model-selection criteria.

| Model | Comparison | Mean absolute movement | Maximum movement | Maximum term |
|---|---|---:|---:|---|
| drought only | broad | 0.00070 | 0.00230 | soybeans/dryland/d1_weeks |
| drought only | cultivated | 0.00079 | 0.00223 | soybeans/dryland/d2_weeks |
| drought plus weather | broad | 0.00050 | 0.00127 | soybeans/irrigated/d4_weeks |
| drought plus weather | cultivated | 0.00048 | 0.00130 | soybeans/irrigated/d4_weeks |

## State-cluster and leave-one-state-out screen

The table reports every weather-controlled term that is either below 0.05 under state-cluster inference or retains the same nonzero sign in every represented-state deletion. This is a stability screen, not a multiple-testing-adjusted discovery rule.

| Basis | Crop | Support | Category | Estimate | State-cluster p | Leave-one-state-out same-sign share |
|---|---|---|---|---:|---:|---:|
| Cultivated 990 m | Corn | Dryland | D0 | +0.0434 | 0.5539 | 1.000 |
| Cultivated 990 m | Corn | Dryland | D2 | -0.2550 | 0.0131 | 1.000 |
| Cultivated 990 m | Corn | Dryland | D3 | -0.4188 | 0.0082 | 1.000 |
| Cultivated 990 m | Corn | Dryland | D4 | -0.1816 | 0.2085 | 1.000 |
| Cultivated 990 m | Corn | Irrigated | D0 | +0.0463 | 0.4295 | 1.000 |
| Cultivated 990 m | Corn | Irrigated | D4 | -0.0921 | 0.1404 | 1.000 |
| Cultivated 990 m | Soybean | Dryland | D1 | -0.2281 | 0.0046 | 1.000 |
| Cultivated 990 m | Soybean | Dryland | D2 | -0.1622 | 0.0371 | 1.000 |
| Cultivated 990 m | Soybean | Dryland | D3 | -0.1054 | 0.4058 | 1.000 |
| Cultivated 990 m | Soybean | Irrigated | D0 | +0.1686 | 0.1965 | 1.000 |
| Cultivated 990 m | Soybean | Irrigated | D1 | -0.0423 | 0.5185 | 1.000 |
| Cultivated 990 m | Soybean | Irrigated | D2 | -0.1181 | 0.0327 | 1.000 |
| Cultivated 990 m | Soybean | Irrigated | D3 | -0.1867 | 0.0060 | 1.000 |
| Cultivated 990 m | Soybean | Irrigated | D4 | +0.3718 | 0.0044 | 1.000 |
| Broad agriculture 990 m | Corn | Dryland | D0 | +0.0455 | 0.5340 | 1.000 |
| Broad agriculture 990 m | Corn | Dryland | D2 | -0.2539 | 0.0141 | 1.000 |
| Broad agriculture 990 m | Corn | Dryland | D3 | -0.4161 | 0.0092 | 1.000 |
| Broad agriculture 990 m | Corn | Dryland | D4 | -0.1792 | 0.2163 | 1.000 |
| Broad agriculture 990 m | Corn | Irrigated | D0 | +0.0462 | 0.4433 | 1.000 |
| Broad agriculture 990 m | Corn | Irrigated | D4 | -0.0905 | 0.1507 | 1.000 |
| Broad agriculture 990 m | Soybean | Dryland | D1 | -0.2287 | 0.0046 | 1.000 |
| Broad agriculture 990 m | Soybean | Dryland | D2 | -0.1669 | 0.0374 | 1.000 |
| Broad agriculture 990 m | Soybean | Dryland | D3 | -0.0973 | 0.4404 | 1.000 |
| Broad agriculture 990 m | Soybean | Irrigated | D0 | +0.1706 | 0.1953 | 1.000 |
| Broad agriculture 990 m | Soybean | Irrigated | D1 | -0.0403 | 0.5386 | 1.000 |
| Broad agriculture 990 m | Soybean | Irrigated | D2 | -0.1216 | 0.0348 | 1.000 |
| Broad agriculture 990 m | Soybean | Irrigated | D3 | -0.1848 | 0.0075 | 1.000 |
| Broad agriculture 990 m | Soybean | Irrigated | D4 | +0.3685 | 0.0049 | 1.000 |

## Interpretation boundary

The final 990 m reconstruction establishes the spatial fidelity of the historical U.S. drought benchmark and quantifies how much the coarse approximation moved its associations. It does not identify a causal USDM response, project future drought, establish transferability outside the United States, monetize damages, or authorize any SCC calculation. Those gates remain false in both the summary and independent validation receipts.

Machine-readable sources:

- `data/provenance/usdm_agricultural_area_990m_spatial_basis_comparison_20260923.json`
- `data/provenance/usdm_national_990m_merged_validation_20260923.json`
- `data/provenance/usdm_agricultural_area_990m_summary_independent_validation_20260923.json`
