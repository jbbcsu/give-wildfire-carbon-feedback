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

A subsequent exact-key cross-audit joins these cells to the separately locked
1.25 RMS-ratio dominance classification. Eight of ten metric-disagreement cells
are near ties and two are materially dominant; among the 20 metric-agreement
cells, seven are near ties and 13 are materially dominant. Disagreement is
therefore concentrated among near ties but does not disappear when the fixed
materiality screen is applied. The cross-audit still selects no metric or
probability weight and performs no allocation or welfare calculation.

The next checksum-bound intersection requires both scenarios in a matched
window/latitude pair to pass metric agreement and material dominance. Only
five of fifteen pairs pass in both SSP1-2.6 and SSP5-8.5. All five retain the
same larger axis across scenarios: four climate-forcing and one ecosystem-
model contrast. Ten pairs fail the dual-scenario robustness intersection, so
the subset is not used to select a common metric, discard a structural axis,
or construct probabilities or welfare weights.
