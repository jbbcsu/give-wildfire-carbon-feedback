# FishMIP structural-dominance stability

Status: preregistered and evaluated descriptive sensitivity; not probability weighting,
variance decomposition, causal forced response, allocation, welfare, damage,
or SCC evidence.

The preceding two-by-two audit identifies whether the climate-forcing or
ecosystem-model contrast has larger root-mean-square magnitude in each of 30
fixed scenario/window/latitude cells. This extension asks whether that label
is stable across the two scenarios and three time windows, and whether the
larger contrast is materially separated rather than nearly tied.

Before running the real receipt, material dominance is fixed at a
larger-to-smaller RMS ratio of at least `1.25`. The audit reports all 30 ratios,
the number of near ties, agreement of the larger axis across scenarios in each
of 15 window/band pairs, and agreement across all three windows in each of ten
scenario/band groups. It assigns no probabilities to the four structures and
does not interpret the ratio as a variance share.

The executable is
`scripts/evaluate_fishmip_structural_dominance_stability.py`; its result will
be bound to the existing structural-contrast receipt in
`data/provenance/fishmip_structural_dominance_stability_20260901.json`.

## Result

Only 15/30 cells meet the predeclared 1.25 material-dominance ratio; the other
15 are near ties. The larger structural axis agrees across SSP1-2.6 and
SSP5-8.5 in 13/15 matched window/latitude pairs, but agrees across all three
windows in only 3/10 scenario/latitude groups. Of the materially separated
cells, 13 favor the climate-forcing contrast and two favor the ecosystem-model
contrast. Thus the aggregate 18/12 winner count masks many near ties and
substantial temporal instability. Neither structural dimension can be dropped
or assigned probability weight from this evidence.
