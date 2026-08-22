# Reproducibility and release instructions

## Repository boundary

This is a standalone precipitation-driven agriculture/SCC project. It contains
only its own code, documents, manifests, and tests. It must not vendor or
reference wildfire/biomass-burning code, data, outputs, or credentials.

## Environment

The prototype is Julia-first. The tracked `Project.toml` pins the direct Mimi
compatibility boundary; use Julia 1.8+ and a project-local depot. The current
daily-feature pipeline uses Python 3.11+ with `numpy`, `pandas`, `xarray`, and
a NetCDF engine.
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
3. Run the schema/validation gates in `VALIDATION_PROTOCOL.md`.
4. Fit the pre-registered crop-specific joint response and write coefficient
   draws outside raw-data paths.
5. Feed matched baseline/pulse region-crop feature arrays to
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
.venv/bin/python scripts/test_feature_builder.py
.venv/bin/python us_county_validation/scripts/test_prepare_nass_county_yields.py
JULIA_DEPOT_PATH=.julia_depot ../tools/julia-1.8.5/bin/julia --project=. -e 'using Pkg; Pkg.instantiate()'
JULIA_DEPOT_PATH=.julia_depot ../tools/julia-1.8.5/bin/julia --project=. test/runtests.jl
```
