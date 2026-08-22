# GIVE coverage and next-sector screen

Updated 2026-08-21. This is a literature-based prioritization note, not a
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

RFF's 2026 air-quality review concludes that climate-driven air pollution is
missing from current SCC models and specifically prioritizes wildfire smoke
and surface-level ozone for near-term modeling:
https://www.rff.org/publications/journal-articles/incorporating-air-quality-health-impacts-into-the-social-cost-of-carbon/

## Assessment

No reviewed RFF source provides a common global SCC distribution across all
omitted sectors, so calling one omission the numerically “largest” would be
unsupported. The strongest evidence-backed **next research priority** outside
the already active agriculture, fisheries, and biodiversity tracks is
climate-driven air-quality health, because the newest RFF review explicitly
prioritizes it. Under this program's strict wildfire isolation rule, the
implementable candidate narrows to **surface-level ozone morbidity and
mortality**. This is a priority judgment, not a magnitude claim.

Labor productivity is the closest alternative: RFF documents that it is
included in EPA's 2023 enumerative implementation but absent from GIVE's four-
sector core. It may be more implementation-ready than global ozone, but its
market-output endpoint has wider overlap with agriculture, energy use,
mortality, and any macroeconomic damage function. It should remain the second
candidate until a direct comparison of data coverage, identification, and
additive boundaries is completed.

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

## Scaffold gate

No data download or numerical code should begin until a coordinator chooses
between (A) non-wildfire surface ozone health and (B) labor productivity, and
approves the endpoint reconciliation. For ozone, the next safe artifact is a
source/provenance manifest covering climate-chemistry concentration fields,
baseline mortality/morbidity rates, concentration-response functions,
population, and valuation—without coefficients filled by assumption.
