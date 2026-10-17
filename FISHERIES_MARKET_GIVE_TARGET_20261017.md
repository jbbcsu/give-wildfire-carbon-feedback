# Fisheries market-only GIVE target

## Finished result

The strongest currently defensible fast product is a **non-additive external
SCC sensitivity**, not an integrated GIVE sector. The published Blue-SCC
market-only distribution can be mechanically aligned to GIVE's 2020 pulse
year, per-tCO2 denominator, and exact 2005-to-2020 price-level convention.
After the tiny price-basis correction, the market-only sensitivity is:

| Published case | 2020 USD/tCO2 |
|---|---:|
| Monte Carlo 5th percentile | 0.0376075 |
| Monte Carlo median | 0.0617078 |
| Monte Carlo 95th percentile | 0.0962528 |
| Deterministic | 0.0548240 |

The source uses a one-million-tCO2 pulse in 2020 and divides by one million;
the GIVE replication uses a `0.0001 GtC` pulse in 2020 and converts carbon to
CO2 before its per-ton denominator. Thus both outputs are dollars per physical
tCO2. Different pulse magnitudes need no mechanical scaling after
normalization, but the public Blue-SCC artifacts contain no decreasing-pulse
convergence test, so local linearity is not independently verified.

## Why it cannot be added to GIVE yet

Currency and pulse units are not the limiting problems. The terminal published
SCC cannot be rediscounted: its deterministic parameters are PRTP 1.5% and
eta 1.45, while GIVE's 2% near-term specification uses PRTP 0.19746% and eta
1.244459. GIVE's PRTP lies below the published Monte Carlo support of 1--2%,
so reweighting or extrapolating those terminal draws would be indefensible.
The published release supplies no annual market-damage path from which to
recompute GIVE discounting.

More importantly, the source market coefficient is a GDP-fraction response
derived from projected profits after regional output multipliers. It is not
identified direct consumer plus producer surplus. Inserting it into GIVE's
consumption damages would risk counting indirect/induced market effects that
also appear in other damage sectors. The interface therefore fails closed
with `additive_eligible=false`.

Nutrition remains entirely outside this market sensitivity and is retained
only as a non-additive literature bound because its mortality pathway overlaps
GIVE mortality damages.

## What would open the integration gate

Either of these evidence packages is sufficient for the next review:

1. matched annual baseline/pulse direct consumer- and producer-surplus paths,
   permitting GIVE-consistent discounting and draw coupling; or
2. annual multiplier-free direct profit paths plus evidence that the profit
   measure equals producer surplus, an independently estimated consumer-
   surplus component, and a documented overlap subtraction.

The executable target record verifies the exact public source commits, source
hashes, pulse and price conventions, GIVE hashes and parameters, and the
benchmark receipt before emitting any values. It copies no source rows and
does not modify GIVE.
