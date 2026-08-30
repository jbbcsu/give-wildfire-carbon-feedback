# FishMIP control-adjusted spatial consensus

## Registered comparison

This audit uses the exact 40,398 grid cells with finite `tc` values in all 20
checksum-validated FishMIP files: BOATS and EcoOcean, GFDL-ESM4 and
IPSL-CM6A-LR, forced historical, preindustrial-control historical and future,
and SSP1-2.6 and SSP5-8.5 future experiments. The reference decade is
2005--2014 and the future decade is 2081--2090.

For each forcing/model/scenario cell, the spatial diagnostic is

`(forced future - forced historical) / forced global historical mean`

minus

`(control future - control historical) / control global historical mean`.

Both global means use the same exact 20-file support and cosine-latitude area
weights. The area-weighted mean of the cell diagnostic must reproduce the
difference between the forced and control global relative changes to machine
precision. This normalization permits genuine zero-density cells without
inventing a local denominator and never averages incompatible absolute model
levels.

## Results

On the exact common support, the area-weighted share with a negative adjusted
cell change ranges from 41.85% to 63.89% across the four SSP1-2.6 trajectories
and from 53.72% to 76.53% across the four SSP5-8.5 trajectories. At least three
of four trajectories are negative over 42.22% of weighted area under SSP1-2.6
and 56.54% under SSP5-8.5. Strict unanimity is much lower: 13.15% and 26.35%,
respectively.

The spatial result therefore reinforces the global matrix's central warning.
Control adjustment leaves substantial model and geographic disagreement;
even the all-negative late-century SSP5-8.5 global means do not imply a
universal local sign.

## Evidence boundary

The control historical/future join changes social forcing from `histsoc` to
`2015soc-from-histsoc`. The adjustment is consequently a structural
sensitivity, not causal attribution or a pure autonomous-drift correction.
The audit uses modeled catch density rather than observed catch and supplies
no country/EEZ allocation, matched CO2 pulse, consumer or producer welfare,
damage function, probability weight, or SCC input.

The machine-readable receipt is
`data/provenance/fishmip_control_adjusted_spatial_consensus_20260830.json` and
the executable is
`scripts/evaluate_fishmip_control_adjusted_spatial_consensus.py`.
