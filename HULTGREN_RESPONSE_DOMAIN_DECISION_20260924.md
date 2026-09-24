# Decision required before global maize monetization

## Evidence

The published Hultgren maize response gives negative value-weighted mean-log
precipitation responses in all five ESMs. On unrestricted future weather,
however, cell-first exponentiation produces positive fixed-price aggregate
output changes in four ESMs because a small number of extrapolated positive
cell responses dominate the level sum. Moderator-only support screens do not
remove the problem.

A post hoc joint weather screen does:

| Weather application domain | Value retained across ESMs | Negative cell-first aggregate | Mean-log sign stability |
|---|---:|---:|---:|
| Unrestricted | 100% | 1 of 5 | 5 of 5 negative |
| Author minimum--maximum | 80.4%--99.0% | 5 of 5 | 5 of 5 negative |
| Author p01--p99 | 6.3%--51.8% | 1 of 5 | 2 of 5 negative |

The p01--p99 restriction is too selective to represent global maize exposure.
The unrestricted calculation fails the level-aggregation plausibility gate.

## Recommended decision

Use the author minimum--maximum joint weather domain as a **bounded-support
sensitivity and interim monetization benchmark**, not yet as the final primary
specification. Report model-specific retained baseline value and do not scale
the supported result to excluded cells. In parallel, inspect the published
application code or obtain author clarification about their future-weather
extrapolation, capping, or support rule. Promote the boundary to primary only
if it matches a published rule or survives a preregistered comparison with a
smooth bounded-response alternative.

## Alternatives

1. Keep unrestricted extrapolation. Rejected as an interim monetary route
   because its aggregate level result is dominated by implausible positive
   tails.
2. Hard-cap cell yield changes. Not recommended without a literature-based or
   preregistered cap; the threshold would directly determine damages.
3. Use p01--p99 support. Rejected as a global benchmark because coverage is
   low and strongly model-dependent.
4. Fit a new regularized global response. Scientifically attractive, but it
   requires a separate empirical design and does not solve the immediate
   published-response benchmark.

No current option authorizes a GIVE SCC result. The next monetary calculation
must also specify prices/market welfare, other crops, coverage, adaptation
costs, and a marginal emissions-pulse climate path.
