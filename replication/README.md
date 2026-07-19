# Wildfire-Carbon Feedback Replication Package

This directory documents the reproducible extension that adds a temperature-dependent wildfire CO2 feedback to the Rennert et al. (2022) GIVE replication archive.

## Scope

The extension is deliberately separate from the original replication scripts. It does not overwrite the baseline GIVE model. The key scientific distinction is:

- The original RFF-SP input used by GIVE contains one aggregate global CO2 emissions path in GtC/yr.
- The released RFF-SP file does not decompose CO2 into fossil, industrial process, AFOLU, biomass burning, wildfire, natural-stock changes, or negative-emissions components.
- Therefore the defensible first-pass wildfire-carbon experiment is a residual feedback: added fire CO2 is scaled down by explicit net-persistence and not-already-embedded fractions.
- Gross fire cases are retained only as stress tests because they are not double-counting safe.

## Code Entry Points

- `../WildfireGIVE.jl`: model extension module.
- `../run_temperature_feedback_scc.jl`: deterministic scenario run used for quick mechanism checks.
- `../run_temperature_feedback_mcs.jl`: paired Monte Carlo run with endogenous wildfire feedback parameter uncertainty.
- `../run_temperature_feedback_mcs.sh`: shell wrapper for the Monte Carlo run.

## Julia Environment

The local Julia binary used for this package is:

```bash
/Users/jbb/Dropbox/GIVE/tools/julia-1.6.4/bin/julia
```

The Julia depot used during testing is:

```bash
/Users/jbb/Dropbox/GIVE/.julia_depot_1_6
```

The active project is the original Zenodo replication project:

```bash
/Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/Project.toml
/Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/Manifest.toml
```

## Quick Validation

Run the deterministic mechanism check:

```bash
JULIA_DEPOT_PATH=/Users/jbb/Dropbox/GIVE/.julia_depot_1_6 \
/Users/jbb/Dropbox/GIVE/tools/julia-1.6.4/bin/julia \
  --project=/Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo \
  /Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/wildfire_extension/run_temperature_feedback_scc.jl \
  /Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/output/wildfire_temperature_feedback
```

Run a five-draw smoke test of the Monte Carlo machinery:

```bash
/Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/wildfire_extension/run_temperature_feedback_mcs.sh \
  5 \
  /Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/output/wildfire_temperature_feedback_mcs_smoke \
  20260503
```

Run a 100-draw validation run:

```bash
/Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/wildfire_extension/run_temperature_feedback_mcs.sh \
  100 \
  /Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/output/wildfire_temperature_feedback_mcs_100 \
  20260503
```

Run the requested 10,000-draw scenario set:

```bash
/Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/wildfire_extension/run_temperature_feedback_mcs.sh \
  10000 \
  /Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/output/wildfire_temperature_feedback_mcs_10000 \
  20260503
```

Run the same production job as a detached logged process:

```bash
/Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/wildfire_extension/run_temperature_feedback_mcs_10000_detached.sh \
  10000 \
  20260503 \
  all
```

For a production run that should survive the Codex terminal session, submit the worker through macOS `launchctl`:

```bash
launchctl submit -l org.give.wildfire.mcs.20260612_0900 -- \
  /Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/wildfire_extension/run_temperature_feedback_mcs_worker.sh \
  10000 \
  20260503 \
  all \
  20260612_0900
```

The detached runner writes a PID file and log file to:

```text
/Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/output/wildfire_temperature_feedback_mcs_logs
```

The `launchctl` worker writes a `.status`, `.pid`, and `.log` file to the same directory. The run submitted on 2026-06-12 uses:

```text
Output directory: /Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/output/wildfire_temperature_feedback_mcs_10000_full_20260612_0900
Log file: /Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/output/wildfire_temperature_feedback_mcs_logs/wildfire_temperature_feedback_mcs_10000_20260612_0900.log
Status file: /Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/output/wildfire_temperature_feedback_mcs_logs/wildfire_temperature_feedback_mcs_10000_20260612_0900.status
PID file: /Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/output/wildfire_temperature_feedback_mcs_logs/wildfire_temperature_feedback_mcs_10000_20260612_0900.pid
```

That 10,000-draw run was intentionally stopped on 2026-06-12 before completion. The partial output directory is marked with `RUN_STOPPED_BY_USER.txt` and should not be used for manuscript values. Current manuscript and figure values remain based on the completed 100-draw paired validation run until a new production run is requested.

Run a selected scenario plus the paired baseline:

```bash
/Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/wildfire_extension/run_temperature_feedback_mcs.sh \
  10000 \
  /Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/output/wildfire_temperature_feedback_mcs_10000_residual_high \
  20260503 \
  feedback-residual-high
```

Multiple scenarios can be passed as a comma-separated fourth argument. The baseline is always included for comparison.

The five-scenario 10,000-draw run executes 50,000 total SCC model evaluations plus setup. Based on the corrected 100-draw timing test, it should be treated as an overnight or multi-day job on this machine unless the scenarios are distributed across workers. The 100-draw paired validation output is:

On 2026-06-12 the 10,000-draw production driver was test-launched and manually stopped after the baseline scenario reached roughly 2% completion. The ETA at that point was about six hours for baseline alone, implying roughly a day-plus for the full five-scenario run on this machine. The partial directory `output/wildfire_temperature_feedback_mcs_10000` contains setup files only and is marked with `RUN_INCOMPLETE.txt`; it should not be used for manuscript numbers.

```text
/Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/output/wildfire_temperature_feedback_mcs_100_paired/scc_summary.csv
```

For the 2.0% discount case, the 100-draw paired validation gives:

| Scenario | Mean SCC | Median SCC | 5th | 95th | Delta mean | Delta % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 198.35 | 155.82 | 33.39 | 464.21 | 0.00 | 0.00% |
| feedback-residual-medium | 198.89 | 156.03 | 33.46 | 465.23 | 0.54 | 0.27% |
| feedback-residual-high | 209.57 | 161.67 | 35.80 | 485.26 | 11.21 | 5.65% |
| feedback-resfire-half-gross | 262.79 | 194.93 | 45.45 | 646.43 | 64.44 | 32.49% |
| feedback-resfire-gross | 346.37 | 248.55 | 84.63 | 785.47 | 148.02 | 74.62% |

## Output Files

Each Monte Carlo run writes:

- `paired_mcs_ids.csv`: FAIR and RFF-SP draw IDs used in all scenarios.
- `all_feedback_parameter_draws.csv`: sampled wildfire-feedback parameters.
- `all_scc_samples.csv`: scenario-level SCC samples.
- `scc_summary.csv`: mean, median, 2.5th, 5th, 95th, and 97.5th percentile SCC values.
- PNG/PDF figures are written to `wildfire_extension/manuscript/figures/png_pdf`.
- Per-scenario folders with `feedback_parameter_draws.csv` and `scc_samples.csv`.

The figure builder adds uncertainty summaries for the 2.0% discount case:

- `paired_scc_delta_interval_summary_2pct.csv`: paired-delta intervals and exceedance probabilities.
- `paired_scc_delta_interval_summary_2pct.md`: manuscript-ready paired-delta table.
- `wildfire_parameter_draw_summary.csv`: sampled beta, persistence, missing-share and effective-intensity summaries.
- `uncertainty_source_diagnostics_2pct.csv`: descriptive baseline-state versus fire-intensity uncertainty diagnostics.

The parameter-accounting framework is documented in:

```text
/Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/wildfire_extension/source_data/wildfire_parameter_uncertainty_framework.csv
```

Additional diagnostics:

- `output/wildfire_sectoral_diagnostics_100`: sectoral marginal-damage diagnostics with `save_md=true` and `compute_sectoral_values=true`.
- `output/wildfire_regional_damage_diagnostics`: country-level map inputs for total core damage increments and core-sector SCC contributions.
- `output/wildfire_temperature_feedback_refyear_check/fire_scale_check_deterministic.csv`: deterministic fire-flow and atmospheric-stock scale checks.

## Baseline Replication Target

The published Rennert et al. (2022) preferred mean SC-CO2 is about $185/tCO2 in 2020 USD under the 2.0% near-term Ramsey discount specification. A small 100-draw run will not reproduce that value exactly because the SCC distribution is broad and right-skewed. The full 10,000-draw run is the relevant replication check.

## Double-Counting Treatment

The residual scenarios sample:

- `sensitivity_per_c`: fractional gross fire-emissions response per degree C of global warming above the run-specific 2020 reference temperature.
- `net_persistence_fraction`: fraction of gross fire carbon treated as persistent net atmospheric CO2 after regrowth and other land-carbon adjustment.
- `not_embedded_fraction`: fraction not assumed already captured in the RFF-SP aggregate CO2 pathway.

The RESFire half-gross and gross cases set the latter two fractions to 1.0. Those runs are diagnostic upper bounds, not preferred estimates.
