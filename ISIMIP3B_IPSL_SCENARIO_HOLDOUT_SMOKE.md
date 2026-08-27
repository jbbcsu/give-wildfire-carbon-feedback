# ISIMIP3b IPSL whole-scenario holdout smoke

Status: bounded engineering evidence for the approved direct daily-feature
route; not a production emulator, damage function, or SCC input.

The frozen IPSL-CM6A-LR r1i1p1f1 historical, SSP1-2.6, SSP3-7.0, and SSP5-8.5
daily precipitation and mean-temperature cells now have exact version, file
identifier, byte, SHA-512, license, decoded-content, historical-boundary, and
same-realization GMST receipts. The newly acquired six files total
6,698,319,987 bytes; the pre-existing SSP3-7.0 pair remains separately pinned.
All files are public, unrestricted CC0 version 20210512 data from the frozen
outcome-blind selection.

Using the committed `43e37c8` feature code from an isolated archive, the
historical cell contains 2,058 maize/rainfed crop-years and 6,174 stage rows;
each new future scenario contains 2,744 crop-years and 8,232 stage rows. All
four cells pass finite/nonnegative rainfall and extreme bounds, and stage days,
rain totals, wet-day counts, and Rx1day reconcile exactly to the seasonal rows.

The exact historical-plus-three-SSP training design contains 113,190 long
feature rows and 44 whole-scenario-by-feature holdouts. The transparent
training-cell mean plus common within-cell GMST slope improves on the cell-mean
benchmark in 26/44 folds. The overall median RMSE ratio is 0.9996 and the
maximum is 1.0638. Improvement counts are 4/11 for historical, 9/11 for
SSP1-2.6, 8/11 for SSP3-7.0, and 5/11 for SSP5-8.5. This is stronger than the
same bounded GFDL smoke on the improvement count, but both have median ratios
near one and some worsened folds. The simple model is therefore not promoted.

This closes a second ESM's bounded whole-scenario engineering smoke. Complete
five-ESM × four-scenario temporal coverage, joint whole-ESM plus whole-scenario
validation, common-random-number baseline/pulse paths, scenario-specific
support flags, zero-pulse and pre-divergence identity, decreasing-pulse
convergence, crop responses, damages, and SCC remain open. MESMER-M-TP plus a
daily generator remains fallback only.

Reproduce the generic audit with:

```bash
./.venv/bin/python scripts/test_isimip3b_scenario_holdout_smoke.py

./.venv/bin/python scripts/evaluate_isimip3b_scenario_holdout_smoke.py \
  --config config/isimip3b_ipsl_scenario_holdout_smoke_v1.toml \
  --training-out data/interim/isimip3b_ipsl_scenario_holdout/training_long.parquet \
  --holdouts-out data/interim/isimip3b_ipsl_scenario_holdout/holdouts.csv \
  --audit-out data/provenance/isimip3b_ipsl_scenario_holdout_smoke_20260827.json
```
