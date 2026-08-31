# FishMIP control-adjusted spatial sign persistence

## Registered comparison

This audit tightens the fixed-decade spatial robustness check. A cell is
classified as persistently lower for one forcing/ecosystem-model trajectory
only when its normalized forced-minus-control change is strictly negative in
all three registered windows: 2021--2030, 2041--2050, and 2081--2090. The
analysis retains the exact 40,398-cell intersection across all 20 frozen
FishMIP files and never averages absolute model levels.

For each scenario, the audit counts how many of the four forcing/model
trajectories are persistently lower at each cell. This is stricter than
reporting the sign-consensus share separately in each decade because the same
cell and trajectory must retain its negative sign throughout.

## Results

Under SSP1-2.6, 15.34% of cosine-latitude-weighted ocean area has at least
three of four trajectories persistently lower across all three windows, and
only 2.82% has persistent unanimity. Under SSP5-8.5, the corresponding shares
are 17.89% and 3.35%.

Individual persistent-lower shares range from 29.37% to 42.69% under
SSP1-2.6 and from 28.08% to 46.75% under SSP5-8.5. The much smaller
cross-structure agreement shares show that increasing decade-specific sign
consensus does not imply stable agreement on the same locations through time.

## Evidence boundary

The historical/future control join changes social forcing from `histsoc` to
`2015soc-from-histsoc`; the diagnostic is therefore a structural sensitivity,
not a causal forced response. It uses modeled total-catch density, not observed
catch, and supplies no EEZ/country allocation, matched CO2 pulse, consumer or
producer welfare, probability weights, damages, or SCC input.

The machine-readable receipt is
`data/provenance/fishmip_control_adjusted_spatial_persistence_20260830.json`;
the executable and synthetic gates are
`scripts/evaluate_fishmip_control_adjusted_spatial_persistence.py` and
`test/test_fishmip_control_adjusted_spatial_persistence.py`.
