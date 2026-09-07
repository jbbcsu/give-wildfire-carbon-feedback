# Global historical rainfall and drought associations

Exploratory derived results, September 7, 2026. **Not climate-change damages,
causal responses, rainfed-only estimates, or SCC inputs.**

## Findings

The global common-support panel gives positive fitted rainfall associations
for maize and soybean. Soybean quantity and drought results are sensitive to
allowing unrestricted annual shocks: the wider-block intervals then include
zero. Distribution terms have positive partial associations, but this does
not overturn their small/uncertain incremental out-of-sample performance.
Within-sample association and improvement in held-out prediction are different
questions. The latter remains reported in the September 6–7 benchmarks.

The table uses annual intercepts and 20-degree spatial blocks. Percentages
are transformations of fitted log-yield contrasts, **not** arithmetic-average
yield effects, effects of future climate, or population-weighted global gains.

| Separate moisture model and partial contrast | Maize: fitted % contrast [conditional 95% interval] | Soybean: fitted % contrast [conditional 95% interval] |
|---|---:|---:|
| Quantity: +0.1 weighted log-rain index | 0.658 [0.285, 1.032] | 0.420 [-0.041, 0.884] |
| Quantity + distribution: same rain-index shift | 0.746 [0.363, 1.131] | 0.703 [0.141, 1.269] |
| Quantity + distribution: stage-3 to stage-2 share shift of 0.1 | 1.050 [0.480, 1.624] | 1.282 [0.402, 2.169] |
| Seasonal scPDSI: +1 index unit | 1.389 [0.449, 2.338] | 0.648 [-0.005, 1.305] |
| Stage scPDSI: +1 index unit in all three stages | 1.363 [0.425, 2.310] | 0.599 [-0.078, 1.280] |

The quantity index is fixed-MIRCA-weighted log(1+seasonal precipitation/mm),
formed separately in the two calendar regimes before weighting. Its +0.1
shift multiplies (1+rainfall/mm) by exp(0.1) in both regimes: it is NOT exactly
10% more rainfall, and NOT log of mean rainfall. Timing holds the included
controls fixed formally; this is not necessarily a realizable daily-weather
perturbation. Higher scPDSI means a wetter index value, not a universal drought
threshold crossing. Moisture families are alternatives, never summed.

With the earlier quadratic end-year controls instead, the quantity contrast
is 0.681% [0.306, 1.057] for maize and 0.585% [0.125, 1.048] for soybean;
seasonal-scPDSI contrasts are 1.488% [0.531, 2.456] and 1.012%
[0.240, 1.791]. All model/time-control/block variants are retained, not only
the more favorable values. No model is selected by an interval excluding zero.

## Support and uncertainty

Differences end in 1983–2010: 404,671 maize and 166,870 soybean grid-year pairs.
These equal-weight counts match the existing training support exactly. The
2012–2016 terminal outcomes are not used here. A GDHY yield appears once per
crop/cell/year; irrigation is a fixed exposure-basis allocation, not separate
observed irrigated/rainfed yields. There are 127/56 crop-specific 10-degree
blocks and 47/28 20-degree blocks (maize/soy). Parameter counts and scaled
Gram condition numbers are retained with each result; all designs pass.

Intervals use normal CR1 cluster-score covariance conditional on a fitted
specification. All years within a geographic block are grouped. The 20-degree
soybean calculation has only 28 blocks; normal inference may be optimistic.
Neither block choice guarantees independent GDHY source data, removes
cross-block climate dependence, nor addresses omitted drivers, adaptation,
measurement error, selection, or specification-search uncertainty. Simple
linear heat controls are not a validated nonlinear causal specification.

## Execution and reproduction

Protocol: `GLOBAL_HISTORICAL_ASSOCIATION_PROTOCOL_20260907.md`.
Implementation: `scripts/global_historical_moisture_associations.py`.
Accepted output:
`data/provenance/global_historical_moisture_associations_20260907.v2.json`.
This contains 16 fits, each with two cluster-covariance variants (32 records).
Code/protocol, input registry, all six source tables and assembly receipts are
hash-bound. Run the companion test script first, then the implementation with
`--out` pointing to a new JSON file; both are run under `run_bounded_job.py`.

Four synthetic tests verify direct-OLS/CR1 agreement, singular/few-cluster
rejection, exclusion of terminal years, and contrasts/year design. Strict
floating-point error handling is enabled. Post-run checks confirm all 32
records complete, original training counts, current code/protocol hashes,
and invariant point estimates under the two cluster definitions.

The initial numerical run failed on matrix-vector floating-point exceptions
in the annual-intercept models; it is not an accepted result. That failure
record remains at the same output name without `.v2`. The algebraically
equivalent explicit contraction fixed this path without changing inputs,
specifications, or thresholds; strict tests and all fits then passed.
The final real run took 14.02 seconds and peaked at 434,208,768 bytes
(414.09 MiB) of sampled process-group RSS. Tests peaked at 81.67 MiB.
Both used the authorized 4 GiB ceiling, single-thread numerical libraries,
and a starting-free-space-minus-64-MiB disk floor. No data were downloaded.
