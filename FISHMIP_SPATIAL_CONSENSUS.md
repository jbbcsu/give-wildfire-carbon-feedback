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
