# Bounded five-ESM ISIMIP3b holdout smoke

Status: passed engineering smoke for one SSP3-7.0 maize/rainfed slice; not the
complete feature emulator, a paired pulse path, agricultural damages, or an
SCC input.

The smoke assembles the already content-validated 2016--2019 maize/rainfed
feature cells for the five frozen ISIMIP3b ESM/member realizations. It retains
same-realization annual GMST and evaluates 11 feature families: mean
temperature, seasonal rainfall, wet days, maximum dry spell, Rx1day, Rx5day,
three stage rainfall shares, the precipitation timing centroid, and rainfall
concentration.

Each whole-ESM fold fits only the other four ESMs. The deliberately simple
model starts from each grid cell's training-ESM mean and adds one common
within-cell slope on same-realization GMST. Its registered engineering
benchmark is the training-cell mean without GMST. This transparent smoke tests
assembly, exact holdout exclusion, spatial support, and score generation; it
is not a proposed production model.

The real table has 150,920 long feature rows and the exact 55 ESM-by-feature
holdout scores. The GMST adjustment has lower RMSE than the cell-mean benchmark
in 35/55 comparisons. Median RMSE ratios are close to one for every feature:
`0.9847` for seasonal mean temperature and `0.9974`--`1.0015` for the rainfall
quantity, timing, dry-spell, and extreme families. The worst fold ratios are
`1.0612` for maximum dry spell and `1.0757` for wet-day count. This mixed,
small-gain result is evidence that the mechanics work and that a one-scenario,
four-year slice is not enough to promote a GMST-only response form.

The machine-readable receipt is
`data/provenance/isimip3b_five_esm_holdout_smoke_20260827.json`. The long
training table and holdout CSV remain transient and uncommitted.

Production validation remains gated on the complete five-ESM by historical,
SSP1-2.6, SSP3-7.0, and SSP5-8.5 feature product, whole-ESM and whole-scenario
holdouts, same-realization GMST throughout, explicit support flags, common-
random-number baseline/pulse pairs, zero-pulse and pre-divergence identity,
and convergence across decreasing pulse sizes. MESMER-M-TP plus a published
daily generator remains a fallback only.

Reproduce the bounded smoke with:

```bash
./.venv/bin/python scripts/test_isimip3b_five_esm_holdout_smoke.py

./.venv/bin/python scripts/evaluate_isimip3b_five_esm_holdout_smoke.py \
  --config config/isimip3b_five_esm_ssp370_holdout_smoke_v1.toml \
  --training-out /private/tmp/give-five-esm-holdout/training.parquet \
  --holdouts-out /private/tmp/give-five-esm-holdout/holdouts.csv \
  --audit-out data/provenance/isimip3b_five_esm_holdout_smoke_20260827.json
```
