# Country decomposition of the narrow quantity-channel SCC

## Result

The equal-26-model, fixed-adaptation, uncapped annual-maize rainfall-quantity
benchmark at GIVE's 2% schedule is -$0.00610173 per tCO2 (2020 USD). Country
accounting components sum exactly to that value within `4.7e-17` USD/tCO2.
The decomposition covers 106 countries; 61 have negative equal-model mean
components (benefits in the damage-positive convention) and 45 have positive
components (damages).

Gross negative components sum to -$0.00695645/tCO2 and gross positive
components sum to +$0.00085472/tCO2. The global sign therefore reflects
substantial but incomplete geographic offsetting, not a uniform benefit.

| Direction | Country | Equal-model mean (2020 USD/tCO2) | Model range |
|---|---|---:|---:|
| Negative | United States | -0.00352580 | -0.00585777 to +0.00192693 |
| Negative | China | -0.00232612 | -0.00370726 to +0.00274846 |
| Negative | Argentina | -0.00014279 | -0.00056956 to +0.00025728 |
| Negative | Kenya | -0.00013461 | -0.00031699 to +0.00007143 |
| Negative | Ethiopia | -0.00013261 | -0.00032591 to +0.00018484 |
| Positive | Mexico | +0.00031341 | -0.00051407 to +0.00072550 |
| Positive | Brazil | +0.00029132 | -0.00113729 to +0.00154911 |
| Positive | South Africa | +0.00009522 | -0.00081119 to +0.00087815 |

The United States and China together supply 84.1% of the gross negative
component and 95.9% of the net global value. Mexico and Brazil supply 70.8% of
the gross positive component. Each of those four country components changes
sign across at least one of the 26 climate models. Consequently, the country
ranking should be interpreted as an equal-model accounting summary rather
than a stable local impact ordering.

## Validation and claim boundary

The script independently reconstructs every climate model's central paired
diagnostic from country components. The maximum model reconstruction error is
`9.4e-17` USD/tCO2. Missing country-model precipitation slopes are represented
as zero contributions in the equal-model estimand, rather than silently
changing the model denominator; 96 countries have all 26 slopes and 10 have
22--24.

These are country accounting components of a narrow transported response,
not country causal effects or country total precipitation damages. They hold
the published maize response, central market, fixed adaptation, uncapped tail,
and discount schedule fixed. Temperature, drought, timing shifts, additional
crops, trade, storage, and adaptation costs remain outside this result.

## Reproduction

- Implementation: `scripts/decompose_quantity_scc_by_country.py`
- Machine-readable receipt:
  `data/provenance/quantity_scc_country_decomposition_20260925.json`
- Audited figure: `manuscript/figures/quantity_scc_country_decomposition_20260925.svg`
- Figure receipt:
  `data/provenance/quantity_scc_country_decomposition_figure_20260925.json`
- Memory-bounded job receipt:
  `data/provenance/quantity_scc_country_decomposition_job_20260925.json`
- Derived country table (gitignored):
  `data/interim/quantity_scc_country_decomposition_20260925.csv`

The validated rerun completed in 3.4 seconds with sampled peak process-group
RSS of 178,094,080 bytes (169.8 MiB) under a 768 MiB budget.
