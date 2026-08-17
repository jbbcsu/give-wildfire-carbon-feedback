# Reproducibility and release instructions

## Repository boundary

This is a standalone precipitation-driven agriculture/SCC project. It contains
only its own code, documents, manifests, and tests. It must not vendor or
reference wildfire/biomass-burning code, data, outputs, or credentials.

## Environment

The prototype is Julia-first. Install Julia 1.8+ and create a project-local
environment with `Mimi`, `NetCDF`, `CSV`, `DataFrames`, and `Statistics`.
The planned feature builder also supports Python 3.11+ with `numpy`, `pandas`,
`xarray`, and a NetCDF engine. Exact package versions must be locked in a
future `Manifest.toml`/lock file before estimation results are released.

## Reproducible order

1. Run `scripts/verify_provenance.py` after every download.
   Use `scripts/download_isimip3a_climate.sh pr tas` for the first climate
   stage and `scripts/download_isimip3a_climate.sh --all` only when the final
   temperature-extreme controls are required.
2. Use `scripts/build_crop_year_features.py` on daily climate and crop-calendar
   files to make an auditable crop-year panel.
3. Run the schema/validation gates in `VALIDATION_PROTOCOL.md`.
4. Fit the pre-registered joint response and write coefficient draws outside
   raw-data paths.
5. Feed matched baseline/pulse 16-FUND feature arrays to `JointAgriculture`;
   replace rather than add to MooreAg.

## Release gate

Before a public push, inspect `git status --ignored`, scan tracked files for
credentials, confirm `data/raw/` is ignored, and review all manifests against
data licenses. A remote must be explicitly supplied or created by the user;
never push to a guessed GitHub destination.

## Local checks

```sh
.venv/bin/python scripts/verify_provenance.py data/provenance
.venv/bin/python scripts/test_feature_builder.py
tools/julia-1.8.5/bin/julia -e 'include("src/AdaptationScenarios.jl")'
```
