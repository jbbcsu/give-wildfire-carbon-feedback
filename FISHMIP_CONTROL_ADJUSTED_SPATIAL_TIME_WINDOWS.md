# FishMIP control-adjusted spatial time-window robustness

## Registered comparison

This audit extends the exact 20-file control-adjusted spatial diagnostic over
three fixed future decades: 2021--2030, 2041--2050, and 2081--2090. Every
comparison retains the same 40,398 cells with finite total-catch density in
all BOATS and EcoOcean, GFDL-ESM4 and IPSL-CM6A-LR, historical, control,
SSP1-2.6, and SSP5-8.5 files.

For each forcing/model/scenario/window cell, forced and control spatial
changes are separately normalized by their own cosine-weighted 2005--2014
global historical means and then differenced. Absolute model levels are never
averaged. The area-weighted mean of every spatial diagnostic must reproduce
the corresponding global difference in relative changes to machine
precision.

## Results

The area share where at least three of four forcing/model trajectories are
negative rises monotonically across the three registered decades: 34.30%,
38.04%, and 42.22% under SSP1-2.6, and 33.51%, 42.95%, and 56.54% under
SSP5-8.5. Strict-unanimity shares also rise monotonically but remain much
lower: 9.38%, 11.06%, and 13.15% under SSP1-2.6, and 8.11%, 14.55%, and
26.35% under SSP5-8.5.

The late-century geographic decline signal therefore builds gradually in
this frozen matrix rather than being present at the same strength throughout
the century. Even at 2081--2090, unanimity covers only 13.15% of weighted area
under SSP1-2.6 and 26.35% under SSP5-8.5, so model and geographic disagreement
remain material.

## Evidence boundary

The control historical/future join changes social forcing from `histsoc` to
`2015soc-from-histsoc`. These results are structural temporal sensitivities,
not causal forced responses. They use modeled catch density rather than
observed catch and provide no EEZ/country allocation, matched CO2 pulse,
consumer or producer welfare, damage function, probability weights, or SCC
input.

The machine-readable receipt is
`data/provenance/fishmip_control_adjusted_spatial_time_windows_20260830.json`
and the executable is
`scripts/evaluate_fishmip_control_adjusted_spatial_time_windows.py`.
