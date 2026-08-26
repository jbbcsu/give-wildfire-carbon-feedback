# FishMIP common-support scenario benchmark

Status: validated biophysical scenario diagnostic; not a matched CO2 pulse,
welfare estimate, damage function, or SCC input.

The registered diagnostics use 12 validated files spanning two climate
forcings, two ecosystem models, and two emissions scenarios, without selecting
among them from their results. For each climate forcing it intersects the
time-stable BOATS and EcoOcean finite masks, retaining 41,029 one-degree cells
under GFDL-ESM4 and 40,399 under IPSL-CM6A-LR. Within each model it computes the cosine-latitude
weighted monthly mean of `tc` density, averages the 12 months within each year,
and compares three future decades under SSP1-2.6 and SSP5-8.5 with the model's
own 2005--2014 historical reference. Unsupported cells remain missing; they
are never changed to zero. Both scenarios use the same historical files,
reference decade, weighting rule, reporting periods, and common support.

| Climate forcing | Scenario | Ecosystem model | 2005--2014 reference (`g m-2`) | 2021--2030 change | 2041--2050 change | 2081--2090 change |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| GFDL-ESM4 | SSP1-2.6 | BOATS | 1.81663044513e-08 | -26.04% | -32.78% | -35.62% |
| GFDL-ESM4 | SSP1-2.6 | EcoOcean | 0.112406880682 | +0.27% | -0.98% | -24.40% |
| GFDL-ESM4 | SSP5-8.5 | BOATS | 1.81663044513e-08 | -25.61% | -33.70% | -42.91% |
| GFDL-ESM4 | SSP5-8.5 | EcoOcean | 0.112406880682 | -0.64% | -3.01% | -31.90% |
| IPSL-CM6A-LR | SSP1-2.6 | BOATS | 1.28962579791e-08 | -20.08% | -27.35% | -29.31% |
| IPSL-CM6A-LR | SSP1-2.6 | EcoOcean | 0.081846606621 | -3.92% | -5.28% | -21.17% |
| IPSL-CM6A-LR | SSP5-8.5 | BOATS | 1.28962579791e-08 | -19.77% | -29.19% | -36.94% |
| IPSL-CM6A-LR | SSP5-8.5 | EcoOcean | 0.081846606621 | -4.06% | -5.35% | -27.42% |

The absolute density scales differ greatly between the two ecosystem models
and also change with climate forcing, so the diagnostic does not average
levels or treat any level as an observed catch calibration. Both ecosystem
models under both climate forcings show a lower late-century
within-model density than their own historical reference on common spatial
support, and the late-century decline is larger under SSP5-8.5 than SSP1-2.6
for both. Their near- and mid-century paths differ substantially, however, and
the scenario spread is much smaller than the ecosystem-model spread in those
periods. This is useful structural-uncertainty evidence for the biophysical
benchmark only. Neither SSP path is a baseline/one-ton-pulse counterfactual,
and `tc` density is not observed catch, producer surplus, or consumer surplus.

The machine-audited cross-matrix sign check retains the forcing/model as the
comparison unit and never averages absolute density levels. Seven of eight
near-century trajectories, all eight mid-century trajectories, and all eight
late-century trajectories are below their own historical reference. SSP5-8.5
is more negative than SSP1-2.6 in two of four near-century comparisons and all
four mid- and late-century comparisons. These counts show where the frozen
scenario matrix agrees; they are not uncertainty probabilities and do not
resolve the missing observed-catch, marginal-pulse, or welfare layers.

The frozen configurations are the four
`config/fishmip_scenario_benchmark_*ssp*_v1.toml` files; the executable is
`scripts/evaluate_fishmip_scenario_benchmark.py`. The machine-readable real
outputs remain under ignored raw storage beside the 12 validated NetCDF
files. Synthetic tests cover exact model membership, differing finite masks,
common-support preservation, the two ecosystem-model calendars, annual
coverage, known relative changes, complete forcing/scenario/model membership,
and rejection of support, reference, or nonfinite-result drift.
