# AI-assisted GIVE damage expansion synthesis

This isolated project synthesizes the completed sector audits and implementations without modifying them. It asks two distinct questions:

1. What credible quantitative information has been produced for damage sectors missing or incomplete in GIVE?
2. Which results can be combined without changing their scientific meaning or double counting damages?

The current answer to the second question is intentionally conservative: **no cross-sector headline total is authorized yet**. Two rows are integrated or pair-tested, but their agriculture target contracts are incompatible. The remaining numerical results are external sensitivities, bounded regional benchmarks, or explicitly nonadditive.

The current ledger contains 29 component rows tied to 51 exact evidence files. Recent additions retain their source claim boundaries: winter recreation is a CONUS lost-revenue benchmark rather than social welfare; heat morbidity, education heat, freshwater angling, permafrost feedback, Amazon dieback feedback, and wetland methane feedback remain blocked with no marginal SCC; and grid T&D is a CONUS direct repair/replacement-cost benchmark that excludes outage welfare and remains nonadditive because its released response bundles several climate stressors. The permafrost entry records unresolved FaIR and baseline-emissions boundaries, an incompatible biogenic-CH4 port, missing recursive baseline/pulse validation, the 765-versus-775 PerCX artifact discrepancy, and an unused decay argument. The Amazon entry records unresolved FaIR land-sink and baseline land-use boundaries, an incomplete GMST-only hazard, unvalidated historical conditioning and common-random recursion, and a released stock-overshoot rule alongside a tested stock-conserving correction. Wetland methane records GIVE's constant 168.83862060475192 MtCH4/yr natural baseline and the Sloughter/MAGICC 30 +/- 13 MtCH4/yr/K candidate slope, while leaving baseline partition, anomaly anchoring, biogenic oxidation, timing, proxy/reversibility, negative-tail, recursive-pulse, and version gates closed. Forestry is retained only as a reproduced legacy external benchmark: -$0.076953/tCO2 in 2020 USD at fixed 2%, where the negative sign is a market benefit. Its -$0.154557 to -$0.037065 one-at-a-time range is a parameter diagnostic, not uncertainty, and documentation/code conflict, legacy calibration, FUND/GIVE mismatch, and disturbance overlap prohibit addition. Swiss building hail appears only as an original-unit scenario benchmark: CHF74 million annual average loss for 2011-2021 weather and CHF90 million at +3C, the published rounded +22% change, under fixed exposure and with no currency price year. Adaptation accounting now makes fixed/current-practice agriculture primary; trend and upper are gross free-attenuation sensitivities, not net damages or SCCs. FrEDI road, rail, and grid totals and CIAM OptimalCost already include specified adaptation expenditures, while inland flooding assumes no additional adaptation. The OECD agriculture scale of USD15.7-20.2 billion/year in 2005 dollars remains an unallocated original-unit benchmark. The non-SCC scenario table retains these values and the four CIRA II freshwater-angling NPVs without promoting any to SCC. Bilal and Känzig's $1,206.969/tCO2 estimate appears only as a mutually exclusive top-down comparator in its original 2024 international-dollar unit. It is not added, converted, or treated as the residual of sectors absent from GIVE.

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
