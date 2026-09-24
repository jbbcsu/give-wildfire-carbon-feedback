# Paired adaptation-by-tail agriculture replacement

## Result

The anchored GIVE replacement was executed for all 26 climate models, three
registered adaptation scenarios, and two response-tail rules at the smallest
converged pulse and central market specification. This gives 156 paired paths
and 624 model-by-discount SCC values.

At the 2% Ramsey schedule:

| Adaptation | Tail rule | Mean | Median | Minimum | Maximum |
|---|---|---:|---:|---:|---:|
| Fixed | Uncapped | -$0.006102 | -$0.006343 | -$0.010246 | $0.003166 |
| Fixed | Published-analogue | -$0.006112 | -$0.006351 | -$0.010253 | $0.003035 |
| Trend | Uncapped | -$0.006524 | -$0.006688 | -$0.010637 | $0.001938 |
| Trend | Published-analogue | -$0.006527 | -$0.006756 | -$0.010639 | $0.001829 |
| Upper | Uncapped | -$0.007024 | -$0.007204 | -$0.011101 | $0.000483 |
| Upper | Published-analogue | -$0.007019 | -$0.007198 | -$0.011097 | $0.000399 |

Values are 2020 USD per tCO2. The tail rule has little effect at this scale;
the registered adaptation scenarios shift the mean more visibly. These are
scenario comparisons, not estimated adaptation probabilities.

## Validation

Baseline agriculture damage and per-capita consumption reproduce standard GIVE
exactly in every run. All 624 values join exactly to the independently
constructed diagnostic. The maximum paired-versus-external disagreement is
`6.37e-8` 2005 USD per tCO2 and remains below its propagated numerical bound.
The maximum annual level-plus-increment cancellation error is $0.01039. The
successful sequential job completed in 153 seconds and peaked at 1.83 GB
sampled process-group RSS under a 3 GB ceiling.

## Boundary

This closes paired execution for climate-model, adaptation, and tail choices
within the annual maize rainfall-quantity channel. Market-structure alternatives
remain paired-equivalent diagnostics rather than paired executions. Empirical
coefficient uncertainty and rainfall timing, drought, temperature, other crops,
irrigation adaptation, trade, storage, and adaptation costs remain outside the
estimate.
