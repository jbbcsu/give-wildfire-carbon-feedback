# Standard-GIVE-baseline partial-SCC diagnostic

## Result

The validated annual maize precipitation-quantity marginal damage paths have
been discounted with GIVE's own deterministic baseline consumption path and
normalized to dollars per tonne of CO2. The consumption path was exported by
running the pinned GIVE environment with its default deterministic RFF
socioeconomic sample 6546. The diagnostic covers 2020--2300, all 26 EPA
climate models, three positive pulse sizes, three adaptation scenarios, two
tail rules, three elasticity pairs, two supply mappings, and GIVE's four
Ramsey schedules, yielding 11,232 path-level values.

For the smallest pulse, fixed adaptation, uncapped response, and central
0.10/0.04 horizontal-output market, the 26-model mean diagnostics in 2020 USD
per tCO2 are:

| Ramsey schedule | Mean | Median | Model range |
|---|---:|---:|---:|
| 1.5% | -0.00883 | -0.00918 | -0.01483 to 0.00458 |
| 2.0% | -0.00610 | -0.00634 | -0.01025 to 0.00317 |
| 2.5% | -0.00454 | -0.00472 | -0.00763 to 0.00236 |
| 3.0% | -0.00359 | -0.00373 | -0.00603 to 0.00186 |

Negative values denote a modeled marginal benefit. At every discount schedule,
25 of 26 climate models are negative under this central specification. The
quantity-only diagnostic is therefore small and negative on average; it is not
evidence about total precipitation damages or total agricultural climate
damages.

## Exact calculation

For each year, the billion-2005-USD marginal damage difference is multiplied
by `12/44 / pulse_GtC`, which converts it to 2005 USD per tonne CO2. GIVE's
Ramsey factor is

`(CPC_2020 / CPC_t)^eta / (1 + prtp)^(t - 2020)`.

Discounted annual values are summed through 2300 and then multiplied by GIVE's
pinned `113.648/87.504` conversion to 2020 USD. The exported consumption path
exactly uses GIVE's standard baseline model and includes its existing MooreAg
component.

## Validation

The Julia export contains all 281 annual observations. Its net-consumption and
per-capita-consumption identities agree to floating-point precision. The two
smallest pulse diagnostics have maximum relative disagreement `6.89e-6`, well
below the `2e-4` gate inherited from the climate response. An independent
validator streamed all 1,052,064 annual source rows and reconstructed every
one of the 11,232 diagnostics with `math.fsum`; maximum disagreement is
`1.22e-16` USD per tCO2.

The GIVE run peaked at 1.22 GB sampled process-group RSS under a 1.5 GiB cap.
The diagnostic builder and independent validator peaked at 167 MB and 312 MB,
respectively.

## Why this is not yet the replacement SCC

The discount factors come from standard GIVE, which retains MooreAg. This is a
transparent standard-baseline discount diagnostic of the new marginal path,
not a paired replacement run. A final replacement requires defensible baseline
and pulse agriculture damage levels, removal of MooreAg exactly once, and
paired uncertainty draws. The current result also excludes rainfall timing,
dry spells, extremes, drought, temperature, other crops, trade, storage,
future crop-value growth, and adaptation costs.

## Reproducible artifacts

- GIVE consumption exporter:
  `scripts/export_give_deterministic_discount_path.jl`
- Diagnostic builder:
  `scripts/build_epa_fair_hultgren_quantity_partial_scc_diagnostic.py`
- Independent validator:
  `scripts/validate_epa_fair_hultgren_quantity_partial_scc_diagnostic.py`
- Provenance receipts:
  `data/provenance/give_deterministic_discount_path_job_20260924.json`,
  `data/provenance/epa_fair_hultgren_quantity_partial_scc_diagnostic_20260924.json`,
  and
  `data/provenance/epa_fair_hultgren_quantity_partial_scc_diagnostic_validation_20260924.json`
- Ignored derived data:
  `data/interim/give_deterministic_discount_path_20260924.csv` and
  `data/interim/epa_fair_hultgren_quantity_partial_scc_diagnostic_20260924.csv`
