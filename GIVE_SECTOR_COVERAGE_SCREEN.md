# GIVE coverage and next-sector screen

Updated 2026-10-09. This is a literature-based prioritization note, not a
damage estimate. It uses current RFF documentation to define the baseline and
does not rank sectors by invented SCC values.

## Verified baseline

RFF's 2024 ocean-systems report states that GIVE contains four damage
categories: temperature-related mortality, agriculture, building energy use,
and coastal impacts from sea-level rise. It identifies coral reefs and
fisheries as priority ocean omissions:
https://www.rff.org/publications/reports/challenges-and-opportunities-for-incorporating-climate-changes-impacts-on-ocean-systems-into-the-social-cost-of-greenhouse-gases/

RFF's 2026 practitioner primer distinguishes GIVE's sectoral core from EPA's
broader 2023 implementation, which also includes labor productivity, and lists
wildfire, extreme-weather, and biodiversity damages among remaining omissions:
https://www.rff.org/publications/reports/adopting-the-social-cost-of-carbon-for-state-benefit-cost-analysis-a-primer-for-practitioners/

Moore et al. (2026) now provide a directly relevant modern-IAM labor result:
heat-related labor productivity has a published 2025 partial SCC of USD
41/tCO2 (90% interval USD 1--108). The same paper updates agriculture in GIVE
and reports a 2025 agriculture partial SCC of USD 29/tCO2. The labor result is
therefore no longer only an EPA precedent; it is the most implementation-ready
large published candidate identified by this screen. It remains an external
publication result until its currency and pulse conventions, uncertainty
dependence, and overlaps are locally reproduced. The authors' complete
MIT-licensed GIVE archive has now been acquired from
https://doi.org/10.5281/zenodo.21483095; its checksum, pinned Julia 1.12.5
environment, country damage arrays, and deterministic sector-isolation path
pass local checks in the separate `labor_productivity_scc` project. Exact
10,000-draw reproduction remains in progress. Primary article:
https://doi.org/10.1038/s41558-026-02749-z.

RFF's 2026 air-quality review concludes that climate-driven air pollution is
missing from current SCC models and specifically prioritizes wildfire smoke
and surface-level ozone for near-term modeling:
https://www.rff.org/publications/journal-articles/incorporating-air-quality-health-impacts-into-the-social-cost-of-carbon/

## Assessment

No reviewed source provides a common, mutually exclusive global SCC
distribution across every omitted sector, so a numerical ranking of all gaps
would still be unsupported. However, the September 2026 labor paper changes
the implementation ranking. **Labor productivity is now the preferred next
published-sector replication** because it has a peer-reviewed global damage
chain, explicit uncertainty, and a modern partial SCC. This is a readiness
decision, not a claim that labor is the largest omitted damage in nature.

Climate-driven air-quality health remains the preferred next *newly modeled*
sector after labor. Under this program's strict wildfire isolation rule, the
implementable candidate is **surface-level ozone morbidity and mortality**.
Its lower readiness relative to labor reflects the need to assemble and pair
climate-chemistry concentration fields, not evidence of a smaller effect.

Coral-reef ecosystem services are a co-candidate, not evidence that labor is
unambiguously second. RFF's ocean assessment identifies coral reefs and
fisheries after considering anticipated magnitude and IAM feasibility. The
active fisheries track excludes reef tourism, nonuse value, and coastal
protection, while the biodiversity track is restricted to nonuse value and
has no calibrated valuation. The remaining reef services are therefore real
coverage gaps, but they are less scaffold-ready because every service must be
assigned once across fisheries, biodiversity, and CIAM. This evidence supports
including coral services in the coordinator choice; it does not establish a
cross-sector numerical rank.

## Surface-ozone research boundary

A safe initial module would estimate only the climate-mediated change in
surface ozone under matched baseline and marginal-CO2 climate paths, holding
anthropogenic ozone-precursor emissions fixed within each pair. It would then
apply separately identified concentration-response relationships to endpoints
not already monetized elsewhere.

Required exclusions and reconciliation rules:

- Exclude wildfire smoke, fire emissions, fire data, and every wildfire CO2
  pathway from this track.
- Separate climate-mediated ozone from policy co-benefits caused by changing
  co-emitted precursor pollutants; the latter are not part of a pure CO2-pulse
  SCC without an expanded emissions counterfactual.
- Reconcile mortality by cause/pathway with GIVE's temperature-related Cromar
  mortality. Do not add a regression of total mortality on ozone if the
  underlying endpoint also absorbs heat effects.
- Exclude ozone-related crop-yield losses from the health module; they belong
  in the joint agriculture replacement if separately identified.
- Exclude labor/productivity effects from the health valuation unless a joint
  morbidity-productivity model allocates them once.
- Keep optional DICE and Howard--Sterner aggregate damage functions disabled
  in any future sectoral run.

## Implementation order

1. Reproduce Moore et al. (2026) labor country damage paths and partial SCC
   under their published configuration using the verified public archive.
2. Audit labor overlap against agriculture, heat mortality, energy/adaptation
   spending, and macroeconomic incidence. Agricultural labor must not be
   counted both through yield/GTAP agriculture and economy-wide labor losses.
3. Install labor as an explicit paired baseline/pulse component only after
   the reproduction and overlap gates pass.
4. Continue fisheries and biodiversity as separate residual pathways. Their
   published USD 22.10 and USD 8/tCO2 benchmarks are not directly additive.
5. Develop non-wildfire surface ozone next, beginning with a source/provenance
   manifest for climate chemistry, health endpoints, population, and valuation.
6. Treat coral services separately: fisheries values stay in fisheries,
   nonuse values in biodiversity, shoreline/property protection in CIAM, and
   tourism/recreation only in a separately identified residual.

No candidate is additive eligible before its overlap review passes. Published
point estimates must never be pasted into GIVE as scalar damages.
