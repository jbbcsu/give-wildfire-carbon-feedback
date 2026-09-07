# Published elasticity sensitivity — hypothetical, not empirical damages

September 7, 2026. All36registered hypothetical states completed. The exercise
tests an economic translation after independently derived accounting; it does
not estimate crop losses, dollars or SCC.

## Source and scope

[Roberts and Schlenker (2013), AER](https://www.aeaweb.org/articles?id=10.1257/aer.103.6.2265)
provides a published market-elasticity candidate. Its
[publisher appendix](https://www.aeaweb.org/articles/materials/2408), TableA8
(printedA26, PDFindex26), reports six IV/3SLS specifications using the FAS
alternative data, not the main FAO baseline. We retain all six rounded point
estimates and reported standard errors. Publisher PDF text was inspected;
visual page verification failed because the screenshot service returned a
cache miss. The source config records that limitation explicitly.

The [replication package](https://doi.org/10.3886/E112674V1) is identified, but its
license contents and executable code have not been verified or used. This is
not a reproduction of the published ethanol experiment or its full economic
model. No joint parameter covariance is available in this implementation;
standard errors are not used as independent draws, and specification ranges
are not confidence intervals.

## Independent normalized calculation

Use Qs=exp(s)P^es, Qd=P^-ed with positive es and ed; baseline market value R=1.
Supply shifts are either s=log(a) (horizontal-output convention) or
s=(1+es)log(a) (fixed-input-cost convention). Neither mapping is empirically
selected. The protocol froze a=0.99,1,1.01 and all six source columns before
calculation. No observed yield shock enters these equations.

For the **hypothetical1% productivity loss**:

| Supply-shift convention | Price increase | Total-surplus loss as % of R |
|---|---:|---:|
| Horizontal output | 5.025–6.930% | 0.917–0.933% |
| Fixed input cost | 5.598–7.786% | 1.030–1.042% |

These ranges show mapping/specification sensitivity, not a climate damage
estimate or probability interval. Producer/consumer changes are calculated
jointly; price increases must not be counted as a second loss on top of total
surplus. Closed-market aggregation omits country/crop substitution, trade and
distributional allocation. Actual baseline values, coverage, adaptation costs,
validated joint yield changes and a marginal emissions path are still missing.

## Verification and reproduction

`scripts/test_normalized_welfare_sensitivity.py`: three synthetic tests pass.
The first test run exposed a wrapper error: the derivative returned by
`equilibrium` is evaluated at its zero starting state, not the shifted state.
The wrapper now explicitly calls `paired_surplus(market, shift, 0)` for the
local derivative; the preexisting accounting core was unchanged. Failed logs
are retained as `outputs/welfare_normalized_tests_20260907.log`; the corrected
run is `outputs/welfare_normalized_tests_v2_20260907.log`. No empirical
calculation preceded that fix.

`scripts/evaluate_normalized_welfare_sensitivity.py --out NEW_RESULT.json`
checks market clearing and total=consumer+producer surplus for36states.
All six reciprocal-elasticity multipliers agree with the publisher values
within the intervals implied by printed rounding. Local analytic derivatives
agree with centered finite differences; maximum absolute residual9.37e-12.
All36states, source/code/protocol hashes and explicit non-empirical flags are
in `data/provenance/welfare_normalized_sensitivity_20260907.json`.

The calculation completed in0.242seconds, with6.19MiB sampled process-group
RSS under a512MiB monitor. Such a short run can have unsampled higher peaks;
the monitor is not a kernel memory cap. These checks validate implementation,
not the transferability of published parameters or the missing economic and
climate assumptions.
