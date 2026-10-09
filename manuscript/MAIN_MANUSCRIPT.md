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
damages. This architecture illustrates how AI can increase the scale and pace
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

The current original estimate is deliberately narrow. For a fixed-adaptation,
annual-maize rainfall-quantity channel, the central partial SCC is
-$0.00610/tCO2 in 2020 USD at the GIVE 2% schedule. Across 936 structural paths,
the 2% design range is -$0.01137 to +$0.00104/tCO2. These are design summaries,
not probabilities, and the estimate is not total precipitation-agriculture
damage. Drought, timing, extremes, other crops, endogenous irrigation costs,
and international market adjustment remain outside the promoted result.

### 4.2 Labor productivity and updated agriculture

Moore et al. (2026) report 2025 partial SCCs of $41/tCO2 for labor productivity
(90% interval $1–108) and $29/tCO2 for updated agriculture. We have verified
the official code archive and its exact dependency environment. A diagnostic
SSP2-4.5 deterministic isolation run produces distinct labor and agriculture
partial SCCs, and the published GTAP arrays pass structural checks. Exact RFF
10,000-draw reproduction is in progress; published headline values remain
external until that gate passes.

### 4.3 Fisheries and biodiversity

The published Blue-SCC source data imply a fisheries benchmark of
$22.09755/tCO2, dominated by a nutrition/use pathway rather than market losses.
It is not added to GIVE because its mortality, nutrition, agricultural-market,
and macroeconomic overlaps remain unresolved. A published biodiversity nonuse
benchmark of approximately $8/tCO2 is similarly retained outside the combined
SCC pending regional coefficients, joint uncertainty, and ecosystem-service
allocation.

## 5. Interpretation

The initial evidence suggests that the fastest substantial extension is labor
productivity, not precipitation agriculture: it has a large published effect
and a complete reproducibility package. The precipitation project remains
scientifically valuable because the modern total-agriculture comparator omits
projected rainfall effects and because annual-mean rainfall does not represent
drought, timing, or irrigation scarcity. Fisheries and biodiversity may also
be material, but their headline values cannot yet be added without overstating
damages through overlapping endpoints.

## 6. Planned final analyses

1. Complete and verify the 10,000-draw labor and updated-agriculture SCCs.
2. Finish the precipitation replacement design, prioritizing drought/timing,
   additional crops, irrigation, and heterogeneous winners and losers.
3. Reproduce fisheries country paths and separate market from nutrition and
   mortality endpoints.
4. Obtain the biodiversity coefficient and joint-draw inputs or report the
   benchmark as irreducibly external.
5. Construct the overlap-cleared combined SCC and evidence envelope.
6. Run leave-one-sector-out, structural, discounting, climate, socioeconomic,
   and adaptation sensitivities.
7. Release code, manifests, receipts, and an adversarial replication checklist.

## 7. Contribution

The substantive contribution is broader, more current damage coverage in
GIVE. The methodological contribution is a reproducible way to use AI to ask a
larger economic question: not by automating judgment, but by making many more
sources, code paths, uncertainty choices, and falsification checks tractable
within one coherent research design.
