# Aggregate-irrigation heat-control basis contract

## Purpose and inference boundary

`scripts/allocate_irrigation_heat_basis.py` creates the common non-moisture
control table required by the locked direct-weather versus historical-scPDSI
predictive diagnostic. It estimates no climate response, yield response,
damage, future projection, or SCC quantity. The 29 °C and 30 °C thresholds are
registered diagnostic definitions, not production thresholds and not choices
selected by yield fit or SCC magnitude.

The output contract is
`global_crop_stage_heat_control_basis_v1`, with source role
`common_nonmoisture_controls_only`. `diagnostic_fit_authorized=true` permits
only the separate, locked nonproduction predictive diagnostic. Family
stacking, coefficient export, causal interpretation, production model
selection or fitting, response-draw creation, damage calculation, future
projection, SCC use, and selection by SCC are all exactly false.

## Immediate inputs

One file for each of `noirr` and `firr` is required for all three input types:

1. the direct candidate panel, carrying one aggregate GDHY outcome plus the
   regime's exact crop calendar, stage lengths, and stage mean temperature;
2. the combined seasonal daily-maximum-temperature summary; and
3. the combined three-stage daily-maximum-temperature summary.

The fourth input is a fixed MIRCA baseline area-share table. The direct panels
must have identical crop-grid-year keys and exactly identical outcome values
and missingness. Calendars may differ between rainfed and irrigated regimes,
but each panel calendar must equal its corresponding heat calendar exactly:
plant year, cross-year status, planting and maturity day, season length, stage
lengths, longitude, and crop-grid-year identity. Equal-duration shifted
calendars fail.

The caller declares the crop, complete year range, threshold list, three-stage
count, and ordered irrigation labels exactly. Heat source tables are checked
with the existing strict season and stage schemas. Hotter-threshold day counts
must nest inside cooler-threshold counts, and degree days must satisfy the
necessary cross-threshold bounds.

## Season/stage reconciliation and allocation order

Seasonal heat remains a required validation input even though the narrow
downstream table exposes stage controls only. Within each regime and before
any area weighting:

- stage lengths must sum to season length;
- stage hot-day counts and degree days must sum to their seasonal values;
- the stage-day-weighted maximum-temperature mean must equal the seasonal
  maximum-temperature mean; and
- stage offsets must be integer, contiguous, start at crop-season day one,
  and use one common fraction definition.

The actual allocation is:

1. take `stage1_tmean_c`, `stage2_tmean_c`, and `stage3_tmean_c` from each
   regime's direct panel;
2. take each registered stage `tmax_{29,30}c_days` and
   `tmax_{29,30}c_degree_days` from that regime's validated stage-heat table;
3. construct this complete basis inside the regime;
4. multiply every already-constructed basis column by the independent fixed
   MIRCA area share; and
5. sum across `noirr` and `firr` to one crop-grid-year outcome row.

Applying a threshold or any other nonlinear transform after averaging regimes
is forbidden. Weighted hot-day counts are exposures and can therefore be
fractional.

## Exact output schema

The output contains only:

- keys: `harvest_year`, `lat`, `lon_360`, `crop`;
- outcomes: `yield_observed`, `yield_t_ha`;
- three stage mean-temperature fields;
- for every exactly declared 29 °C or 30 °C threshold, three stage hot-day and
  three stage degree-day fields;
- `heat_control_basis_contract_id`, `source_role`, and
  `diagnostic_fit_authorized`; and
- the ten exact false gates used by the downstream diagnostic.

No precipitation, dry-spell, wet-extreme, PDSI/scPDSI, SPEI, or other moisture
term is allowed. Rich allocation metadata belongs in the JSON audit, not in
the narrow Parquet table, because the downstream diagnostic rejects unknown
columns. For the current registered primary comparison, maize uses 29 °C and
soy uses 30 °C; any alternative or joint-threshold run must declare and retain
its own exact threshold list and remains diagnostic.

## Coverage and weights

Missing heat fails by default. The optional
`--exclude-missing-heat-cells` flag permits only exclusion of the complete
crop-grid-year outcome if either regime lacks a seasonal or stage heat window.
There is no infill.

Missing MIRCA support also fails by default. The optional
`--exclude-missing-weight-cells` behavior is inherited from the one-outcome
allocator: it excludes the complete crop-grid-year outcome, reports the loss,
and never fills or renormalizes weights. Every retained crop-grid cell must
contain both regimes and fixed shares summing to one.

## Provenance and validation

The allocation audit records ordered paths and SHA-256 hashes for every direct
panel, seasonal heat table, stage heat table, weight file, and output. It also
records exact expectations, source row counts, whole-key exclusions, the
feature list, allocation order, and every authorization gate.

`scripts/validate_irrigation_heat_basis.py` rereads all immediate inputs,
checks those hashes and the exact audit schema, recomputes the entire derived
basis and fixed-share allocation, and requires frame equality with the stored
Parquet output. It emits the strict receipt expected by the downstream
diagnostic. This is a complete recomputation from the immediate summary
inputs. It does **not** reopen raw daily temperature and therefore records
`upstream_raw_daily_heat_recomputation_performed=false` in the audit.

Example for the registered maize diagnostic:

```bash
./.venv/bin/python scripts/allocate_irrigation_heat_basis.py \
  --panel MAIZE_NOIRR_DIRECT.parquet --panel MAIZE_FIRR_DIRECT.parquet \
  --season-heat MAIZE_NOIRR_SEASON_HEAT.parquet \
  --season-heat MAIZE_FIRR_SEASON_HEAT.parquet \
  --stage-heat MAIZE_NOIRR_STAGE_HEAT.parquet \
  --stage-heat MAIZE_FIRR_STAGE_HEAT.parquet \
  --weights MIRCA_FIXED_WEIGHTS.parquet \
  --expected-irrigation noirr --expected-irrigation firr \
  --expected-crop mai --expected-year-start 1982 --expected-year-end 1989 \
  --threshold-c 29 --threshold-c 30 --stages 3 \
  --out data/interim/diagnostic_heat_controls/maize_1982_1989_heat_control_basis.parquet \
  --audit-out outputs/diagnostic_heat_controls/maize_1982_1989_heat_control_audit.json
```

The validator takes the same ordered sources plus `--candidate` and
`--allocation-audit`. Synthetic tests cover outcome disagreement, shifted
equal-duration calendars, incomplete heat and irrigation regimes, missing and
non-unit weights, threshold nesting, numeric and Boolean type gates, stale
source hashes, authorization-audit tampering, and a post-weighting threshold
transform.
