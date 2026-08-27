# Continuous global panel: post-build assembly contract

## Purpose and current status

`scripts/assemble_continuous_global_panel_partitions.py` is the fail-closed
post-build gate for the isolated 1990–2011 maize/soy feature construction. On
2026-08-27 it passed the complete synthetic/adversarial suite, validated all
720 real tasks in read-only preflight, and completed the real atomic assembly.
The source registry contains 720 partition receipts and 144 source-bound
scPDSI manifests; no missing, extra, stale, or unauthorized artifact was
accepted.

The assembler is feature engineering only. It does not read crop outcomes,
fit a response, select a moisture family, export coefficients, project future
climate, calculate damages, or calculate an SCC.

## Required source state

Before writing anything, the production command requires exactly:

- 36 non-overlapping ten-latitude-index bands covering `[0, 360)`;
- two crops (`mai`, `soy`), two irrigation regimes (`noirr`, `firr`), and five
  separate families (`direct_season`, `direct_stage`, `heat_season`,
  `heat_stage`, and `historical_scpdsi_stage`);
- harvest years 1990–2011 for every populated partition;
- all 720 registered parquet files and all 720 source-bound build receipts;
- all 144 source manifests for historical scPDSI and no unregistered parquet,
  receipt, or scPDSI-manifest file in the partition tree; and
- no active task lock.

Every receipt is checked against the current config, task identity, source
objects, builder-code identities, output SHA-256, byte count, and parquet row
count. Each scPDSI manifest is checked against its output and the source hashes
in the corresponding receipt. A missing, extra, stale, malformed, or
unauthorized artifact stops the run before aggregate output is created.

## Bounded assembly and reconciliation

The assembler writes 20 tables (five families × two crops × two irrigation
regimes). It reads, validates, sorts, and appends one latitude partition at a
time with a parquet writer. The final directory is staged and renamed
atomically; an existing aggregate directory is never overwritten.

Reconciliation is evaluated in bounded latitude bands:

- direct-stage keys must equal direct-season keys; stage days, precipitation,
  wet days, day-weighted mean temperature, and Rx1day must reconcile exactly
  within the declared numerical tolerance, while CDD and stage-local Rx5day
  obey their mathematically valid bounds;
- heat-stage keys must equal heat-season keys; stage days, threshold-day
  counts, degree days, and day-weighted mean maximum temperature must
  reconcile;
- direct-season and heat-season keys and crop-calendar identities must match;
  and
- historical scPDSI stage keys must be an exact subset of direct-weather stage
  keys. The receipt reports direct-only and common support explicitly. It
  forbids scPDSI-only keys and silent infill and retains the role
  `historical_benchmark_not_future_scc_input`.

Candidate moisture families remain separate outputs. The aggregate receipt is
deterministic, contains only project-relative paths, and binds every input
partition, receipt, optional manifest, output table, hash, byte count, row
count, and reconciliation result. It contains no raw data or absolute paths.
Keys and integer counts are exact. The general floating-point reconciliation
tolerance is `1e-9`; direct stage-weighted mean temperature has a separately
declared `2e-5` °C roundoff tolerance because the source builders independently
average float32 daily temperatures (the bounded real pilot maximum was
`8.686934368284938e-6` °C).

The completed direct-season, direct-stage, heat-season, and heat-stage tables
contain 1,483,240, 4,449,720, 1,483,240, and 4,449,720 rows per crop-regime.
Historical scPDSI contains 3,619,680--3,619,692 stage rows per crop-regime and
is an exact subset of direct-weather support, with no scPDSI-only key. Direct
stage/season precipitation differs by at most `4.55e-13` mm, mean temperature
by `1.42e-5` °C, and all registered heat reconciliations pass.

After GDHY outcome joining and fixed-MIRCA regime-basis-before-weighting,
validated 1990--2011 direct/heat candidates retain 730,202 rows and 321,632
observed maize yields and 526,548/131,417 soybean rows/outcomes. The historical
scPDSI candidates retain 662,144/316,388 maize and 485,479/130,663 soybean
rows/outcomes. Source-compatible early, middle, and late schemas then assemble
into separate continuous 1982--2016 direct, heat, and historical-scPDSI
candidates. Exact direct/scPDSI common support contains 1,053,418 maize rows
with 491,918 observed outcomes and 772,352 soybean rows with 204,917 outcomes.
These remain data and predictive-diagnostic inputs only.

## Commands

Once the real 720-task build is complete, a read-only preflight is:

```bash
./.venv/bin/python scripts/assemble_continuous_global_panel_partitions.py \
  --config config/continuous_global_panel_1982_2016_v1.toml
```

The aggregate is written only with the explicit execution flag:

```bash
./.venv/bin/python scripts/assemble_continuous_global_panel_partitions.py \
  --config config/continuous_global_panel_1982_2016_v1.toml \
  --execute
```

The synthetic complete-registry and adversarial test is:

```bash
./.venv/bin/python scripts/test_assemble_continuous_global_panel_partitions.py
```

The test covers the locked 720-task registry, atomic 20-table assembly, exact
reconciliation, allowed scPDSI subset support, missing receipts, unregistered
partitions, output-hash tampering, manifest-hash tampering, missing years,
cross-family metric disagreement, scPDSI keys outside direct support, and
absolute-path rejection.
