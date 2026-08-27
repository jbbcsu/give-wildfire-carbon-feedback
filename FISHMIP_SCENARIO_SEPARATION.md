# FishMIP scenario-separation audit

Status: validated biophysical scenario diagnostic only; not observed catch, a
matched carbon pulse, welfare, a damage function, or an SCC input.

This audit compares annual SSP5-8.5 and SSP1-2.6 total-catch density within
each climate forcing and ecosystem model. It uses the checksum-validated
BOATS/EcoOcean × GFDL-ESM4/IPSL-CM6A-LR files and the same forcing-specific
common spatial support as the registered scenario matrix. Each annual
difference is divided by that forcing/model's own 2005--2014 historical mean;
absolute BOATS and EcoOcean levels are never averaged.

The executable reports the number of years in 2015--2100 for which SSP5-8.5
is below SSP1-2.6, the longest consecutive run, the first ten-year persistent
run if one exists, and predeclared near-, mid-, and late-century mean
differences. Every period result must reproduce the corresponding difference
between the independently validated scenario-matrix entries.

In the hash-bound real audit, SSP5-8.5 is lower than SSP1-2.6 in 64/86 annual
GFDL/BOATS values, 82/86 GFDL/EcoOcean values, 69/86 IPSL/BOATS values, and
67/86 IPSL/EcoOcean values. The first ten-year persistent lower run begins in
2044, 2021, 2052, and 2051, respectively. Near-century separation is mixed
and small: the normalized SSP5-8.5-minus-SSP1-2.6 difference ranges from
-0.91 to +0.42 percentage points of the same forcing/model historical mean.
All four late-century differences are negative, from -7.63 to -6.24
percentage points. This convergence is descriptive scenario evidence only;
it does not supply a marginal carbon-pulse response or welfare mapping.

Reproduce with:

```bash
/Users/jbb/Dropbox/GIVE/precipitation_scc/.venv/bin/python \
  test/test_fishmip_scenario_separation.py

/Users/jbb/Dropbox/GIVE/precipitation_scc/.venv/bin/python \
  scripts/evaluate_fishmip_scenario_separation.py \
  --plan data/provenance/fishmip_isimip3b_tc_acquisition_plan.csv \
  --matrix data/provenance/fishmip_scenario_benchmark_matrix_20260826.json \
  --raw-root data/raw/fishmip \
  --out data/provenance/fishmip_scenario_separation_20260827.json
```
