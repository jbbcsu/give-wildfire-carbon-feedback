# FishMIP spatial change distribution

Status: bounded biophysical scenario diagnostic; not observed catch, a matched
CO2 pulse, welfare, damages, or an SCC input.

The existing FishMIP scenario benchmark reports cosine-latitude-weighted
global mean total-catch-density changes. The spatial audit adds a distinct
question: are the 2081--2090 changes relative to 2005--2014 broadly signed
across the validated common grid, or can a global mean be dominated by a
small set of cells?

`scripts/evaluate_fishmip_spatial_change_distribution.py` uses the exact 12
checksum-pinned historical, SSP1-2.6, and SSP5-8.5 files for BOATS and
EcoOcean under GFDL-ESM4 and IPSL-CM6A-LR. Within each climate forcing it
retains only cells finite in both ecosystem models and all three experiments.
It reports unweighted and cosine-latitude-weighted shares of cells with lower,
higher, or exactly unchanged decadal mean density. Distribution quantiles are
cell changes divided by the same model/forcing common-support historical mean;
absolute BOATS and EcoOcean levels are never averaged.

The executable cross-check requires the area-weighted reference and
late-century changes to reproduce the already validated scenario matrix.
The tracked machine-readable result is
`data/provenance/fishmip_spatial_change_distribution_20260827.json`.

Reproduce with the project environment:

```bash
./.venv/bin/python test/test_fishmip_spatial_change_distribution.py

./.venv/bin/python scripts/evaluate_fishmip_spatial_change_distribution.py \
  --plan data/provenance/fishmip_isimip3b_tc_acquisition_plan.csv \
  --matrix data/provenance/fishmip_scenario_benchmark_matrix_20260826.json \
  --raw-root data/raw/fishmip \
  --out data/provenance/fishmip_spatial_change_distribution_20260827.json
```

Passing this audit does not supply a pulse response or welfare mapping. It
cannot populate the GIVE interface until the separately required ecological,
matched-pulse, surplus, overlap, aggregation, and SCC gates pass.
