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
cell annual-precipitation climatology from the same resident gridded historical
weather product used for the cell basis. Let `R0_annual[g]` be that strictly
positive cell annual total and `delta_R[c,m,t,p]` the EPA country annual change
above. Because EPA supplies no subnational or monthly pattern, make the
explicit benchmark assumption that the same absolute annual-total change
occurs at every represented crop cell within a country. Define

`scale[g,c,m,t,p] = 1 + delta_R[c,m,t,p] / R0_annual[g]`.

Apply each cell's scale to every month at that cell. The cell's annual total
then changes by exactly the EPA country mean change, while its baseline within-
season shares are preserved. Do **not** divide an annual EPA change by a crop-
season total. Reject any cell-country-year-pulse combination with non-finite
inputs or `scale <= 0`; do not cap or repair it. This uniform-absolute-change
assumption is a declared structural benchmark because EPA supplies only an
area-weighted country mean, not its within-country pattern.

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

## Input implementation checkpoint (September 24, 2026)

The cell annual-rainfall climatology and crop-calendar Hultgren precipitation
basis required above have now been built and independently validated. The
latter contains 48,889 rainfed/irrigated regime-cell rows over 32,301 unique
cells and averages the six precipitation terms across 29 complete 1982--2010
harvest years. Five fixed sentinels were independently reconstructed from
10,957 daily source steps with maximum absolute discrepancy `5.82e-11`;
sampled peak RSS remained below 355 MB. Full details and frozen identities are
in `HULTGREN_PRECIP_BASIS_CLIMATOLOGY_RESULTS_20260924.md`. This checkpoint
opens only the historical-feature-input gate. Response, damage, SCC, and
replacement-accounting gates remain closed.

## Response and source-price damage checkpoint (September 24, 2026)

The 26-model marginal response and central national-market damage paths have
now been evaluated for all four FAIR pulses, three adaptation scenarios, and
both uncapped and frozen 1st/99th-percentile tail rules. The successful exact
streamed build contains 175,344 model/year/pulse/adaptation/tail records for
2020--2300. Zero-pulse, pre-2021, positive-scale, and shrinking-pulse gates
pass; an independent implementation exactly re-ranked the 162,847,160-value
tail pool and reconstructed five fixed market cases. Full evidence is in
`EPA_FAIR_HULTGREN_QUANTITY_DAMAGE_PATH_RESULTS_20260924.md`.

This opens the marginal-response and central structural source-price damage-
path gates only. Currency alignment, alternative elasticities and supply
mappings, paired GIVE replacement, discounting, and SCC normalization remain
required. No value from this checkpoint may be called an SCC.

## Currency and FUND-region checkpoint (September 24, 2026)

The central paths have now been rebased to billion 2005 USD with the registered
GDP-deflator approximation and allocated to all 16 GIVE FUND regions. The
2,805,504-row output is the exact ordered product of 175,344 global path keys
and 16 regions. A streaming independent audit verifies all rows, zero/pre-2021
identities, the currency calculation, and reconciliation to every source global
path (maximum source-dollar disagreement `7.11e-14`). Evidence is in
`EPA_FAIR_HULTGREN_QUANTITY_FUND_PATH_RESULTS_20260924.md`.

This opens the currency and regional-transport gates for the central structural
case only. It does not open the paired-replacement or SCC gates. The current
artifact contains marginal differences rather than paired agriculture damage
levels; imposing a zero replacement baseline would change regional consumption
and endogenous discount factors and is not treated as an innocuous default.
