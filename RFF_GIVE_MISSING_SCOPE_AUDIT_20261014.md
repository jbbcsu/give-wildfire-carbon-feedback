# RFF/GIVE missing-scope reconciliation

Status date: 14 October 2026. This is a scope and reproducibility audit, not a
damage estimate or an authorization to add any component to GIVE.

## Authoritative scope

The original RFF-led GIVE paper says that its four damage sectors were selected
because global coverage, regional disaggregation, and monetization made them
readily incorporable. It explicitly identifies biodiversity, labour
productivity, conflict, and migration as examples of still-missing categories
([Rennert et al. 2022](https://doi.org/10.1038/s41586-022-05224-9)). The current
umbrella already tracks biodiversity and labour productivity, but it did not
name conflict or non-coastal migration.

For the fuller crosswalk, this audit uses Table 3.2.1 of EPA's official 2023
SC-GHG report and Table A.1 of the EPA National Center for Environmental
Economics working paper hosted by RFF. The latter explicitly adapts the former
and compares GIVE/DSCIM with FrEDI v4.1
([EPA 2023, pp. 87-92](https://www.epa.gov/system/files/documents/2023-12/epa_scghg_2023_report_final.pdf);
[Kopits et al. 2025, Tables A.1-A.3](https://media.rff.org/documents/NCEE-economic-damages-climate-change-jan2025.pdf)).
RFF labels the working paper as an external EPA resource, so it is not described
here as an RFF-authored publication.

These sources confirm that GIVE contains mean-temperature mortality, crop
agriculture, building heating/cooling expenditure, and sea-level-rise damages.
They also distinguish partial representation from absence. A registry row for
one endpoint therefore does not close its entire parent category.

## Reconciliation result

The current umbrella already tracks the four GIVE sectors plus labour
productivity, precipitation/drought agriculture, fisheries, biodiversity
nonuse, inland flooding, surface ozone, non-wildfire PM2.5, wildfire smoke and
carbon, coral services, and municipal water. The authoritative scope still
contained the following unnamed or incompletely named pathways:

| Authoritative category | Umbrella status before this audit | Scope conclusion |
|---|---|---|
| Infectious disease and other morbidity | Not named | Gap. FrEDI contains selected CONUS endpoints, not a global health sector. |
| Displacement and migration | Coastal adaptation/migration only inside CIAM | Gap outside the existing coastal model. |
| Human capital | Not named | Gap. Labour productivity does not imply education or lifetime human-capital effects. |
| Energy production and provision | Building energy only | Gap. Generation, capacity, transmission, distribution, and interruption costs are distinct. |
| Heat- and weather-related transport infrastructure | Inland flood row only | Gap. Road-surface and rail-buckling costs are not inland flooding. |
| Animal and livestock health/productivity | Crop agriculture only | Gap. No livestock transfer has been screened. |
| Forestry; timber, pulp, and paper | Not named | Gap. Wildfire carbon is not forestry welfare. |
| Tourism, recreation, aesthetics outside coral tourism | Coral residual-services row only | Gap. Winter recreation, terrestrial recreation, and scenic/cultural values remain outside it. |
| Other provisioning, regulating, and cultural ecosystem services | Biodiversity nonuse and bundled coral services only | Gap. Pollination, water filtration, pest/flood/fire mitigation, medicinal resources, and cultural heritage remain unrepresented. |
| Crime | Not named | Gap. |
| National security/conflict | Not named | Gap; also one of the RFF-led GIVE paper's explicit examples. |
| Trade, logistics, and supply-chain spillovers | Not named | Gap. |
| Large-scale Earth-system feedbacks beyond the separate wildfire-carbon project | Not named | Cross-module gap rather than a damage sector. Permafrost and Amazon carbon feedbacks require a separate climate-module boundary. |

The registry now names the three fastest screenable sector candidates and
points to the machine-readable crosswalk. The remaining gaps stay in this
bounded deferred register; none is silently treated as zero.

## Ranked fast-route candidates

Ranking is qualitative and based on four requested criteria. “Marginal-pulse
compatibility” means that a released response can be run on matched baseline
and one-ton-pulse climate paths; it does not mean that a GIVE result has been
computed. “Overlap risk” is the risk before a boundary audit.

| Rank | Candidate | Expected materiality | Public reproducibility | Marginal-pulse compatibility | Overlap risk | Bounded next gate |
|---:|---|---|---|---|---|---|
| 1 | Heat-driven road and rail infrastructure | High relative to the other screened CONUS omissions: Kopits et al. identify road and rail heat-stress impacts among FrEDI pathways with large regional damages | High for a CONUS screen: EPA FrEDI v4.1.1 is a pinned, open R package with code, packaged response data, documentation, and tests | High: FrEDI accepts annual temperature paths, and EPA documents its use with a one-ton GHG perturbation | Medium | Reproduce road-repair, road-user, rail-replacement, and rail-delay annual outputs separately; exclude coastal, high-tide, hurricane, urban-drainage, and inland-flood endpoints; audit whether time-delay valuation overlaps labour losses. |
| 2 | Electricity production/provision and transmission/distribution | Medium, with multiple capital, fuel, O&M, capacity, efficiency, repair, and interruption channels | High for a CONUS screen through the same pinned FrEDI release | High for temperature-mediated endpoints under matched paths | Medium-high | Run only supply and grid endpoints; exclude building heating/cooling expenditure already in GIVE; establish whether interruption, lost-capacity, and repair-cost lines are additive. |
| 3 | Climate-sensitive infectious disease and selected morbidity | Materiality is unresolved globally; the released endpoints are narrower than the authoritative category | High for the selected CONUS FrEDI endpoints (Valley fever and vibriosis; Lyme is documented separately), but not for global extrapolation | High for FrEDI's temperature-response endpoints | Medium-high | Reproduce mortality and morbidity separately, exclude all-cause heat and air-pollution outcomes, and leave suicide closed because FrEDI v4.1.1 explicitly warns of possible double counting with default temperature mortality. |

The common executable source is EPA FrEDI release v4.1.1, tag commit
`08ead1b64821acd0ff0ee95fdf662a1a73f242e1`, under an MIT-style license plus
EPA disclaimer
([release](https://github.com/USEPA/FrEDI/releases/tag/v4.1.1),
[repository](https://github.com/USEPA/FrEDI),
[technical documentation](https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=P101BGD6.txt)).
FrEDI is CONUS-only. Its public response functions may support a U.S. component
or a reproducibility benchmark; they do not support coefficient transfer to the
rest of the world.

## Important non-ranked pathway

Permafrost-thaw and Amazon-dieback carbon feedbacks have a stronger official
materiality signal than several sector candidates and are naturally compatible
with paired climate runs. They are not ranked as a damage sector. Kopits et al.
describe a temperature-to-additional-emissions feedback into FaIR, while
excluding direct biodiversity, ecosystem-service, erosion, and infrastructure
damages. The paper says RFF developed code, but this audit did not locate a
pinned, licensed public implementation linked from the paper. The next gate is
therefore an exact code/data/license request, not reimplementation from prose.
Any future module must also remain distinct from the separate wildfire-carbon
project.

## Why the other gaps are not fast routes

The authoritative sources establish importance or omission, not a transferable
annual global welfare package. Conflict/security, migration, human capital,
livestock, forestry, broad recreation, ecosystem services, crime, and
trade/logistics remain scope entries until a primary source supplies geographic
coverage, monetized annual paths, uncertainty, licensing, and a matched
baseline/pulse interface. No coefficient, U.S.-to-global scaling factor, or
sector share is inferred in this audit.

The machine-readable record is
[`data/provenance/rff_give_missing_scope_audit_20261014.json`](data/provenance/rff_give_missing_scope_audit_20261014.json).
