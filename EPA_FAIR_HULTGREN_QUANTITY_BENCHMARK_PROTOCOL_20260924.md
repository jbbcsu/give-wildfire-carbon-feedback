# Registered EPA/FAIR-to-Hultgren quantity-only partial-SCC benchmark

## Purpose and status

This protocol defines the shortest defensible route to a **provisional maize
precipitation-quantity partial SCC** using only already validated components:
the published EPA country/model annual-precipitation slopes, the matched
core-GIVE FAIR baseline and pulse temperature paths, the reproduced Hultgren
et al. maize precipitation response, the audited MapSPAM/value inputs, and the
registered GIVE replacement interface. It is a benchmark, not the paper's
primary precipitation-pattern SCC. It deliberately holds within-year rainfall
shares fixed and therefore cannot represent timing, dry spells, extremes, or
drought.

No result is authorized by this protocol alone. Code, independent numerical
validation, shrinking-pulse convergence, support accounting, welfare
sensitivity, and the no-double-count replacement test must all pass before a
number can be labeled a provisional partial SCC.

## Frozen climate link

For country `c`, EPA climate model `m`, year `t`, and FAIR pulse size `p`, use
the validated annual quantity change

`delta_R[c,m,t,p] = beta[c,m] * (T_pulse[t,p] - T_baseline[t])`,

where `beta` is the published EPA annual precipitation slope in
mm yr-1 K-1. Inputs and their hashes remain those frozen in
`EPA_FAIR_ANNUAL_PRECIPITATION_PULSE_PROTOCOL_20260921.md` and its validated
result. Missing country/model slopes remain missing; do not impute them or
replace them with an ensemble mean.

The production calculation must retain the zero pulse and the three validated
positive pulses (`0.0001`, `0.00005`, and `0.000025` GtC). Baseline paths must
be bit-identical across pulse sizes, pulse and baseline must remain identical
through 2020, and normalized damages from the two smallest pulses must meet a
predeclared convergence tolerance before SCC normalization.

## Frozen quantity-only feature transport

Use each retained country-cell's validated baseline Hultgren maize weather
basis and country identity. First construct and independently validate a fixed
country annual-precipitation climatology from the same resident gridded
historical weather product used for the cell basis, aggregated with the EPA
country mask. Let `Rbar0_annual[c]` be that strictly positive country annual
total and `delta_R[c,m,t,p]` the EPA country annual change above. Because EPA
supplies no subnational or monthly pattern, define a uniform proportional
scale:

`scale[c,m,t,p] = 1 + delta_R[c,m,t,p] / Rbar0_annual[c]`.

Apply the same country scale to every represented cell and month in that
country. This maps an annual-total change into crop-season rainfall under the
explicit assumption that every month changes proportionally; it preserves all
baseline within-season shares. Do **not** divide an annual EPA change by a
crop-season total. Reject any country-year-pulse combination with non-finite
inputs or `scale <= 0`; do not cap or repair it. Report sensitivity to the
country aggregation weights because the published EPA slope and the crop-cell
baseline need not use identical spatial weights.

For each cell, update the Hultgren precipitation basis exactly as in the
already validated quantity-path decomposition:

- each of the three phase-linear precipitation sums is multiplied by `scale`;
- each of the three sums of squared monthly precipitation is multiplied by
  `scale^2`;
- crop calendar, long-run precipitation moderator, income, irrigation share,
  and all temperature terms are held at the paired baseline value; and
- only the precipitation component of predicted log yield is evaluated.

This is intentionally a precipitation-quantity partial effect. It must not be
described as the joint effect of climate change, and it may not be added to a
temperature damage estimate unless the final replacement accounting shows
that the terms are mutually exclusive.

## Response, adaptation, and tail rules

Use the hash-pinned reproduced Hultgren maize coefficients and evaluator.
Report the uncapped result and a preregistered published-analogue tail
sensitivity. For the latter, calculate the log-yield response per GtC at the
smallest positive pulse, pool unique country-cell/model/year derivatives, and
freeze its 1st/99th percentile bounds before evaluating any other pulse size.
Apply those derivative bounds consistently across pulse sizes so that the
tail rule cannot mechanically defeat shrinking-pulse convergence. Do not
select a cap using the resulting SCC magnitude.

Report the three registered adaptation scenarios separately:

- **fixed:** no attenuation;
- **trend:** attenuate negative log-yield effects by 0.3% per year after 2020,
  capped at 35%; and
- **upper:** attenuate negative effects by 0.7% per year, capped at 70%.

Positive effects are not amplified or attenuated. Adaptation costs remain
unmodeled, so trend and upper results are sensitivities rather than net
benefits of adaptation.

## Economic and GIVE integration

The primary benchmark uses the independently reconstructed matched-support
common-price maize weights, not the failed FAOSTAT constant-dollar field. Run
the registered national-market elasticities and both yield-to-supply mappings;
the `0.10/0.04` elasticity pair with horizontal-output mapping is the declared
central structural case. Report GDP-deflator-rebased country prices as a named
price-basis sensitivity.

The provisional central benchmark holds real maize production and baseline
value fixed at the audited circa-2000 support. This is a transparent fixed-
baseline exposure calculation, not a forecast of the future maize economy.
Do not silently scale crop value with total GDP. Any time-varying baseline must
be separately registered from a source-pinned crop-production/value pathway,
with its effect reported apart from the fixed-baseline result.

For every climate-model, parameter, and adaptation draw, generate paired
annual baseline and pulse monetary-damage paths through 2300. Pass those paths
through the existing agriculture **replacement** interface: the precipitation
benchmark replaces, and is never stacked on top of, the overlapping existing
GIVE agricultural damage component. Use GIVE's registered currency,
population/income, discounting, pulse normalization, and uncertainty draws
without changing conventions in this benchmark.

## Required validation and reporting

Before reporting a provisional SCC, require all of the following:

1. Exact source hashes and the existing 4,703-pair/184-country EPA support.
2. A complete country-to-cell support ledger, including unmatched production
   and value without renormalizing it away.
3. Zero-pulse and pre-2021 identity for every intermediate feature, yield, and
   damage path.
4. Direct-versus-centered feature-difference agreement on a sentinel sample.
5. Independent reconstruction of country scales, six precipitation-basis
   changes, log-yield effects, annual market damages, and discounted SCC.
6. Normalized convergence of the two smallest positive pulses for features,
   damage, and SCC.
7. Separate results for every EPA climate model, adaptation scenario,
   elasticity, supply mapping, and price basis; no outcome-selected averaging.
8. A replacement-versus-stacking test demonstrating that overlapping GIVE
   agriculture damages are removed exactly once.

Report the distribution across EPA climate models and GIVE uncertainty draws,
not only an equal-model mean. Label the result **maize precipitation-quantity
partial SCC benchmark**. It does not cover other crops, rainfall timing,
dry-spell persistence, extremes, drought indices, endogenous irrigation,
trade, storage, expectations, nutrition, or adaptation costs.

## Why this benchmark does not finish the paper

The EPA source supplies country annual totals, while the paper's central
question concerns crop-calendar timing and distribution. Proportional scaling
therefore answers a narrower counterfactual: what is the partial SCC if a
marginal CO2 pulse changes annual rainfall quantity but leaves each country's
baseline within-season pattern unchanged? The primary paper still requires a
validated marginal-pulse route for monthly/daily distribution and joint
temperature-moisture features. A null or unstable pattern increment must be
reported rather than hidden behind this quantity benchmark.
