# Full registered structural paired GIVE ensemble

## Result

The complete registered market × adaptation × response-tail design has now
been executed through the anchored GIVE agriculture replacement. It contains
936 paired paths and 3,744 model/specification/discount SCC values: 26 climate
models, six market specifications, three adaptation scenarios, two tail rules,
and four Ramsey schedules.

At the 2% schedule, averaging equally across climate models, adaptation cases,
and tail rules within each market specification:

| Elasticity pair | Yield-to-supply mapping | Mean | Median | Minimum | Maximum | Negative / 156 |
|---|---|---:|---:|---:|---:|---:|
| 0.08 / 0.02 | Horizontal output | -$0.006673 | -$0.006789 | -$0.011306 | $0.003225 | 150 |
| 0.08 / 0.02 | Fixed input cost | -$0.007206 | -$0.007332 | -$0.012211 | $0.003482 | 150 |
| 0.10 / 0.04 | Horizontal output | -$0.006551 | -$0.006666 | -$0.011101 | $0.003166 | 150 |
| 0.10 / 0.04 | Fixed input cost | -$0.007206 | -$0.007332 | -$0.012211 | $0.003482 | 150 |
| 0.50 / 0.06 | Horizontal output | -$0.004804 | -$0.004888 | -$0.008141 | $0.002322 | 150 |
| 0.50 / 0.06 | Fixed input cost | -$0.007206 | -$0.007332 | -$0.012211 | $0.003482 | 150 |

Values are 2020 USD per tCO2. The nearly identical fixed-input-cost values
across elasticity pairs are a numerical result of the registered small-pulse
formulations, not an assumption that elasticity never matters.

## Engineering and validation

Alternative market paths were rebuilt at the country level and mapped to GIVE
regions; no global scalar was used to infer regional incidence. Each of the
five new regional datasets sums to every registered global annual market path
within `2e-12` billion 2005 USD. The central regional path retains its earlier
independent row-level validation.

Every paired run preserves baseline MooreAg agriculture damage and per-capita
consumption exactly, removes the legacy marginal response, and installs one
replacement producer. All 3,744 values match the independently reconstructed
external diagnostic exactly at the stored precision. Maximum paired numerical
disagreement is `6.37e-8` 2005 USD per tCO2, below a maximum propagated bound
of `7.98e-6`. Peak sampled process-group memory was 2.20 GB under a 3 GB cap.

The alternative regional allocations are currently validated by the builder's
country-to-region/global reconciliation plus the paired aggregate check, not a
second row-by-row implementation. A separate independent regional-incidence
audit remains desirable before using regional results distributionally; it does
not affect the global sectoral SCC sums reported here.

## Interpretation boundary

This completes paired execution of the registered structural choices for the
annual global-maize rainfall-quantity channel. The cells are a balanced design,
not a probability distribution. Empirical coefficient uncertainty, rainfall
timing, drought, temperature, other crops, irrigation adaptation, trade,
storage, and adaptation costs remain omitted. The small negative estimates
must not be generalized to total precipitation-driven agricultural damages.
