# FishMIP persistent spatial signs by latitude band

## Registered comparison

This audit partitions the existing same-cell persistence test into the five
fixed, exhaustive latitude bands used by the earlier end-century consensus
audit: south of 40 S, 40--20 S, 20 S--20 N, 20--40 N, and north of 40 N. A
forcing/ecosystem-model trajectory is persistently lower at a cell only when
its normalized forced-minus-control change is strictly negative in all three
registered windows (2021--2030, 2041--2050, and 2081--2090).

The calculation retains the exact 40,398-cell intersection across all 20
frozen FishMIP files. Cosine-latitude weights are normalized separately inside
each band, and band support counts and global-support weights reconcile to the
full common support.

## Results

Persistent agreement from at least three of four trajectories is spatially
heterogeneous. Under SSP1-2.6, the area-weighted share is 12.01% south of
40 S, 14.07% at 40--20 S, 15.68% in the tropics, 27.68% at 20--40 N, and
8.89% north of 40 N. Under SSP5-8.5, the corresponding shares are 9.61%,
20.69%, 22.13%, 23.75%, and 8.76%.

Persistent unanimity is lower in every band. It ranges from 0.60% to 11.06%
under SSP1-2.6 and from 0.99% to 8.57% under SSP5-8.5. Thus the global
persistence shares do not describe a spatially uniform pattern, and neither
scenario has the same band ordering.

## Evidence boundary and reproduction

The historical/future control join changes social forcing from `histsoc` to
`2015soc-from-histsoc`; this remains a structural sensitivity rather than a
causal forced response. It uses modeled total-catch density, not observed
catch, and supplies no EEZ/country allocation, matched carbon pulse, welfare,
probability weights, damages, or SCC input.

The machine-readable receipt is
`data/provenance/fishmip_control_adjusted_spatial_persistence_latitude_bands_20260831.json`.
The executable and synthetic gates are
`scripts/evaluate_fishmip_control_adjusted_spatial_persistence_latitude_bands.py`
and
`test/test_fishmip_control_adjusted_spatial_persistence_latitude_bands.py`.
