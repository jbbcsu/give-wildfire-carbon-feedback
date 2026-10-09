# Methods Supporting Information

## S1. Reproducibility architecture

Each sector occupies an isolated directory and Git branch. Raw or licensed
inputs are ignored; acquisition scripts, source URLs, licenses, checksums, and
derived validation receipts are tracked. The umbrella project stores only the
cross-sector registry, combination rules, and manuscript. It does not vendor
or silently mutate sector code.

## S2. Evidence and claim taxonomy

Every quantitative statement is assigned an evidence class before manuscript
use. A published number is not a local result. A deterministic smoke test is
not a Monte Carlo reproduction. A predictive association is not a causal
damage function. A partial SCC is not a total sector SCC. An external benchmark
is not an additive component.

## S3. Published-model replication

For each published model we record the versioned source, license, archive hash,
runtime and package versions, data dependencies, pulse year and size, gas and
molecular-weight convention, currency and price year, discount schedule,
socioeconomic sampling, climate-model sampling, random seed, trial count, and
sectoral aggregation. Replication tolerances are declared before the full run.

## S4. Original estimation

Original modules preregister the estimand, units, sample, fixed effects,
clustering, train/test partition, feature hierarchy, adaptation scenarios, and
promotion tests. Complex features advance only if they improve held-out
performance and retain stable direction and magnitude. Null results are
reported without replacement by an unregistered specification.

## S5. Overlap matrix

Before combination, every endpoint is mapped across sectors. Particular checks
include agricultural labor versus crop-market welfare; fish nutrition versus
mortality and terrestrial food substitution; biodiversity nonuse versus coral
and fisheries use values; coastal protection versus CIAM; wildfire-smoke and
ozone mortality versus existing climate mortality; wildfire-smoke PM2.5 versus
the separate wildfire-CO2 feedback; and adaptation energy costs versus
building energy. Air-pollution modules retain separate physical chains for
wildfire PM2.5, surface ozone, and additional wildfire CO2, while recording
shared fire and climate inputs.

## S5.1 Wildfire-smoke evidence gate

The provisional smoke module is promoted only after reproducing: the 43-source
simulation inventory, regridding and fixed population weights, country-model
fixed-effects coefficients, PM2.5 concentration-response transformation,
country-year mortality and VSL scaling, paired GIVE pulse calculation, and
leave-one-model-out sensitivity. Its reported interval is labeled conditional
unless structural fire-model and functional-form uncertainty are propagated.

## S5.2 Meteorological ozone and non-wildfire PM2.5 evidence gate

The McDuffie et al. reduced-form model is reproduced from its versioned public
repository before integration. Validation separately checks article and code
versions, the two GCM-specific impact-per-degree functions, 10,000 RFF paths,
the marginal-pulse carbon-to-CO2 conversion, country aggregation, Ramsey
discounting, certainty-equivalent adjustment, and the identity between ozone,
PM2.5, and net summaries. Any mismatch between article and repository output
fails promotion rather than being reconciled through undocumented arithmetic.

## S6. SCC calculation

Eligible damage modules are evaluated in paired baseline and marginal-emission
runs using a common pulse, horizon, price year, socioeconomic draw, climate
draw, and discount schedule. Joint draws preserve dependencies where the
source model provides them. Otherwise, results are reported separately or
under transparent alternative dependence assumptions rather than assuming
independence.

## S7. Validation

Validation includes source checksums, schema and balance checks, unit and sign
tests, deterministic sector isolation, small Monte Carlo staging, published
result reproduction, memory monitoring, cross-model comparisons, held-out
prediction for empirical modules, and machine-checked manuscript claims.

## S8. Role of AI and human review

The research log will identify tasks performed with AI assistance and the
artifacts used to verify them. AI output is treated as untrusted until checked
against primary sources or executable results. Material modeling choices,
overlap allocations, and manuscript claims remain subject to investigator
approval and independent critical review.
