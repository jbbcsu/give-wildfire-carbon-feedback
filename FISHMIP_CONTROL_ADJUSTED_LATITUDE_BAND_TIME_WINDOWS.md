# FishMIP control-adjusted latitude-band time windows

## Question and fixed design

This outcome-free extension asks whether the latitude-band magnitudes in the
frozen 20-file FishMIP matrix persist across the fixed 2021--2030, 2041--2050,
and 2081--2090 windows. Each BOATS/EcoOcean x GFDL-ESM4/IPSL-CM6A-LR
trajectory retains its own historical scale and matched preindustrial-control
change. The support intersection is common to all files and windows. Absolute
model levels are never averaged.

## Results

Under SSP1-2.6, only the southern high-latitude band has all four trajectory
means below zero in every window. The southern midlatitude count is 3/4, 2/4,
and 4/4; the tropics and northern midlatitudes remain 3/4 in every window; and
the northern high-latitude count is 3/4, 1/4, and 3/4.

Under SSP5-8.5, the southern midlatitudes reach 4/4 negative means in
2041--2050 and remain 4/4 in 2081--2090. The tropics and northern midlatitudes
reach 4/4 only in 2081--2090. The southern high-latitude band is 4/4, 4/4,
then 3/4, while the northern high-latitude band is 3/4, 1/4, then 3/4. Thus
late-century unanimity broadens across the three central bands under SSP5-8.5
but is neither global nor monotone at high latitudes.

## Evidence boundary

This is a structural scenario/model sensitivity. The four trajectories are
not a probability sample, latitude bands are not countries or EEZs, and the
audit does not estimate observed catch, a matched CO2 pulse, welfare, damages,
or an SCC value. Allocation remains blocked on authorized EEZ/High Seas source
acquisition and review.

The executable is
`scripts/evaluate_fishmip_control_adjusted_latitude_band_time_windows.py`, the
synthetic failure suite is
`test/test_fishmip_control_adjusted_latitude_band_time_windows.py`, and the
hash-bound result is
`data/provenance/fishmip_control_adjusted_latitude_band_time_windows_20260901.json`.
