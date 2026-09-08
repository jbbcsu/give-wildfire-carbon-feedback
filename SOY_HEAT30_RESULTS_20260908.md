# Soybean 30°C control: real same-file completion

Both irrigation-calendar regimes were independently constructed at30°C from
the already validated GFDL-ESM4 SSP126 daily Tmax cutout. No download and no
29°C output overwrite were needed. Each regime has5,488seasonal and16,464stage
rows for2042–2049 at39.25/39.75N. Calendar, stage and seasonal reconciliation
pass before fixed MIRCA2000 weighting; the final2,616rows cover327soybean cells.

All existing rainfall and stage-mean-temperature fields match the prior29°C
joint input table exactly. An additional real cross-threshold check verifies
that30°C exceedance days never exceed29°C days and, for each stage, the
29-minus30°C degree-day difference lies between the30°C and29°C day counts.
These identities hold after the same fixed irrigation weighting.

The prespecified historical range check uses4,321positive-observed-yield
1982–2010rows from149cells. Of1,192evaluable future crop-years,703(58.98%)
exceed at least one of six historical30°C heat ranges. All departures are
above the corresponding historical maximum. Second-stage30°C degree days
are outside in263of1,192rows(22.06%);1,424future rows have no historical range.
This is an extrapolation diagnostic, not a yield loss, causal climate effect,
global geographic estimate or SCC. It now uses the locked soybean threshold;
that alone does not establish response transport or common joint support.

Four exact-join and four range tests pass, including explicit30°C-field tests.
Real construction/weighting took5.16s and472.63MiB sampled peak group RSS;
range comparison0.70s/138.73MiB; threshold-overlap check0.67s/90.98MiB. All
first executions passed, with numerical threads fixed at one. Tests and these
jobs are completed; do not rerun them as unfinished work.

Reproduce new output paths under the bounded runner:

```
.venv/bin/python scripts/extend_heat_cutout_two_crops.py \
  --pilot data/interim/authorized_heat_subset_real_20260908 \
  --out-dir data/interim/soy_heat30_real_20260908 \
  --crops soy --threshold-c 30 \
  --accounted-dir data/interim/two_crop_heat_real_20260908
.venv/bin/python scripts/compare_future_heat_ranges.py \
  --parent data/interim/soy_heat30_real_20260908/receipt.json \
  --out data/interim/soy_heat30_real_20260908/historical_heat_ranges.json
.venv/bin/python scripts/validate_soy_heat_threshold_overlap.py
```

The last script is an explicitly dated audit of these retained paths and
refuses to overwrite its receipt. Aggregate evidence, resource receipts and
input/output hashes are exported by`export_heat30_welfare_provenance.py`.
New scenario heat, spatial coverage, causal transport, CO2/adaptation and
monetary aggregation remain required; no damage coefficient was fitted here.
