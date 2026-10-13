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

### 4.3 Fisheries and biodiversity

The published Blue-SCC source data imply a fisheries benchmark of
$22.09755/tCO2, dominated by a nutrition/use pathway rather than market losses.
It is not added to GIVE because its mortality, nutrition, agricultural-market,
and macroeconomic overlaps remain unresolved. A published biodiversity nonuse
benchmark of approximately $8/tCO2 is similarly retained outside the combined
SCC pending regional coefficients, joint uncertainty, and ecosystem-service
allocation.

The shortest published nutrition transfer now also fails reproducibility and
coverage gates. Requiring all published nutrition and mortality fields to be
numeric leaves 116 of 184 GIVE countries and only 4 of 16 complete FUND
regions. The broader released 2020 country-SCC file covers 154 countries, but
its fisheries sum is 4.92% above the separate Figure 4 total. The repository
lacks the RICE50x baseline and one-million-ton-pulse result files needed to
reconstruct annual damages. No missing coefficient is zero-filled or
renormalized; the benchmark remains external pending a licensed complete
release and explicit mortality-overlap allocation.

### 4.4 Air pollution and wildfire feedbacks

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
5. Reproduce the global wildfire-smoke coefficients and SCC, then integrate it
   with the wildfire-carbon module under a shared-input and endpoint audit.
6. Resolve the EPA public-release discrepancy and reproduce its surface-ozone
   and non-wildfire PM2.5 country paths.
7. Construct the overlap-cleared combined SCC and evidence envelope.
8. Run leave-one-sector-out, structural, discounting, climate, socioeconomic,
   and adaptation sensitivities.
9. Release code, manifests, receipts, and an adversarial replication checklist.

## 7. Contribution

The substantive contribution is broader, more current damage coverage in
GIVE. The methodological contribution is a reproducible way to use AI to ask a
larger economic question: not by automating judgment, but by making many more
sources, code paths, uncertainty choices, and falsification checks tractable
within one coherent research design.
