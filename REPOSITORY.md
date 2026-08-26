# Reproducibility and release instructions

## Repository boundary

This is a standalone precipitation-driven agriculture/SCC project. It contains
only its own code, documents, manifests, and tests. It must not vendor or
reference wildfire/biomass-burning code, data, outputs, or credentials.

## Environment

The prototype is Julia-first. The tracked `Project.toml` pins the direct Mimi
compatibility boundary; use Julia 1.8+ and a project-local depot. The current
daily-feature pipeline uses Python 3.11+ with `numpy`, `pandas`, `xarray`, a
NetCDF engine, and `rasterio` for publisher-supplied MIRCA-OS GeoTIFFs.
The tracked `Manifest.toml` locks the Julia dependency graph used by the test
suite; regenerate and review it deliberately when changing dependencies.

## Reproducible order

1. Run `scripts/verify_provenance.py` after every download.
   Use `scripts/download_isimip3a_climate.sh pr tas` for the first climate
   stage and `scripts/download_isimip3a_climate.sh --all` only when the final
   temperature-extreme controls are required.
2. Use `scripts/build_crop_year_features.py` on daily climate and crop-calendar
   files to make an auditable crop-year panel.
   `scripts/build_feature_partitions.sh` runs the same builder in resumable
   ten-latitude partitions, avoiding global daily-array loads.
   `scripts/combine_feature_partitions.py` refuses to combine an incomplete or
   schema-inconsistent partition set.
   Use `scripts/build_stage_feature_partitions.sh` for the separate
   stage-resolved panel; retain both products for reconciliation.
   For a complete historical crop/irrigation/time chunk, use
   `scripts/run_historical_crop_chunk.sh`. It runs both resumable latitude
   extractions, refuses incomplete partition sets, reconciles stage and season
   quantities, joins GDHY, and writes the stage-pattern panel below the ignored
   `data/interim/` boundary.
   Use `scripts/build_heat_feature_partitions.sh` and
   `scripts/build_stage_heat_partitions.sh` only after registering explicit
   temperature thresholds. Validate and combine every latitude partition, then
   run `scripts/reconcile_stage_heat_features.py` against the seasonal heat
   product. Use `scripts/join_stage_heat_features.py` only after that audit to
   preserve one regression row per crop-year/grid.
   Acquire fixed irrigation weights with `scripts/download_mirca_os_v2.py`,
   build each declared vintage with `scripts/build_mirca_irrigation_shares.py`,
   and audit observed-cell support before combining calendar exposures.
   The separate rice-season candidate is acquired by
   `scripts/download_mirca_rice_seasons.py` and must pass
   `scripts/audit_mirca_rice_inventory.py` plus the annual reconciliation in
   `scripts/build_mirca_rice_season_shares.py`; current v2 files fail both
   documented gates, so no rice weights are promoted.
   For maize/soybean, construct the minimal predictive basis with
   `scripts/allocate_irrigation_response_basis.py`. Construct the broader
   direct precipitation-pattern candidate table with
   `scripts/allocate_irrigation_distribution_basis.py`; it builds all
   nonlinear quantity/distribution/occurrence/intensity/dry-spell/Rx terms by
   regime before weighting and remains explicitly unfit for estimation until
   the production model and thresholds are frozen.
   For a completed rainfed/fully-irrigated crop-period pair, use
   `scripts/run_irrigation_basis_chunk.sh` to reproduce the minimal held-out
   diagnostic and the validated, unfitted 54-column distribution candidate in
   one fail-closed run. The wrapper is currently restricted to maize and
   soybean because rice and wheat lack approved season-specific MIRCA weights.
   To construct the separate historical climatic-water-balance candidate, run
   `scripts/run_scpdsi_candidate_chunk.sh` with the pinned CRU scPDSI object,
   both crop calendars, both completed crop-period panels, and the fixed MIRCA
   weights. It source-binds and validates every latitude partition, constructs
   all nonlinear drought-index features within regime before area weighting,
   and fully recomputes the final candidate from the derived stage tables. The
   candidate validator does not claim an independent raw-metric recomputation.
   It does not fit a response and cannot
   provide a future drought or SCC input.
   Build the direct-weather/scPDSI common-support basis with
   `scripts/build_direct_scpdsi_common_support.py` and validate it with
   `scripts/validate_direct_scpdsi_common_support.py`. The four current bundles
   emit separate 54-feature direct and 16-feature scPDSI views. Common
   rows/observed outcomes and direct-only dropped rows/observed outcomes are:
   maize 1982--1989, 240,784/115,758 and 24,744/1,921; soybean 1982--1989,
   176,537/47,653 and 14,935/269; maize 2012--2016, 150,490/59,772 and
   15,465/1,046; soybean 2012--2016, 110,336/26,601 and 9,334/147. All four
   scPDSI-only drop counts are 0/0. This validation is limited to hashes and
   exact recomputation from the supplied immediate inputs; it does not rerun
   upstream raw sources or bind upstream validation receipts. Run the upstream
   validators and retain their receipts as an external prerequisite. The
   output is data-only: no model fit, coefficient, causal effect, selection,
   future projection, damage, or SCC result. Keep seasonal quantity as the
   reference, retain distribution only for robust stable outer-holdout value,
   and compare drought families mutually exclusively rather than stacking.
   When annual GDHY support changes within a diagnostic period, construct the
   separately labeled complete-support sensitivity with
   `scripts/filter_complete_yield_support.py`. Never treat this conditioning
   step as imputation or as the primary sample.
   Before welfare aggregation, run
   `scripts/audit_mirca_welfare_support.py`; do not substitute cell-count
   coverage for harvested-area, production, or crop-value coverage, and do
   not aggregate crops without pinned crop-value weights.
3. Run the schema/validation gates in `VALIDATION_PROTOCOL.md`.
4. Fit the pre-registered crop-specific joint response and write coefficient
   draws outside raw-data paths.
5. Feed matched baseline/pulse region-crop feature arrays to
   `scripts/validate_scc_response_bundle.py`. A passing audit is a structural
   gate, not an empirical-performance result. Then feed the validated arrays to
   `CropResponseAggregation`, then connect its regional joint-loss fraction to
   `JointAgriculture`; replace rather than add to MooreAg. Production SCC runs
   retain the default full-coverage gate.

## Release gate

Before a public push, inspect `git status --ignored`, scan tracked files for
credentials, confirm `data/raw/` is ignored, and review all manifests against
data licenses. A remote must be explicitly supplied or created by the user;
never push to a guessed GitHub destination.

## Local checks

```sh
.venv/bin/python scripts/verify_provenance.py data/provenance
.venv/bin/python scripts/validate_response_spec_boundaries.py
.venv/bin/python scripts/test_validate_response_spec_boundaries.py
.venv/bin/python scripts/test_feature_builder.py
.venv/bin/python scripts/test_download_mirca_os_v2.py
.venv/bin/python scripts/test_build_mirca_irrigation_shares.py
.venv/bin/python scripts/test_validate_mirca_weight_coverage.py
.venv/bin/python scripts/test_audit_mirca_welfare_support.py
.venv/bin/python scripts/test_allocate_irrigation_response_basis.py
.venv/bin/python scripts/test_allocate_irrigation_distribution_basis.py
.venv/bin/python scripts/test_download_mirca_rice_seasons.py
.venv/bin/python scripts/test_audit_mirca_rice_inventory.py
.venv/bin/python scripts/test_build_mirca_rice_season_shares.py
.venv/bin/python scripts/test_verify_provenance.py
.venv/bin/python scripts/test_stage_heat_pipeline.py
.venv/bin/python scripts/test_run_historical_crop_chunk.py
.venv/bin/python scripts/test_run_irrigation_basis_chunk.py
.venv/bin/python scripts/test_stage_scpdsi_pipeline.py
.venv/bin/python scripts/test_allocate_irrigation_scpdsi_basis.py
.venv/bin/python scripts/test_run_scpdsi_candidate_chunk.py
.venv/bin/python scripts/test_render_precipitation_distribution_table.py
.venv/bin/python scripts/test_filter_complete_yield_support.py
.venv/bin/python scripts/test_scc_response_bundle.py
.venv/bin/python us_county_validation/scripts/test_prepare_nass_county_yields.py
JULIA_DEPOT_PATH=.julia_depot ../tools/julia-1.8.5/bin/julia --project=. -e 'using Pkg; Pkg.instantiate()'
JULIA_DEPOT_PATH=.julia_depot ../tools/julia-1.8.5/bin/julia --project=. test/runtests.jl
```

The isolated component tests above use native Julia 1.8.5. Reproducing the
executed control against the archived GIVE checkout currently requires its
original x86_64 Julia 1.6.4 environment under Rosetta:

```sh
arch -x86_64 env JULIA_DEPOT_PATH=../.julia_depot_1_6 \
  ../tools/julia-1.6.4/bin/julia \
  --project=../paper-2022-scc-give-zenodo \
  scripts/test_give_replacement_harness.jl \
  ../paper-2022-scc-give-zenodo
```

A native Apple-silicon Julia 1.8.5 attempt stops before the harness because
the archived GIVE dependency lock requests an unavailable Electron artifact
for `aarch64-apple-darwin`. This is a baseline-environment portability limit;
it is not evidence that the replacement passed under native ARM.
