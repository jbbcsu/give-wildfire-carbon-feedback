# Labor productivity SCC extension

This isolated project reproduces and evaluates the published labor-productivity
damage extension to GIVE from Moore et al. (2026). It does not modify or depend
on the wildfire-CO2 project.

## Fast route

The primary replication source is the authors' MIT-licensed GIVE archive:

- Article: <https://doi.org/10.1038/s41558-026-02749-z>
- Model code: <https://doi.org/10.5281/zenodo.21483095>
- Sectoral heat-stress inputs: <https://doi.org/10.5281/zenodo.21712766>
- Agricultural analysis capsule: <https://doi.org/10.24433/CO.9032029.v1>

The exact archived source is retained under `vendor/moore_2026/`; new work must
not edit files there. Reproduction wrappers and receipts belong in `scripts/`,
`data/provenance/`, and `output/`.

## Current labor result

Both 10,000-draw structural cases have been reproduced. The labor-only
fast-track release is documented in `LABOR_FASTTRACK_RELEASE.md`: the
equal-weight mean of the Lancet and ISO case means is **$40.5643/tCO2** in 2020
USD, with structural case means of $29.2638 and $51.8647/tCO2. This partial SCC
is eligible for matched-contract mean transfer after confirming that the target
GIVE run has no active labor-productivity sector. Cross-function quantiles and
standard errors are intentionally not pooled.

The exact-target integration is now complete at the expected-value level; see
`GIVE_INTEGRATION_COMPLETE.md`. In the published updated-agriculture GIVE
target, the equal-weight expected SCC is $138.5939/tCO2 without labor and
$179.1581/tCO2 with labor. The validated additive labor contribution is
$40.5643/tCO2. Same-run uncertainty remains case-specific.

## Reproduction environment

- Julia 1.12.5 (the version named by the authors)
- One Julia thread to control memory
- A project-local Julia depot at `.julia_depot/`
- Published `Project.toml` and `Manifest.toml` unchanged

The deterministic smoke test uses SSP2-4.5 and runs only the labor and
agriculture sectors, separately. It therefore avoids interpreting a total SCC
as a sectoral SCC and does not require the 1.46 GB RFF-SP archive:

```sh
env JULIA_NUM_THREADS=1 \
  JULIA_DEPOT_PATH="$PWD/.julia_depot" \
  ../tools/julia-1.12.5/bin/julia \
  --project=vendor/moore_2026/lrennels-paper-2026-give-labor-ag-5d034e7 \
  scripts/smoke_replicate.jl
```

The smoke result is a code-path check, not the paper's Monte Carlo estimate.
Promotion requires reproducing the authors' 10,000-draw configuration and
matching their reported sectoral summaries within a prespecified tolerance.

After the RFF-SP dependency is installed, a staged Monte Carlo replication can
be run with one labor response and the paper's 2% discount schedule:

```sh
env JULIA_NUM_THREADS=1 DATADEPS_ALWAYS_ACCEPT=true \
  JULIA_DEPOT_PATH="$PWD/.julia_depot" \
  N_TRIALS=100 LABOR_FUNCTION=ISO \
  ../tools/julia-1.12.5/bin/julia \
  --project=vendor/moore_2026/lrennels-paper-2026-give-labor-ag-5d034e7 \
  scripts/replicate_sectoral_scc.jl
```

The staging sequence is 100, 1,000, then 10,000 draws. Advancement requires a
successful receipt, bounded memory, and stable signs and magnitudes; only the
10,000-draw run is eligible for comparison with the paper's headline values.
