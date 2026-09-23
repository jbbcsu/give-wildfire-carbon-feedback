# FAO FishStat GUI export reconciliation

The supported FishStatJ 4.04.11 route—**File > Export selection (CSV
file)**—has now independently exported the complete Global Capture Production
1950--2024 selection from the pinned FAO workspace. The ignored raw GUI file
is 14,985,286 bytes with SHA-256
`25fba53dd5507443691fc7147796bb9b770c9a2ceb5acf5ef0dc2e25425773cd`.

A disk-backed, bounded-memory validator reconciles all 30,918 country × species
× FAO-area × measure records and all 2,318,850 annual value/status pairs to the
previously validated headless extract. It also reconciles the two GUI total
rows. FishStatJ displays at most two decimals, while the headless export retains
source precision; every displayed value and total is within 0.005 of the
source-precision value. The maximum observed difference is exactly 0.005.

The status mapping is complete: 980,486 `A` cells display blank; 1,266,653 `O`
cells display `...`; and `E`, `I`, `N`, `P`, `Q`, and `X` display their literal
symbols. The 493 records without a common species name are independently
matched to FishStatJ's bracketed scientific-name fallback rather than assigned
an invented name. The validator peaks at 31,473,664 bytes RSS.

This closes the GUI-versus-headless record-integrity gate only. It does not yet
authorize a production marine-tonnage filter, assign vessel-flag landings to
EEZs, identify fishing effort or management, validate FishMIP, estimate
welfare, construct damages, or compute an SCC increment.

Machine-readable evidence:

- `data/provenance/fao_fishstat_gui_headless_reconciliation_20260923.json`
- `scripts/reconcile_fao_fishstat_gui_export.py`

