# Country heterogeneity under registered adaptation scenarios

## Result

The five-ESM late-century maize precipitation diagnostic now preserves country
heterogeneity under the registered fixed, trend, and upper adaptation rules.
These are exogenous loss-only attenuation scenarios, not estimates of farmer
behavior, costs, welfare, or SCC.

| Scenario | Global mean log-yield contribution | Gross losses | Gross gains | Countries with mean losses | Countries with mean gains |
|---|---:|---:|---:|---:|---:|
| Fixed | -0.01956 | -0.02167 | +0.00211 | 111 | 33 |
| Trend | -0.00718 | -0.01204 | +0.00486 | 89 | 55 |
| Upper | +0.00933 | -0.00243 | +0.01176 | 59 | 85 |

Fifty-two of 144 countries change from a negative equal-model mean under fixed
adaptation to a positive mean under upper adaptation; none changes in the
opposite direction. Under fixed adaptation, 65 countries are negative in all
five climate models and only three are positive in all five. Under the upper
case those counts become 28 and 41, respectively.

The upper-case sign reversal is mechanical. The registered rule attenuates
negative cell log-yield responses by up to 70% but leaves nonnegative responses
unchanged. It therefore increases every country contribution weakly and can
turn a net loss into a net gain without representing adaptation costs or
general-equilibrium behavior. The fixed case remains the central benchmark;
trend and upper are structural sensitivities.

## Validation and boundaries

The calculation reads the previously validated production-weighted cell-year
components, applies the exact year-specific registered factors, and reconstructs
all 15 source ESM-by-adaptation pooled means within `2e-12`. A separate
validator reconstructs all country summaries and sign flips from the compact
2,160-row country/model/scenario table; its maximum summary discrepancy is
`1.10e-15`. Adaptation monotonicity passes for all 144 countries.

The endpoint contrast is SSP5-8.5 minus SSP1-2.6 during 2092--2100. It contains
multiple forcings and internal variability, uses physical maize-production
weights, and is not a marginal carbon pulse. No result is a causal country
effect, monetary damage, or SCC.

## Reproduction

- Builder: `scripts/summarize_hultgren_adaptation_country_heterogeneity.py`
- Validator: `scripts/validate_hultgren_adaptation_country_heterogeneity.py`
- Result receipt:
  `data/provenance/hultgren_adaptation_country_heterogeneity_production_20260926.json`
- Validation receipt:
  `data/provenance/hultgren_adaptation_country_heterogeneity_validation_20260926.json`
- Compact ignored table:
  `data/interim/hultgren_adaptation_country_heterogeneity_production_20260926.csv`
