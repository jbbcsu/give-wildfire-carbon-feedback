# AI-assisted GIVE damage expansion synthesis

This isolated project synthesizes the completed sector audits and implementations without modifying them. It asks two distinct questions:

1. What credible quantitative information has been produced for damage sectors missing or incomplete in GIVE?
2. Which results can be combined without changing their scientific meaning or double counting damages?

The current answer to the second question is intentionally conservative: **no cross-sector headline total is authorized yet**. Two rows are integrated or pair-tested, but their agriculture target contracts are incompatible. The remaining numerical results are external sensitivities, bounded regional benchmarks, or explicitly nonadditive.

The current ledger contains 24 component rows tied to 32 exact evidence files. Recent additions retain their source claim boundaries: winter recreation is a CONUS lost-revenue benchmark rather than social welfare; heat morbidity, education heat, freshwater angling, and permafrost feedback remain blocked with no marginal SCC; and grid T&D is a CONUS direct repair/replacement-cost benchmark that excludes outage welfare and remains nonadditive because its released response bundles several climate stressors. The permafrost entry records unresolved FaIR and baseline-emissions boundaries, an incompatible biogenic-CH4 port, missing recursive baseline/pulse validation, the 765-versus-775 PerCX artifact discrepancy, and an unused decay argument. It explicitly prohibits applying the combined EPA permafrost-plus-Amazon 9–50% result as a permafrost or GIVE scalar uplift. The four CIRA II freshwater-angling consumer-surplus NPVs are retained in a separate table in their original million-2015-USD scenario units and explicitly overlap FrEDI freshwater recreation. Bilal and Känzig's $1,206.969/tCO2 estimate appears only as a mutually exclusive top-down comparator in its original 2024 international-dollar unit. It is not added, converted, or treated as the residual of sectors absent from GIVE.

## Four evidence tiers

- `integrated_pair_tested`: executed against matched baseline/pulse paths or a same-run GIVE target. This label does not by itself authorize stacking with another target.
- `external_sensitivity`: a reproduced or source-pinned result under another model's settings.
- `bounded_regional_benchmark`: a matched-pulse partial SCC whose geography or support is narrower than global GIVE.
- `blocked_nonadditive`: a readiness result, source scalar, or endpoint with an open overlap or implementation gate.
- `mutually_exclusive_comparator`: a broad top-down result shown only beside the bottom-up program, never inside a sector sum or residual calculation.

The master ledger is [data/derived/master_damage_sector_ledger_v1.csv](data/derived/master_damage_sector_ledger_v1.csv). Every row is tied to exact machine-readable evidence by SHA-256. Restricted raw data and confidential PDFs are not copied here.

## Reproduce

From this directory, with the sibling sector projects present:

```bash
python3 scripts/build_master_ledger.py
python3 scripts/validate_master_ledger.py
python3 -m unittest discover -s tests -v
```

## Paper materials

- [Main manuscript structure](docs/MAIN_MANUSCRIPT_STRUCTURE.md)
- [Overlap interpretation](docs/OVERLAP_MATRIX.md)
- [Next-step priorities](docs/NEXT_STEP_PRIORITIES.md)
- [Machine-readable overlap matrix](data/derived/overlap_matrix_v1.csv)
- [Machine-readable priority table](data/derived/next_step_priorities_v1.csv)

This project is a synthesis layer only. It does not import raw inputs, mutate sector repositories, or manufacture missing numerical estimates.
