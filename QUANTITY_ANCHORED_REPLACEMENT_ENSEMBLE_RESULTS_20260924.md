# Central 26-model anchored agriculture replacement

## Result

All 26 registered climate-model paths were run through the paired GIVE
agriculture replacement under the central market case, fixed adaptation,
uncapped response tail, and 0.000025 GtC pulse. The replacement retains exact
MooreAg baseline regional damage levels, removes the legacy Agriculture
component, and inserts the external precipitation increment as the only
marginal agriculture response.

| Ramsey schedule | Mean | Median | Minimum | Maximum | Negative / 26 |
|---:|---:|---:|---:|---:|---:|
| 1.5% | -$0.008830 | -$0.009179 | -$0.014827 | $0.004581 | 25 |
| 2.0% | -$0.006102 | -$0.006343 | -$0.010246 | $0.003166 | 25 |
| 2.5% | -$0.004543 | -$0.004723 | -$0.007629 | $0.002357 | 25 |
| 3.0% | -$0.003590 | -$0.003733 | -$0.006029 | $0.001863 | 25 |

Values are 2020 USD per tCO2. Negative values denote a modeled benefit.

## Independent validation

- Baseline agriculture damage and global net consumption per capita reproduce
  standard GIVE exactly for every run.
- The graph audit removes the legacy Agriculture component and requires one
  replacement producer of agriculture damages.
- The maximum regional increment error is `4.54e-13` billion 2005 USD and the
  maximum annual global aggregation cancellation error is $0.00822.
- All 104 model-by-discount results match the independently constructed
  standard-baseline diagnostic inside run-specific propagated numerical bounds;
  the maximum absolute disagreement is `5.38e-8` 2005 USD per tCO2.
- The sequential job completed in 78.8 seconds and peaked at 1.39 GB sampled
  process-group RSS under a 3 GB ceiling.

## Interpretation boundary

This is a preliminary paired GIVE SCC estimate for one narrow mechanism:
climate-driven changes in annual rainfall quantity affecting global maize,
translated through the central constant-elasticity market specification. It is
not a complete precipitation-agriculture SCC. It fixes within-season rainfall
shares and omits timing, dry spells and drought, temperature, other crops,
irrigation adaptation, trade, storage, and adaptation costs. The small negative
mean must not be interpreted as evidence that total precipitation change is
beneficial.

Market, adaptation, response-tail, and empirical-response uncertainty still
need paired execution. The anchored baseline intentionally preserves MooreAg's
level to avoid inventing an unsupported new baseline and to prevent double
counting its marginal response.
