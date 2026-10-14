# Expanding the social cost of carbon with an AI-assisted, evidence-gated research workflow

## Abstract

Integrated assessment models omit material climate impacts because connecting
physical hazards, economic outcomes, welfare, and a marginal emissions pulse
is slow and data intensive. We develop an AI-assisted workflow for expanding
damage-sector coverage in the Greenhouse Gas Impact Value Estimator (GIVE).
The workflow combines systematic evidence retrieval, isolated reproducible
sector modules, machine-readable provenance, automated claim validation, and
explicit double-counting gates. We apply it to precipitation-sensitive
agriculture, heat-related labor productivity, fisheries, and biodiversity,
while retaining GIVE's existing mortality, energy, agriculture, and coastal
components. The central methodological result is that rapid evidence coverage
does not imply immediate additivity: published partial SCCs can be reproduced
quickly when authors release damage arrays and model code, whereas sectors
with overlapping mortality, nutrition, market, or ecosystem-service pathways
must remain external benchmarks until their endpoints are allocated once. The
analysis therefore reports an integrated SCC only for locally reproduced,
overlap-cleared components and a separate evidence envelope for other omitted
damages. A newly supplied global wildfire-smoke draft provides a concrete air-
pollution application but remains validation-pending. This architecture
illustrates how AI can increase the scale and pace
of economic research without relaxing standards for identification,
provenance, uncertainty, or reproducibility.

## 1. Research question

How much can modern evidence expand sectoral coverage in a policy-grade SCC
model, and which parts of that expansion can be accomplished rapidly and
defensibly using an AI-assisted research workflow?

The objective is not to maximize the number of point estimates. It is to turn
omitted impacts into one of four observable states: integrated and replicated,
original bounded estimate, published external benchmark, or documented open
gap. This replaces silent omission with an auditable evidence frontier.

## 2. Baseline and scope

The baseline GIVE model contains temperature-related mortality, agriculture,
building energy, and coastal damages from sea-level rise. We preserve these
components while evaluating additional or replacement pathways. Separate
sector repositories prevent accidental dependence on or modification of the
wildfire work and allow every module to maintain its own data licenses,
uncertainty design, tests, and claim gates.

## 3. Methods overview

### 3.1 Sector discovery and prioritization

We begin with authoritative assessments of missing SCC sectors, then search
peer-reviewed and official repositories for end-to-end chains that provide
physical exposure, economic response, welfare conversion, and SCC integration.
Priority is a function of expected materiality, transferability, public input
availability, and overlap risk—not the size of an isolated headline number.

### 3.2 Published-model fast route

Where complete code and damage arrays exist, we reproduce the published model
under its pinned environment before adapting it. The labor-productivity case
provides the first application: Moore et al. (2026) released MIT-licensed GIVE
code, country damage arrays, two labor response functions, GCM uncertainty,
and a 10,000-draw SCC analysis. We checksum the archive, instantiate Julia
1.12.5, validate array balance and uniqueness, run a deterministic sector
isolation test, and then stage 100-, 1,000-, and 10,000-draw reproductions.

### 3.3 Original-estimation route

When no transferable end-to-end model exists, we estimate a bounded pathway.
For precipitation-sensitive agriculture, the primary estimand is the change
in agricultural welfare attributable to climate-driven precipitation quantity,
within-season timing, dry spells, and drought, conditional on temperature and
with irrigation represented explicitly. Annual totals remain primary if more
complex distribution features fail to improve held-out prediction. PDSI,
scPDSI, and SPEI compete with raw precipitation representations rather than
being stacked mechanically, which limits double counting of moisture stress.

### 3.4 Overlap and promotion gates

A sector enters the combined SCC only when five gates pass: source identity,
local numerical reproduction, marginal-pulse alignment, uncertainty alignment,
and endpoint overlap. Failure at any gate changes the reporting category, not
the underlying data. External benchmarks remain visible but non-additive.

### 3.5 AI-assisted research protocol

AI tools assist with literature discovery, code translation, provenance
manifests, test generation, data orchestration, and manuscript synchronization.
They do not supply unobserved data, choose preferred specifications after
seeing results, or convert predictive associations into causal parameters.
Every promoted number must trace to a file, executable script, and validation
receipt; failed and null results remain part of the research record.

## 4. Preliminary results

### 4.1 Precipitation-sensitive agriculture

The current original estimates are deliberately narrow and are not promoted
as a precipitation-sector SCC. The later one-model monthly maize diagnostic is
+$0.004269/tCO2 in 2020 USD under fixed adaptation and the GIVE 2% schedule.
Its positive country components sum to +$0.011572/tCO2 and its negative
components to -$0.007304/tCO2, so 77.4% of gross magnitude cancels. The five
largest countries account for 71.7% of gross magnitude; the small net therefore
reflects concentrated geographic offsetting rather than uniformly small
components. The calculation remains one ESM/scenario, maize only, and does not
replace Moore agriculture.

The strongest U.S. historical moisture result is larger: for directly
reported non-irrigated corn, a one-unit PDSI decline is associated with a
4.30% yield decline (500-km spatial interval 3.57% to 5.02% lower). It passes
the frozen spatial, leave-state, terminal-period, and influence gates, but it
cannot enter an SCC until a separately validated climate-to-future-PDSI stage
exists. Direct rainfall and drought indices remain competing channels.

The first exact-support audit sharply narrows that remaining stage. Existing
historical and future SPEI archives already cover 351 of the 361 frozen
counties at the 0.999 geometric threshold. Ten counties fail because only 11
additional half-degree cells are absent; minimum coverage is 0.412. We do not
fit a biased 351-county subset or renormalize failed counties. The immediate
task is therefore bounded: construct the 11 historical cells and reacquire
matching future temperature extrema for five ESMs and three SSPs before
estimating the same-source SPEI response.

That reconstruction has begun. All 11 historical cells now pass independent
validation for 468 months and SPEI-1/3/6, with all 396 calibration fits valid.
All three GFDL-ESM4 future cases (SSP1-2.6, SSP3-7.0, and SSP5-8.5) and the
IPSL-CM6A-LR SSP1-2.6 and SSP3-7.0 cases pass independent validation. Five of
fifteen future cases are complete and ten remain, so no county response, future yield
effect, damage, or SCC is claimed.

### 4.2 Labor productivity and updated agriculture

Moore et al. (2026) report 2025 partial SCCs of $41/tCO2 for labor productivity
(90% interval $1–108) and $29/tCO2 for updated agriculture. We verified the
official code archive, exact dependency environment, and published GTAP arrays,
then completed registered 10,000-draw Lancet and ISO runs under the authors'
seed. Updated agriculture is $29.05/tCO2 under Lancet and $29.10/tCO2 under
ISO. Labor is $29.26/tCO2 under Lancet (5th-95th percentiles $0.19-$70.78)
and $51.86/tCO2 under ISO ($1.04-$133.88). The arithmetic equal-function means
are $29.07 for agriculture, $40.56 for labor, and $179.16/tCO2 for the total,
reproducing the article's rounded $29, $41, and $179 headlines. The source code
does not specify a pooled cross-function quantile rule, so the two full
distributions remain structural sensitivities and no pooled uncertainty
interval is invented.

A hash-bound paired-module preflight now verifies the source installation
graph without executing the target model. It removes nine legacy agriculture
components/support nodes, replaces the damage aggregator, adds
`AgricultureShare`, `Labor`, and updated `Agriculture` once and in order, and
retains separate Lancet and ISO cases. This is not a completed GIVE
installation. A two-draw legacy-agriculture guard probe reached 2,531,426,304
bytes (2.36 GiB), exceeding the 512 MiB worker cap; target execution and the
replacement-delta gate remain closed pending a larger authorized worker or a
numerically equivalent memory refactor.

### 4.3 Fisheries and biodiversity

The published Blue-SCC source data imply a fisheries benchmark of
$22.09755/tCO2, dominated by a nutrition/use pathway rather than market losses.
It is not added to GIVE because its mortality, nutrition, agricultural-market,
and macroeconomic overlaps remain unresolved. A published biodiversity nonuse
benchmark of approximately $8/tCO2 is similarly retained outside the combined
SCC pending regional coefficients, joint uncertainty, and ecosystem-service
allocation.

A source-pinned public-release audit confirms that the current official
MimiGIVE repository contains no configured biodiversity/nonuse term and the
paper landing page exposes no replication package. We therefore prepared an
artifact request for regional valuation coefficients, temperature-response
calibration, country mapping, joint uncertainty draws, matched annual pulse
outputs, licenses, and an explicit nonuse-only boundary. The approximate
$8/tCO2 result remains a context-only literature benchmark.

The executable biodiversity package gate requires seven complete artifact
groups. The pinned public evidence supplies zero of seven, so the package is
rejected as incomplete without treating missing artifacts as zeros or using
the published benchmark as calibration.

The shortest published nutrition transfer now also fails reproducibility and
coverage gates. Requiring all published nutrition and mortality fields to be
numeric leaves 116 of 184 GIVE countries and only 4 of 16 complete FUND
regions. The broader released 2020 country-SCC file covers 154 countries, but
its fisheries sum is 4.92% above the separate Figure 4 total. The repository
lacks the RICE50x baseline and one-million-ton-pulse result files needed to
reconstruct annual damages. No missing coefficient is zero-filled or
renormalized; the benchmark remains external pending a licensed complete
release and explicit mortality-overlap allocation.

A subsequent annual-pair admission test rejects the released fisheries files
more directly. They are terminal SCC summaries rather than matched annual
baseline/pulse paths, and zero of two comparable fisheries country/global
summary pairs reconcile additively. Pulse metadata, complete mapping, direct
consumer-plus-producer-surplus semantics, a machine-readable market-versus-
nutrition boundary, and an artifact license manifest are also absent. This
rejection neither revises nor validates the published benchmark.

The smaller market component also fails the country-transfer gate despite an
exact aggregate reproduction. The Figure 4 workbook gives
$0.0570404/tCO2, while the 155 released country rows sum to $0.0526646/tCO2,
7.67% lower, because the global and country utilities use different
aggregation and discounting. Upstream coefficients and outputs overlap on
only 120 country keys. The released market measure is multiplier-expanded
profit/GDP rather than consumer plus producer surplus. It is therefore shown
as an external benchmark, not treated as an additive country decomposition.

The same public release provides a $2.46/tCO2 global coral non-market-use
benchmark, but it is not a residual coral-tourism estimate. Its valuation
aggregate combines eight services, including recreation and tourism, coastal
protection, erosion prevention, waste treatment, aesthetics, and cultural
services. Only bundle-level uncertainty and income elasticity are released,
and the nonseparable CES welfare structure does not support allocating the SCC
by simple service-value shares. Released country SCC rows also fail to
reconcile to the corresponding global rows. We therefore retain $2.46/tCO2 as
external context only and request recreation-specific, additive annual
baseline/pulse welfare paths before considering a coral residual component.

A bounded municipal-water and inland-flood fast-route audit finds no
transfer-ready module among three leading candidates. The Dolan et al. GCAM
implementation is the closest welfare route, with 235 water basins and an
explicit consumer-plus-producer-surplus measure, but its released surplus
combines six water-demand sectors, its raw curves are request-only, and its
contrast is constrained versus unlimited water rather than a marginal CO2
pulse. MimiFUND has annual pulse machinery but an aggregate water-resources
endpoint that cannot be relabeled municipal. CLIMADA/GloFAS is an open
fluvial-risk comparator, not a pluvial or annual-welfare route. Zero of three
candidates passes all seven climate-response, welfare, coverage, uncertainty,
pulse, license, and overlap gates, so no municipal or inland-flood SCC is
claimed.

### 4.4 Air pollution and wildfire feedbacks

The final-article air-pollution benchmarks also remain external. At the 2%
Ramsey setting, the official repository's checked-in RFF component summaries
average +$16.67/tCO2 for ozone and -$24.53/tCO2 for PM2.5, whereas its separate
net summary is -$34.67/tCO2; the component sum is only -$7.86/tCO2. Mean-path
summaries (+$20.66 and -$21.91) also do not reproduce the article's +$23 and
-$38 values. The source additionally mixes 2024-dollar GDP/VSL inputs with an
NPV header stating 2020 dollars. We therefore request a versioned final release
and do not adjust the public summaries to match the published values.

The exact released component sum is -$7.857400/tCO2 and the separately
released net is -$34.667618/tCO2, a net-minus-components gap of
-$26.810218/tCO2. The discrepancy is nonzero for both CESM2 and GISS, so it is
not created by model averaging. The article states that open burning,
including wildfire, is excluded, but the repository does not encode that
boundary in machine-readable metadata. Final-release, same-stream additivity,
price-year, exclusion-boundary, local-reproduction, GIVE-transfer, and
replacement-SCC gates all remain closed.

An investigator-supplied draft estimates a provisional global wildfire-smoke
PM2.5 mortality partial SCC of $50/tCO2 for a 2025 pulse at a 2% discount rate
(95% conditional interval $18.5-$102.6). The draft combines 43 historical and
future simulations from several global fire-smoke modeling studies, estimates
country-specific linear mappings from GMT to population-weighted wildfire
PM2.5 exposure, applies a long-run all-cause mortality response, and values
deaths within GIVE. The reported interval is explicitly conditional: it does
not fully propagate between-model structural uncertainty, alternative
functional forms, changing population exposure weights, adaptation, or
regional susceptibility. Leave-one-model-out estimates range materially; the
global mean falls from $50.04 to $25.91 when CESM is excluded. We therefore
classify $50 as an unpublished external module until its data, coefficients,
code, and Monte Carlo results reproduce locally.

Wildfire smoke mortality is distinct from the separate wildfire-CO2 feedback:
the former values PM2.5 exposure and deaths, whereas the latter values
additional greenhouse-gas emissions and downstream climate damages. They may
share fire projections and must not count the same emissions or health outcome
twice. Climate-driven surface ozone is a third air-pollution pathway and
requires a separate climate-chemistry-to-exposure-and-health module.

McDuffie et al. (2026) now provide such a published fast route for
meteorologically driven air pollution. Their peer-reviewed analysis reports a
global mean partial SCC of +$23/tCO2 for surface ozone (90% interval +$7 to
+$45), -$38/tCO2 for non-wildfire PM2.5 (-$118 to -$3), and -$15/tCO2 net at
2% Ramsey discounting. Open burning is held fixed and excluded, making the
PM2.5 pathway conceptually separable from wildfire smoke. The official code is
public, but the available commit predates the final article: equal averaging of
its checked-in CESM2 and GISS summaries yields +$16.67 for ozone and -$24.53
for PM2.5, while its separate net summary yields -$34.67 and does not equal the
component sum. We record this discrepancy as a failed reproduction gate. The
published values remain external benchmarks until the final release alignment
is resolved.

## 5. Interpretation

The initial evidence identifies labor productivity as the fastest substantial
extension: it has a large published effect and both structural specifications
now reproduce locally. The next step is overlap-cleared installation, not more
estimation. The precipitation project remains
scientifically valuable because the modern total-agriculture comparator omits
projected rainfall effects and because annual-mean rainfall does not represent
drought, timing, or irrigation scarcity. Fisheries and biodiversity may also
be material, but their headline values cannot yet be added without overstating
damages through overlapping endpoints.

## 6. Planned final analyses

1. Install the reproduced labor component and updated agriculture replacement
   in paired GIVE runs while preserving both labor structural specifications.
2. Finish the precipitation replacement design, prioritizing the climate-to-
   PDSI/SPEI bridge, multi-model disagreement, additional crops, irrigation,
   and heterogeneous winners and losers.
3. Reproduce fisheries country paths and separate market from nutrition and
   mortality endpoints.
4. Obtain the biodiversity coefficient and joint-draw inputs or report the
   benchmark as irreducibly external.
5. Obtain a service-disaggregated coral recreation/tourism run with additive
   country-year welfare paths; exclude fisheries, nonuse, and coastal
   protection already assigned elsewhere.
6. Reproduce the global wildfire-smoke coefficients and SCC, then integrate it
   with the wildfire-carbon module under a shared-input and endpoint audit.
7. Resolve the EPA public-release discrepancy and reproduce its surface-ozone
   and non-wildfire PM2.5 country paths.
8. Construct the overlap-cleared combined SCC and evidence envelope.
9. Run leave-one-sector-out, structural, discounting, climate, socioeconomic,
   and adaptation sensitivities.
10. Release code, manifests, receipts, and an adversarial replication checklist.

## 7. Contribution

The substantive contribution is broader, more current damage coverage in
GIVE. The methodological contribution is a reproducible way to use AI to ask a
larger economic question: not by automating judgment, but by making many more
sources, code paths, uncertainty choices, and falsification checks tractable
within one coherent research design.
