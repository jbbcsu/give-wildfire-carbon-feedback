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

For Moore et al. (2026), the full Lancet and ISO specifications use Julia
1.12.5, one thread, RFF-SP socioeconomic sampling, random seed 24523438, a
2025 CO2 pulse, 10,000 draws, and the published 2% Ramsey schedule. Tracked
receipts bind each output summary, runner, and package manifest by SHA-256.
The independently reproduced labor means are $29.26/tCO2 for Lancet and
$51.86/tCO2 for ISO; agriculture is $29.05 and $29.10/tCO2. Their arithmetic
equal-function means reproduce the article's rounded headlines. Because the
archived code does not document a cross-function draw-pooling rule, separate
quantiles are retained and pooled quantiles or standard errors are not
constructed.

The paired-module execution preflight is source-graph validation, not a target
GIVE run. It removes nine legacy agriculture components/support nodes, replaces
the damage aggregator, adds `AgricultureShare`, `Labor`, and updated
`Agriculture` once and in order, and retains Lancet and ISO as separate
structural cases. A two-draw legacy-agriculture guard probe reached
2,531,426,304 bytes (2.36 GiB), above the 512 MiB worker ceiling. Therefore a
target run requires an authorized worker above the observed peak or a validated
memory-equivalent refactor; no replacement delta or pooled uncertainty is
promoted from the preflight.

## S4. Original estimation

Original modules preregister the estimand, units, sample, fixed effects,
clustering, train/test partition, feature hierarchy, adaptation scenarios, and
promotion tests. Complex features advance only if they improve held-out
performance and retain stable direction and magnitude. Null results are
reported without replacement by an unregistered specification.

For the U.S. county SPEI bridge, all 11 missing historical half-degree cells
have validated 468-month SPEI-1/3/6 series. Five of fifteen preregistered future
model-scenario extensions are independently validated and ten remain. The
bridge is incomplete, and it is not used to estimate a response, yield effect,
damage, or SCC.

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

The current official-repository audit reports checked-in RFF ozone and PM2.5
components of +$16.671649/tCO2 and -$24.529049/tCO2. Their sum is
-$7.857400/tCO2, whereas the separately released net is -$34.667618/tCO2, a
net-minus-components gap of -$26.810218/tCO2 that is nonzero for both GCMs.
The article states that open burning, including wildfire, is excluded, but the
repository does not provide a machine-readable exclusion field; price-year
headers and inputs also conflict. Final-release, same-stream additivity,
price-year, exclusion-boundary, local-reproduction, GIVE-transfer, and
replacement-SCC gates therefore remain closed.

## S5.3 Fisheries transfer evidence gate

The Blue-SCC fisheries benchmark is not transferred as a scalar. Promotion
requires complete numeric country inputs or source-defined missingness,
reconciliation between country exports and the published aggregate, licensed
versioned RICE50x baseline and pulse results sufficient to reconstruct annual
damages, and an endpoint crosswalk separating seafood-nutrition mortality from
existing GIVE mortality. Missing countries and unavailable nutrition fields
are never treated as observed zeros; incomplete FUND regions are not
renormalized.

The public fisheries terminal-summary files also fail the frozen annual-pair
admission contract: zero of two comparable country/global summary pairs are
additively reconcilable, and matched annual baseline/pulse paths, pulse
metadata, direct consumer-plus-producer-surplus semantics, complete mapping,
machine-readable endpoint boundaries, and artifact-license records are absent.
This is a rejection of the transfer artifact, not a revision of the published
benchmark.

## S5.3a Biodiversity nonuse evidence gate

The executable biodiversity admission contract requires seven artifact groups
covering source implementation, calibration, country/region mapping, joint
uncertainty, matched pulse output, provenance/licensing, and the nonuse welfare
boundary. The pinned public release supplies 0 of 7 complete groups and is
rejected as incomplete. Missing artifacts are not treated as zeros, and the
approximately $8/tCO2 literature value remains external and non-additive.

## S5.4 Coral residual-services evidence gate

The Blue-SCC coral non-market-use result is retained only as an external
benchmark because it combines eight ecosystem services and publishes neither
a recreation-specific SCC nor matched annual marginal-welfare paths. Simple
share-scaling is prohibited under its nonseparable CES welfare function.
The audited $2.46/tCO2 global value is the bundled eight-service external
benchmark; it is neither promoted nor added to another sector value.
Promotion requires licensed, service-disaggregated recreation/tourism inputs;
matched baseline and pulse country-year welfare paths; exact annual regional-
to-global reconciliation; recreation-specific uncertainty; and an explicit
boundary excluding fisheries/provisioning, biodiversity nonuse, and reef
coastal protection already assigned to other sectors. The published country
SCC rows are not treated as additive because they do not sum to the global
rows under the source model's country-specific consumption and discounting.

## S5.5 Municipal water and inland-flood evidence gate

Candidate models must separately identify municipal/household water-supply
reliability or municipal treatment, pumping, storage, and conveyance costs;
provide annual matched marginal-pulse welfare paths; preserve uncertainty and
geographic mappings; and exclude GIVE agriculture, energy, CIAM coastal,
industrial, hydropower, recreation, ecosystem, and inland-flood endpoints.
Mixed water-market surplus may not be allocated by withdrawal, GDP, or
population shares. The current GCAM, MimiFUND, and CLIMADA/GloFAS candidates
pass zero of three complete seven-gate evaluations, so the sector remains an
audited gap rather than a zero or transferred SCC.

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
The umbrella claim-consistency test also checks the registry, manuscript,
Methods SI, and dated machine-readable sector status for reviewed milestone
counts, the observed Moore memory bound, exact EPA reconciliation gap, external
benchmark labels, and closed additivity/promotion gates.

## S8. Role of AI and human review

The research log will identify tasks performed with AI assistance and the
artifacts used to verify them. AI output is treated as untrusted until checked
against primary sources or executable results. Material modeling choices,
overlap allocations, and manuscript claims remain subject to investigator
approval and independent critical review.
