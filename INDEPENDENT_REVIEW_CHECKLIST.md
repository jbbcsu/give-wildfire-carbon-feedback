# Independent critical-review checklist

This checklist is designed for a second analyst or coding agent. Do not accept
the manuscript or `RESULTS_STATUS.md` as evidence without tracing the claim.

## Repository and isolation

- Confirm the precipitation project has no import, symlink, or runtime
  dependency on wildfire working files.
- Confirm raw/interim/processed data and outputs are not Git-tracked and that
  no credentials or tokens are present.
- Compare the working tree and `precipitation-scc` branch; identify uncommitted
  or unreviewed analysis changes.

## Sources and data

- Resolve each DOI/URL in `SOURCES.md` and verify that the cited source supports
  the exact statement made.
- Verify every acquired file against its provenance record, declared size,
  checksum, coverage, version, and license.
- Independently inspect crop/calendar crosswalks, longitude conversion,
  latitude order, units, leap days, and cross-year crop seasons.
- Treat GDHY, FAOSTAT, NASS, ISIMIP, and crop-model outputs according to their
  documented dependence; do not count a derived source as independent
  validation.

## Analysis and inference

- Recreate panel row counts, uniqueness, missingness, and stage-to-season
  reconciliation from code and local artifacts.
- Verify holdout labels are outcome-blind and that no test observations enter
  estimation or model selection.
- Audit fixed effects, clustering/spatial dependence, nonlinear terms,
  temperature--precipitation interactions, CO2 treatment, and observed-support
  flags.
- Confirm PDSI/SPEI/soil moisture and direct precipitation features are
  competing representations rather than mechanically double counted.
- Compare aggregate seasonal-water results against OSCAR-crop and daily
  features against direct ISIMIP/CMIP output before accepting emulator output.
- Reproduce null and failed specifications as well as preferred results.

## GIVE and SCC

- Verify crop-specific responses survive aggregation and crop-value weights
  cover the full agricultural value pool or trigger a hard failure.
- Verify matched base/pulse identifiers, common random numbers,
  pre-divergence equality, pulse-size convergence, and discounting.
- Run the component-graph audit and confirm that the sole internal producer of
  `DamageAggregator.damage_ag` is `JointAgriculture.agcost`, no `Agriculture`
  component remains, and the unmodified GIVE baseline fails as a negative
  control.
- Verify the paired component-output audit rejects pre-divergence differences,
  malformed arrays, and a changing zero-pulse control; confirm it does not
  require a nonzero response to a nonzero pulse.
- Confirm infrastructure flooding remains absent and CIAM-covered coastal
  damages are not duplicated.
- Reject any SCC result that lacks a machine-readable draw artifact,
  uncertainty distribution, provenance, and an explicit promotion in
  `RESULTS_STATUS.md`.

## Minimum reproducibility commands

Use the project-local environments documented in `REPOSITORY.md`. Run all
Python synthetic pipeline tests, the provenance verifier for locally acquired
files, and the Julia test suite. Then rerun each manuscript table and figure
from its declared target rather than inspecting cached images.

Report discrepancies even if they do not change the central estimate. Classify
each as data, code, statistical identification, extrapolation, accounting,
documentation, or reproducibility risk.
