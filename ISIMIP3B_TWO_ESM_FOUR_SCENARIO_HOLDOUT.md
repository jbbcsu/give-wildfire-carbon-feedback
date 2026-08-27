# Two-ESM × four-scenario holdout smoke

Status: bounded joint whole-ESM and whole-scenario engineering evidence for
the approved direct ISIMIP3b route; not a production emulator, damage
function, or SCC input.

The exact hash-bound GFDL-ESM4 and IPSL-CM6A-LR historical, SSP1-2.6,
SSP3-7.0, and SSP5-8.5 bounded training products were combined without
refitting or selecting their input cells. The joint product contains 226,380
long rows across eleven rainfall/timing/temperature feature families, one
maize rainfed calendar, two latitude rows, and seven nonoverlapping harvest
years per realization.

For the first time in this work, the same product is evaluated with both
whole-ESM and whole-scenario exclusions. The transparent training-cell mean
plus common within-cell GMST slope beats the cell-mean benchmark in 11/22
whole-ESM feature folds. Its overall whole-ESM median RMSE ratio is 1.00001
and its maximum is 1.02738; improvement counts are 4/11 when GFDL is held out
and 7/11 when IPSL is held out. In the 44 whole-scenario feature folds, it
improves 29/44, with median RMSE ratio 0.99895 and maximum 1.02682. Scenario
improvement counts are 4/11 historical, 8/11 SSP1-2.6, 8/11 SSP3-7.0, and
9/11 SSP5-8.5.

The joint gates pass, but performance remains essentially tied to the simple
cell-mean benchmark and some folds worsen. The specification is not promoted.
Only two of the five frozen ESMs have the exact four-scenario matrix, and the
spatial, crop, and temporal slices remain deliberately bounded. Complete
five-ESM coverage, common-random-number baseline/pulse paths, scenario-specific
support flags, zero-pulse and pre-divergence identity, decreasing-pulse
convergence, crop response estimation, damages, and SCC remain open.

Reproduce with:

```bash
./.venv/bin/python scripts/test_isimip3b_two_esm_four_scenario_holdout.py

./.venv/bin/python scripts/evaluate_isimip3b_two_esm_four_scenario_holdout.py \
  --config config/isimip3b_two_esm_four_scenario_holdout_smoke_v1.toml \
  --training-out data/interim/isimip3b_two_esm_four_scenario_holdout/training.parquet \
  --esm-holdouts-out data/interim/isimip3b_two_esm_four_scenario_holdout/esm_holdouts.csv \
  --scenario-holdouts-out data/interim/isimip3b_two_esm_four_scenario_holdout/scenario_holdouts.csv \
  --audit-out data/provenance/isimip3b_two_esm_four_scenario_holdout_20260827.json
```
