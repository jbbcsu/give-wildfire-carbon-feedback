# Preregistered FishMIP structural-metric robustness audit

Status: evaluated from the frozen input; structural sensitivity only.

The existing exact two-by-two structural audit compares the root-mean-square
(RMS) magnitude of two EcoOcean-minus-BOATS contrasts with two
IPSL-CM6A-LR-minus-GFDL-ESM4 contrasts inside each fixed
scenario/window/latitude cell. This follow-on freezes one non-EEZ robustness
question before evaluation: does the identity of the larger structural axis
change when the two absolute contrasts are summarized by their arithmetic
mean rather than their RMS?

The exact input is
`data/provenance/fishmip_structural_contrast_sensitivity_20260901.json`, SHA-256
`547ecc9a6cb5858dae1d68b3704fd715405cfb97330ddf34600ffddf35c74836`.
The output must contain all 30 scenario-by-window-by-latitude cells, recompute
both metrics from the two signed contrasts, reproduce the source RMS winner,
and report winner agreement without selecting a preferred metric. No material
threshold is introduced. Ties must be explicit.

This audit does not assign model probabilities, estimate variance shares,
identify a causal forced response, allocate catch to countries or EEZs, use
observed catch, construct a matched carbon pulse, or estimate welfare, damages,
or SCC.

## Result

The larger-axis label agrees between RMS and mean absolute magnitude in 20 of
30 fixed cells and changes in 10. RMS labels climate forcing as larger in 18
cells and ecosystem model as larger in 12. Mean absolute magnitude labels
climate forcing as larger in 17 cells, ecosystem model as larger in 5, and
produces 8 exact ties. This dependence on the summary metric reinforces the
requirement to retain both structural dimensions; it does not rank the metrics
or justify probabilistic weights.

The machine-readable receipt is
`data/provenance/fishmip_structural_metric_robustness_20260902.json`. It binds
the frozen source checksum, recomputed cell results, implementation checksum,
closed interpretation gates, and the 20/30 agreement count.
