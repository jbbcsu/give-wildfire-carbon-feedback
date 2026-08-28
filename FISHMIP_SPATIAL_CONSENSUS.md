# FishMIP cross-matrix spatial sign consensus

## Result and boundary

The checksum-bound audit intersects the exact late-century FishMIP support
across both climate forcings (GFDL-ESM4 and IPSL-CM6A-LR), both ecosystem
models (BOATS and EcoOcean), and historical, SSP1-2.6, and SSP5-8.5. It retains
40,398 one-degree ocean cells. Each model/forcing trajectory is compared with
its own 2005--2014 reference; absolute model levels are never averaged.

For 2081--2090, all four trajectories are lower over 53.10% of cosine-
latitude-weighted ocean area under SSP1-2.6 and 54.60% under SSP5-8.5. At least
three of four are lower over 88.48% and 85.75%, respectively. Unweighted
unanimous-lower shares are 48.27% and 46.78%. The presence of increases in at
least one trajectory over 45.35% and 44.38% of weighted area means the result
is broad agreement, not universal local decline.

This is a biophysical sign-consensus diagnostic for scenario catch density.
It is not observed catch, a matched carbon pulse, consumer or producer
welfare, damages, or an SCC input.

## Reproduction

```bash
../precipitation_scc/.venv/bin/python \
  scripts/evaluate_fishmip_spatial_consensus.py \
  --plan data/provenance/fishmip_isimip3b_tc_acquisition_plan.csv \
  --raw-root data/raw/fishmip \
  --out data/provenance/fishmip_spatial_consensus_20260827.json
```

The synthetic sign/support failures are exercised by
`test/test_fishmip_spatial_consensus.py`.

## Fixed-decade robustness extension

The companion audit repeats the same sign-consensus calculation over three
predeclared, nonoverlapping future decades (2071--2080, 2081--2090, and
2091--2100), always relative to the same 2005--2014 within-trajectory
reference and using one common finite support across all 12 input files and
all three future windows. The exact intersection retains 40,398 cells. The
cosine-latitude-weighted unanimous-lower shares are 49.98%, 53.10%, and
49.99% under SSP1-2.6 and 55.01%, 54.60%, and 52.48% under SSP5-8.5 across
the three successive decades. At-least-three-lower shares remain between
84.39% and 88.48% in all six scenario-window cells. The result therefore
supports broad cross-model sign agreement while showing that a strict
majority-unanimous threshold is not stable for SSP1-2.6. It is reproduced
with:

```bash
../precipitation_scc/.venv/bin/python \
  scripts/evaluate_fishmip_spatial_consensus_time_windows.py \
  --plan data/provenance/fishmip_isimip3b_tc_acquisition_plan.csv \
  --raw-root data/raw/fishmip \
  --out data/provenance/fishmip_spatial_consensus_time_windows_20260828.json
```

This extension tests temporal robustness only. It retains the same
biophysical-only boundary and cannot be interpreted as observed catch,
welfare, a matched carbon pulse, damages, or SCC evidence.

## Fixed latitude-band heterogeneity

A second preregistered robustness view partitions the exact 2091--2100 common
support into five exhaustive latitude bands: south of 40 S, 40--20 S,
20 S--20 N, 20--40 N, and north of 40 N. At least three of four trajectories
are lower over 74.52%--94.00% of weighted band area under SSP1-2.6 and
64.77%--95.97% under SSP5-8.5. Strict unanimity is more heterogeneous:
38.30%--63.30% for SSP1-2.6 and 37.38%--66.10% for SSP5-8.5. The tropical
band has the strongest SSP5-8.5 at-least-three consensus (95.97%), while the
northern high-latitude band has the weakest (64.77%). This prevents the global
consensus share from being read as spatially uniform.

The five bands conserve all 40,398 common-support cells and the full cosine-
weighted support. They are not countries, EEZs, markets, or incidence regions,
so the result does not supply the country allocation required by the welfare
interface. Reproduce it with:

```bash
../precipitation_scc/.venv/bin/python \
  scripts/evaluate_fishmip_latitude_band_consensus.py \
  --plan data/provenance/fishmip_isimip3b_tc_acquisition_plan.csv \
  --raw-root data/raw/fishmip \
  --out data/provenance/fishmip_latitude_band_consensus_20260828.json
```
