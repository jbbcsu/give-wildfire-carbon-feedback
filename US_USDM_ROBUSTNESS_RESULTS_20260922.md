# U.S. drought benchmark: state robustness (calendar-year sensitivity)

**Correction notice:** This file evaluates the superseded January--December
timing sensitivity. The published design uses October of the preceding year
through September of the harvest year. Corrected results are reported in
`US_USDM_OCTSEP_RESULTS_20260922.md`; this file is retained unchanged otherwise
for auditability.

**Status:** completed, independently checked historical sensitivity. These
results are not causal estimates, global response coefficients, damages,
future drought projections, or SCC inputs.

## Question

The weather-controlled benchmark leaves negative D1--D4 associations in both
dryland crops. This sensitivity tests whether those signs depend on any single
state and whether inference is materially different when clustering by state
rather than county. It uses the unchanged common panel and specification.

## Results

Every dryland D1--D4 coefficient retains its negative sign in every eligible
leave-one-state-out refit. The deletion ranges in log points per equivalent
week are:

| Crop | D1 | D2 | D3 | D4 |
|---|---:|---:|---:|---:|
| Corn, dryland | -0.001616 to -0.000925 | -0.003928 to -0.002695 | -0.002857 to -0.001016 | -0.006153 to -0.003064 |
| Soybean, dryland | -0.003288 to -0.001757 | -0.004023 to -0.002912 | -0.002570 to -0.000933 | -0.008345 to -0.004450 |

Thus, the residual dryland sign pattern is not created by one state. That is a
coefficient-stability result, not proof of causality or national homogeneity.
The state producing the largest absolute change varies by term; Missouri,
Virginia, South Carolina, and Texas are the respective corn D1--D4 maxima,
while North Carolina is the maximum for soybean D1--D3 and Tennessee for D4.

State-cluster CR1 uncertainty with a `G-1` Student-t reference is wider than the
registered county-cluster uncertainty for several terms:

| Crop/support | D0 p | D1 p | D2 p | D3 p | D4 p |
|---|---:|---:|---:|---:|---:|
| Corn, dryland | .755 | .140 | .004 | .335 | .091 |
| Corn, irrigated | .907 | .844 | .710 | .865 | .006 |
| Soybean, dryland | .430 | .059 | .003 | .282 | .035 |
| Soybean, irrigated | .409 | .566 | .154 | .007 | .433 |

The main qualitative finding survives: D1--D4 dryland point estimates remain
negative and deletion-stable. The evidence is not equally precise across
categories. Under state clustering, D2 is the most robustly distinguished from
zero in both dryland crops; soybean D4 also remains below .05, while corn D4
and soybean D1 are near .10 and corn D1/D3 and soybean D3 are not precise.
Irrigated corn D4 and soybean D3 remain negative and precise; the other
irrigated categories are mixed or imprecise.

## Validation and resource bound

The production refit reproduces the registered full coefficients exactly.
An independent joint sparse-design validator reproduces full coefficients
within `6.65e-09`, state-cluster covariance entries within `2.04e-10`, and
twelve deterministic sentinel state deletions within `7.19e-09`. The complete
four-model deletion exercise takes 33.0 seconds and peaks at 438,648,832 bytes
(about 418 MiB); validation takes 4.36 seconds and peaks at 435,224,576 bytes.
Both remain below the 640 MiB project ceiling.

This sensitivity does not substitute for agricultural-area USDM weighting or
the published spatial-correlation-robust estimator. The publisher confirms a
supplement archive exists, but it was not retrievable through the permitted
download route; no unpublished setting is guessed.
