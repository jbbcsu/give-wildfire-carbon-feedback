# FishMIP common-support scenario benchmark

Status: validated biophysical scenario diagnostic; not a matched CO2 pulse,
welfare estimate, damage function, or SCC input.

The registered `fishmip_scenario_benchmark_v1` diagnostic uses the four-file
GFDL-ESM4 content smoke without selecting an ecosystem model from its result.
It intersects the time-stable BOATS and EcoOcean finite masks, retaining
41,029 one-degree cells. Within each model it computes the cosine-latitude
weighted monthly mean of `tc` density, averages the 12 months within each year,
and compares three future decades under SSP1-2.6 with the model's own
2005--2014 historical reference. Unsupported cells remain missing; they are
never changed to zero.

| Ecosystem model | 2005--2014 reference (`g m-2`) | 2021--2030 change | 2041--2050 change | 2081--2090 change |
| --- | ---: | ---: | ---: | ---: |
| BOATS | 1.81663044513e-08 | -26.04% | -32.78% | -35.62% |
| EcoOcean | 0.112406880682 | +0.27% | -0.98% | -24.40% |

The absolute density scales differ greatly between the two ecosystem models,
so the diagnostic does not average their levels or treat either level as an
observed catch calibration. Both models show a lower late-century
within-model density than their own historical reference on common spatial
support, but their near- and mid-century paths differ substantially. This is
useful ensemble-disagreement evidence for the biophysical benchmark only.
SSP1-2.6 is a scenario path, not a baseline/one-ton-pulse counterfactual, and
`tc` density is not producer or consumer surplus.

The frozen configuration is
`config/fishmip_scenario_benchmark_v1.toml`; the executable is
`scripts/evaluate_fishmip_scenario_benchmark.py`. The machine-readable real
output remains under ignored raw storage beside the four validated NetCDF
files. Synthetic tests cover exact model membership, differing finite masks,
common-support preservation, the two ecosystem-model calendars, annual
coverage, and known relative changes.
