# Time decomposition of the narrow quantity-channel SCC

## Result

The equal-26-model, central fixed-adaptation, uncapped annual-maize rainfall-
quantity result at GIVE's 2% schedule is -$0.00610173 per tCO2 (2020 USD).
Its discounted accounting contributions are:

| Years | Contribution (2020 USD/tCO2) | Share of signed total |
|---|---:|---:|
| 2020--2050 | -0.00268896 | 44.1% |
| 2051--2100 | -0.00166820 | 27.3% |
| 2101--2200 | -0.00132040 | 21.6% |
| 2201--2300 | -0.00042416 | 7.0% |

Thus 71.4% of the signed total accrues by 2100. The mean undiscounted annual
SCC-equivalent contribution is similar across the four periods (about
-$0.000135 to -$0.000139 per tCO2-year). The small total is therefore not a
late-century artifact: the narrow modeled channel is small per year, and
discounting progressively reduces its distant contributions.

The timing shares vary transparently with the registered discount schedule:

| GIVE schedule | Total (2020 USD/tCO2) | Share through 2100 | Share in 2201--2300 |
|---|---:|---:|---:|
| 1.5% | -0.00882969 | 60.2% | 12.4% |
| 2.0% | -0.00610173 | 71.4% | 7.0% |
| 2.5% | -0.00454292 | 80.6% | 3.5% |
| 3.0% | -0.00359037 | 87.2% | 1.7% |

These are four policy schedules, not probability draws. Higher discount rates
mechanically shift the signed present-value share toward earlier years; they
do not change the physical annual response path.

## Validation and interpretation

The 7,306 model-year contributions reconstruct every climate model's central
SCC, with a maximum error of `9.3e-17` USD/tCO2. This is a temporal accounting
decomposition of the same estimate, not a causal estimate of precipitation
timing within a crop season. It does not expand the quantity-only claim to
drought, rainfall distribution, temperature, other crops, or total
agricultural damages.

The memory-bounded run completed in 1.8 seconds at 178,323,456 bytes (170.1
MiB) sampled peak process-group RSS under a 768 MiB budget.

## Reproduction

- Implementation: `scripts/decompose_quantity_scc_by_period.py`
- Machine-readable receipt:
  `data/provenance/quantity_scc_period_decomposition_20260925.json`
- Four-schedule reweighting receipt:
  `data/provenance/quantity_scc_period_discount_grid_20260925.json`
- Audited figure:
  `manuscript/figures/quantity_scc_period_discount_grid_20260925.svg`
- Figure receipt:
  `data/provenance/quantity_scc_period_discount_figure_20260925.json`
- Memory-bounded job receipt:
  `data/provenance/quantity_scc_period_decomposition_job_20260925.json`
- Derived model-year table (gitignored):
  `data/interim/quantity_scc_period_decomposition_20260925.csv`
