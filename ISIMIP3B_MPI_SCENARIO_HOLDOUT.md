# MPI-ESM1-2-HR four-scenario engineering smoke

Status: **passed as bounded engineering evidence; not promoted to a production emulator, damage input, or SCC input.**

This audit extends the frozen direct ISIMIP3b daily-feature route to the third ESM with an exact historical/SSP1-2.6/SSP3-7.0/SSP5-8.5 product. The realization is `MPI-ESM1-2-HR r1i1p1f1`; all source blocks are public, unrestricted CC0 ISIMIP3b version `20210512` data.

## Complete-file and feature gates

- Six newly acquired `pr`/`tas` blocks (historical, SSP1-2.6, and SSP5-8.5) total 6,656,301,051 bytes. Every API SHA-512, daily timestamp, 360 x 720 grid, units, finite/missing-value, and physical-range gate passed.
- Both variables join the historical block to every future scenario at an exact 24-hour boundary. SSP3-7.0 retains its previously validated complete-file receipt.
- Same-realization GMST uses the MPI member itself: four historical annual values and six values in each future scenario.
- The bounded maize/rainfed feature cells contain 2,058 historical season rows plus 6,174 stage rows and 2,744 future season rows plus 8,232 stage rows per scenario. Stage days, precipitation totals, wet-day counts, and Rx1day reconcile exactly.

## Whole-scenario result

The transparent cell-mean-plus-common-GMST-slope model was evaluated on 113,190 long-format rows and 44 leave-one-scenario-out feature folds. It improved on the cell-mean benchmark in 19/44 folds. The median RMSE ratio was 1.000832 and the worst ratio was 1.198952; therefore this specification is not promoted. By held-out scenario, improvement counts were 2/11 historical, 7/11 SSP1-2.6, 3/11 SSP3-7.0, and 7/11 SSP5-8.5.

The result establishes a whole-scenario engineering gate for a third ESM. It does not establish complete historical/future temporal coverage, the frozen five-ESM product, common-random-number baseline/pulse paths, support flags, zero-pulse or pre-divergence identity, decreasing-pulse convergence, a yield response, damages, welfare, or an SCC.

Machine-readable records:

- `data/provenance/isimip3b_mpi_scenario_matrix.toml`
- `data/provenance/isimip3b_mpi_scenario_holdout_smoke_20260827.json`
- `config/isimip3b_mpi_scenario_holdout_smoke_v1.toml`
