# Wildfire Extension Change Log

## Added

- `WildfireGIVE.jl`
  - Adds standalone helper functions for wildfire CO2 paths.
  - Adds `wildfire_temperature_feedback_co2`, a lagged-temperature endogenous fire-carbon feedback component.
  - Inserts feedback emissions upstream of GIVE's existing `co2_emissions_identity` and before the marginal SCC pulse.

- `run_temperature_feedback_scc.jl`
  - Deterministic scenario runner for baseline, residual and RESFire stress cases.

- `run_temperature_feedback_mcs.jl`
  - Paired Monte Carlo runner for the temperature-feedback scenarios.
  - Samples feedback-parameter uncertainty using deterministic `SampleStore` draws.
  - Writes parameter draws, SCC samples and summary tables.
  - Supports an optional comma-separated scenario filter as the fourth command-line argument.

- `run_temperature_feedback_mcs.sh`
  - Reproducible shell wrapper for the Monte Carlo runner.

- `make_feedback_figures.jl`
  - Dependency-light SVG figure builder for deterministic fire CO2, concentration, temperature and damage paths.

- `run_regional_damage_map_diagnostics.jl`
  - Runs deterministic baseline and source-informed wildfire-path models.
  - Writes country-level total core damage increments and core-sector SCC contribution diagnostics.
  - Allocates FUND agriculture damages to countries by GDP share for map visualization.

- `make_png_pdf_figures.R`
  - Writes PNG/PDF manuscript figures, including truncated SCC distributions, scale checks, source proxy maps, incremental damage maps and sectoral diagnostics.

- `replication/README.md`
  - Commands, environment notes, output descriptions and double-counting treatment.

- `manuscript/wildfire_carbon_feedback_ncc_draft.md`
  - Draft manuscript in a Nature Climate Change-style structure, plus rendered LaTeX and PDF versions.

- `manuscript/methods_appendix.md`
  - Detailed methods appendix.

- `teaching_module/README.md`
  - Guided teaching module with readings, code walkthrough and exercises.

## Key Modeling Choices

- All emissions entering FAIR are in GtC/yr.
- Fire assumptions stated in GtCO2 are converted with `12/44`.
- The feedback uses trial-specific 2020 temperature as the reference temperature.
- Residual scenarios include explicit net-persistence and not-already-embedded fractions.
- RESFire half-gross and gross scenarios are retained only as diagnostic stress tests.
- Source-side map proxies are explicitly labeled as hand-coded 0-1 assumption indices, not model outputs.
- Damage-side maps include only GIVE core mortality, energy and agriculture damages and exclude CIAM sea-level rise and smoke mortality.

## Current Validation Status

- Deterministic mechanism check completed.
- Five-draw MCS smoke test completed.
- 100-draw paired MCS timing and validation run completed as of 2026-05-03.
- Full 10,000-draw run is scripted but not completed in this interactive session because the 100-draw timing implies a long sequential runtime for five scenarios.
