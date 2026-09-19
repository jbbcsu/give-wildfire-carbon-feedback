# Manuscript insert: structural precipitation benchmark and economic translation

Status: insert-ready text for later merge into the main manuscript and Methods
SI. All values are structural sensitivities; no empirical damage or SCC result
is authorized.

## Results: what the conventional quantity-only benchmark captures

We first quantified the component of agricultural welfare associated with
period-mean precipitation quantity in two published process-crop-model
emulators. This benchmark is deliberately narrower than our primary target: it
does not represent within-season rainfall timing, wet-day frequency, dry spells,
extremes, SPI, SPEI or PDSI. Its role is to establish what a conventional
mean-climate pathway would imply before distribution-aware evidence is added.

The physical experiment compares 1981--2010 with 2031--2060 climate for
GFDL-ESM4 and IPSL-CM6A-LR under SSP1-2.6 and SSP5-8.5, holding CO2 and
management fixed. CARAIB and EPIC-TAMU are retained as separate structural
alternatives. Fixed MapSPAM production weights define a common supported maize
footprint; FAOSTAT value proxies are allocated to rainfed and irrigated
production without filling missing countries or rescaling coverage.

### Welfare attribution must follow, not precede, nonlinear valuation

For each cell, the process-crop emulators provide four yield corners:
baseline temperature/baseline precipitation (`y00`), future temperature/
baseline precipitation (`y10`), baseline temperature/future precipitation
(`y01`) and joint future climate (`y11`). We aggregate positive country-regime
productivity changes into a global maize market and evaluate consumer-plus-
producer surplus at every corner. The precipitation welfare contribution is the
two-driver Shapley value

`0.5[(B01-B00)+(B11-B10)]`,

where `Bab` is the total-surplus benefit at corner `ab`. Temperature is
`0.5[(B10-B00)+(B11-B01)]`; the two contributions close exactly to the joint
change. This ordering avoids treating an order-averaged *yield* contribution as
an independent supply shock and shares the nonlinear interaction once.

Under the central supply/demand elasticity pair (0.10/0.04), horizontal-output
mapping, one global market and fixed management, precipitation is beneficial in
the admissible SSP1-2.6 structural cases and a small loss in the admissible
SSP5-8.5 cases (Table X). Temperature dominates joint maize losses.

| Crop model / climate case | Precipitation Shapley damage, billion USD2005 | Temperature Shapley damage | Joint damage |
|---|---:|---:|---:|
| CARAIB / GFDL SSP1-2.6 | −0.337 to −0.328 | 9.387 to 9.397 | 9.049 to 9.069 |
| CARAIB / GFDL SSP5-8.5 | 0.008 to 0.014 | 14.203 to 14.228 | 14.211 to 14.241 |
| CARAIB / IPSL SSP1-2.6 | −0.063 to −0.057 | 13.801 to 13.813 | 13.738 to 13.757 |
| CARAIB / IPSL SSP5-8.5 | 0.014 to 0.022 | 23.690 to 23.706 | 23.703 to 23.728 |
| EPIC-TAMU / GFDL SSP1-2.6 | −2.820 to −2.787 | 7.548 to 7.566 | 4.728 to 4.779 |
| EPIC-TAMU / GFDL SSP5-8.5 | 0.119 | 12.350 to 12.378 | 12.469 to 12.497 |
| EPIC-TAMU / IPSL SSP1-2.6 | −1.010 to −0.938 | 11.648 to 11.679 | 10.637 to 10.742 |
| EPIC-TAMU / IPSL SSP5-8.5 | not admissible | not admissible | not admissible |

Negative precipitation damage denotes a benefit; the range is across the two
calendar conventions. Across all three elasticity pairs and two supply
mappings, the precipitation component remains beneficial for the admissible
SSP1-2.6 cases and a small loss for the admissible SSP5-8.5 cases. This sign
pattern is conditional on the crop emulators, climate cases and quantity-only
experiment. It is not an estimate of total real-world precipitation damages.

### Market geography is consequential for severe local tails

Before the global-market calculation, we evaluated the registered primary
country-market assumption. CARAIB's central country-market losses are close to
the global-market values: the latter are 97--98% of the former. EPIC-TAMU is
different. In the IPSL/SSP1-2.6 case, a severe modeled Algerian response reduces
the country's aggregate multiplier to 0.10675. That small market contributes
93.494 billion USD2005 to a 105.963-billion country-market subtotal despite only
0.153 million of covered baseline value. Pooling supply before equilibrium
reduces the same case to 10.637 billion. Thus the extreme result is chiefly an
interaction between the crop-response tail and highly inelastic, segmented
markets, not a robust global welfare estimate.

We do not select the global market because it produces smaller losses. The
comparison establishes market geography as structural uncertainty. Neither a
frictionless world market nor isolated national markets represents observed
trade, storage and cross-crop substitution; an intermediate geography requires
source-justified trade structure rather than an arbitrary continent mapping.

### Fixed positive-support sensitivity

Some published polynomial corners are nonpositive. We retain these failures in
the primary diagnostic and never clip them. A prespecified support audit defines
one alternative footprint that is positive at all four corners for both crop
models, both climate models, both scenarios and both calendars. This mask
excludes 186 cell/regime locations but only 0.01751% of common production and
0.02254% of covered value (24.584 million of 109.047 billion USD2005).

On this fixed partial support, the main precipitation signs persist. The largest
central change is EPIC GFDL/SSP1-2.6, for which the precipitation benefit falls
by 0.126 billion. The previously inadmissible EPIC IPSL/SSP5-8.5 case becomes
arithmetically positive, with a central precipitation benefit of 0.346--0.368
billion and joint loss of 22.048--22.097 billion. We do not promote it: removing
invalid corners changes the represented population, even when their value share
is small. The sensitivity shows robustness on retained support, not a model
repair or global estimate.

## Methods: economic benchmark

For market baseline value `V0`, supply elasticity `e`, demand-elasticity
magnitude `d` and log supply shift `s`, normalized supply and demand are

`qS(p;s)=exp(s)p^e` and `qD(p)=p^(-d)`.

The equilibrium satisfies `log p=-s/(e+d)` and `log q=ds/(e+d)`. For a paired
increment `h` from baseline shift zero, the stabilized total-surplus change is

`Delta TS = V0 h exprel(-(1-d)h/(e+d))/(1+e)`,

where `exprel(z)=expm1(z)/z`. Positive damage is `-Delta TS`. We use the
published elasticity scenarios 0.08/0.02, 0.10/0.04 and 0.50/0.06. Two explicit
yield-to-supply mappings are reported: `s=log A` (horizontal output) and
`s=(1+e)log A` (fixed-input cost). Their spread is model uncertainty, not a
confidence interval.

Rainfed and irrigated production enter one commodity market. For regime or
country-regime supply inputs `sr` with fixed covered-value shares `wr`, the
aggregate shift is `log(sum_r wr exp(sr))`. Missing baseline values remain
unvalued. The complete covered value is 109.047 billion USD2005 across 107
countries, derived from a 1999--2001 FAOSTAT proxy and a registered GDP-wide
price rebase. It is a static value base, not projected 2031--2060 output or
income. Welfare is therefore linear in this declared baseline scale.

All physical model, climate model, scenario, calendar, irrigation, elasticity,
supply-mapping, support and market-geography identifiers remain separate. We
preserve signed benefits, do not truncate losses, and do not average CARAIB and
EPIC-TAMU. The calculation supplies neither annual damages nor a matched
emissions-pulse derivative.

## Relation to the distribution-aware primary project

The structural result does not resolve the main empirical question. Direct
daily late-century climate inputs show mixed seasonal-rainfall changes across
three ESMs but common signs for fewer wet days, longer maximum dry spells and
larger Rx1day/Rx5day on rainfed-maize area. U.S. non-irrigated NASS validation
finds useful incremental prediction from direct rainfall-pattern and drought
features, but neither family passes all geographic and temperature-control
gates. The global country-held-out empirical screen promotes no response family.

The published Araujo SPI/SPEI product is an appropriate external drought
benchmark, but its current Dataverse release packages each GCM as a 31--33 GB
archive. The five overlapping GIVE models total 149.18 GiB and have no
repository checksum, so acquisition waits for a safe external-storage or
provider-subset route. Meanwhile, source-consistent ISIMIP SPEI remains the
primary climate path; its GFDL crop-window pilot is technically validated but
too early and too small for a damage interpretation.

## Release gate

No result in this insert is an empirical precipitation damage function, total
agriculture replacement, annual damage path or SCC estimate. The structural
benchmark must not be stacked on GIVE's existing agriculture function. Release
requires a response that survives untouched validation, later-century
multi-ESM climate support, calibrated adaptation, complete welfare coverage and
matched baseline/pulse paths through GIVE's marginal-damage machinery.
