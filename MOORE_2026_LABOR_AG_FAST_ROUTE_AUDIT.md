# Moore et al. (2026) fast-route audit

Status: literature and implementation audit, 9 October 2026. This note does
not import a coefficient, alter GIVE, or create a new SCC estimate.

## Decision

Moore et al. (2026), *New labour and agricultural damages improve climate
cost estimates*, provides a high-value fast route for the broader GIVE damage
expansion, but it does not replace the precipitation project.

- The paper's heat-related labor-productivity pathway is a candidate new GIVE
  sector. The published 2025 partial SCC is USD 41/tCO2, with a reported 90%
  interval of USD 1--108/tCO2. This is an external published estimate until the
  authors' damage arrays, pulse convention, currency basis, and code are
  independently reproduced.
- The paper also replaces the older Moore agriculture function with an
  IPCC-AR6 evidence synthesis. Its published 2025 agriculture partial SCC is
  USD 29/tCO2. The supplement's 2020 decomposition gives USD 27/tCO2 under a
  2% discount rate with socioeconomic and damage uncertainty.
- The updated agriculture function is not precipitation-aware in projection.
  Rainfall change enters the yield meta-regression as a control, but the
  authors report a small, statistically insignificant coefficient (p=0.6) and
  omit rainfall from the projected damage function. That finding concerns
  aggregate rainfall change in the available crop-model literature. It does
  not test within-season timing, dry spells, extremes, SPEI/PDSI, or
  irrigation scarcity and therefore does not invalidate this project's
  precipitation estimand.

The shortest defensible publication route is consequently:

1. use the new agriculture function as the contemporary total-agriculture
   comparator and eventual replacement baseline;
2. report this project's precipitation quantity result as a narrow mechanism
   benchmark and continue the timing/drought/irrigation work as the novel
   extension;
3. reproduce the published labor sector as the next major missing GIVE damage
   category using the authors' now-identified MIT-licensed source package; and
4. keep fisheries, biodiversity, inland flooding, and other sectors in a
   separate overlap-controlled portfolio rather than adding published SCC
   point estimates directly.

## Agricultural methods that are directly usable

The supplement describes a transparent GIVE-compatible chain:

- 8,703 crop-model estimates from 202 studies, covering maize, rice, wheat,
  and soybean in 91 countries;
- a no-intercept yield response in temperature, temperature squared, rainfall
  change, nonlinear CO2 fertilization, and adaptation, estimated on 8,495
  usable observations with study-clustered errors;
- crop- and baseline-temperature-specific warming responses;
- gridded crop impacts aggregated to 160 GTAP regions, followed by general
  equilibrium welfare changes that allow production relocation, commodity
  substitution, and trade adjustment;
- mapping from 160 GTAP regions to 184 GIVE countries;
- country damage functions with half-degree knots from 0 to 4 C above
  preindustrial conditions; and
- one triangular uncertainty draw per Monte Carlo run, shared across countries
  to preserve the cross-country dependence induced by GTAP.

The country-year damage share follows the existing GIVE agriculture scaling:
2017 agriculture share times an income adjustment with elasticity 0.31 times
the country-specific piecewise temperature damage function. This architecture
is much closer to a drop-in GIVE replacement than a stand-alone SCC number.

## Important limitations and overlap rules

1. The projected agriculture function combines temperature, CO2
   fertilization, adaptation, and general-equilibrium adjustment. A new
   precipitation mechanism must replace or decompose this agriculture sector;
   it cannot be added without an explicit overlap allocation.
2. The estimated adaptation benefit is 5.4 percentage points of yield per
   degree of warming, but irrigation and fertilizer costs are not included.
   The authors explicitly characterize the estimated net benefit as likely
   overstated. This project's fixed, trend, and upper adaptation cases remain
   useful sensitivity scenarios rather than calibrated net-welfare paths.
3. The agricultural evidence base is process-model based. The U.S. NASS and
   global empirical work remain complementary validation evidence rather than
   redundant estimation.
4. The article links a complete MIT-licensed GIVE replication archive at
   https://doi.org/10.5281/zenodo.21483095 and an associated CC-BY-4.0 gridded
   heat-stress archive at https://doi.org/10.5281/zenodo.21712766. The code
   archive contains the country agriculture and labor damage arrays, two labor
   response specifications, GCM dimension, uncertainty machinery, and SCC
   scripts. Its published MD5 checksum has been independently verified and its
   exact Julia 1.12.5 environment instantiated in the isolated
   `labor_productivity_scc` project. A deterministic SSP2-4.5 sector-isolation
   smoke test passed. Exact 10,000-draw RFF-SP reproduction remains in progress,
   so the published headline values are still external rather than promoted
   local results.
5. Labor is potentially large and plausibly distinct from GIVE's current
   mortality, agriculture, energy, and coastal sectors, but agricultural labor
   and heat mortality still require explicit overlap checks. The published
   USD 41/tCO2 estimate must not be pasted into GIVE as a scalar.

## Source and integrity record

Primary article: Frances C. Moore, Iman Haqiqi, Qinqin Kong, Lisa Rennels,
Uris Baldos, Hamsa Ganapathi, Matthew Huber, and Thomas Hertel (2026), "New
labour and agricultural damages improve climate cost estimates," *Nature
Climate Change*. DOI: https://doi.org/10.1038/s41558-026-02749-z.

Publisher supplement: 30 pages, 4,560,918 bytes, SHA-256
`3a135cfa33dfbd346bd6e600e9b46922a2c88115d5cbb1afa101bdc64b736371`.
The machine-readable receipt is
`data/provenance/moore_2026_labor_ag_methods_si_20261009.json`.

Related open agricultural input: Hasegawa et al. (2022), *A global dataset for
the projected impacts of climate change on four major crops*, Scientific Data
9, 58, https://doi.org/10.1038/s41597-022-01150-7 (CC0 data record).

## Claim gates

| Gate | Status |
|---|---|
| Publisher supplement identity | Passed |
| Published headline values documented | Passed |
| Official MIT code and country damage arrays acquired | Passed |
| Exact Julia 1.12.5 environment instantiated | Passed |
| Deterministic sector-isolation smoke test | Passed; diagnostic only |
| 2026 agriculture 10,000-draw SCC reproduced | In progress |
| 2026 labor 10,000-draw SCC reproduced | In progress |
| Labor overlap with agriculture/mortality resolved | Closed |
| Updated agriculture installed in local GIVE | Closed |
| Labor installed in local GIVE | Closed |
| Combined missing-sector SCC | Closed |
