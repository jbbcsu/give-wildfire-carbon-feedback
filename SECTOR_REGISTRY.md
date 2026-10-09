# GIVE damage-sector evidence registry

Status date: 9 October 2026. Values below retain their source configuration and
are not mutually additive unless explicitly stated.

| Pathway | Current evidence | Estimate/status | Integration state | Fastest defensible next step |
|---|---|---|---|---|
| Temperature mortality | Existing GIVE sector | Existing model component | Baseline | Preserve; audit overlap with labor and air pollution |
| Agriculture, total | Moore et al. (2026), DOI [10.1038/s41558-026-02749-z](https://doi.org/10.1038/s41558-026-02749-z) | Published 2025 partial SCC: $29/tCO2 | Official code acquired; exact 10,000-draw reproduction in progress | Reproduce before replacing legacy GIVE agriculture |
| Agriculture, precipitation quantity | Original isolated precipitation project | Preliminary central fixed-adaptation maize quantity channel: -$0.00610/tCO2 in 2020 USD at 2%; not total precipitation-agriculture damages | Original bounded estimate; non-additive to total agriculture | Complete drought/timing, irrigation, other crops, and replacement design |
| Agriculture, drought/timing/extremes | Original global and U.S. validation tracks | No promoted global SCC | Open research gap with empirical scaffolding | Retain only features with incremental out-of-sample value; benchmark PDSI/scPDSI and SPEI |
| Labor productivity | Moore et al. (2026) | Published 2025 partial SCC: $41/tCO2; 90% interval $1–108 | Official MIT code and arrays acquired; exact reproduction in progress | Match published 10,000-draw result and audit overlap |
| Fisheries market + nutrition | Bastien-Olvera et al. (2025/2026), DOI [10.1038/s41558-025-02533-5](https://doi.org/10.1038/s41558-025-02533-5) | Published benchmark: $22.09755/tCO2 ($0.05704 market; $22.04051 nutrition/use) | External, non-additive; mortality/nutrition and market overlap unresolved | Reproduce country paths and allocate endpoints once |
| Biodiversity nonuse | Published benchmark audited in isolated biodiversity project | Approximately $8/tCO2; published external benchmark | External, non-additive; regional coefficients/joint draws unavailable locally | Obtain coefficients and joint uncertainty, then audit overlap with reef/nonuse values |
| Coastal flooding | Existing GIVE/CIAM sector | Existing model component | Baseline | Preserve; exclude coastal protection from new flood and reef modules |
| Inland riverine/pluvial flooding | Literature/data screen only | No promoted SCC | Open research gap | Defer until precipitation agriculture replacement is stable |
| Building energy | Existing GIVE sector | Existing model component | Baseline | Preserve; audit adaptation-energy overlap with labor heat exposure |
| Surface ozone health | RFF priority pathway; no local SCC | No promoted SCC | Open research gap | Published-response/source audit with wildfire and crop effects excluded |
| Wildfire smoke/CO2 feedback | Separate wildfire project | Separate paper and codebase | Excluded from this repository | Cite final published/replicated result only; never modify its files here |
| Coral reef services | RFF priority pathway | No mutually exclusive local SCC | Open research gap | Allocate fisheries, nonuse, coastal protection, and tourism once |
| Municipal water systems | Future drought/water-supply pathway | No promoted SCC | Deferred research gap | After agricultural drought: screen scarcity, treatment, pumping, and infrastructure costs while excluding household adaptation already captured elsewhere |

## Authorized integration order

1. Replace legacy GIVE agriculture and add labor using the reproducible Moore
   et al. package.
2. Add the separate wildfire-carbon feedback only after importing its final
   reviewed marginal-damage output through a documented interface; the
   wildfire codebase remains untouched.
3. Add fisheries after reproducing the published paths and allocating its
   nutrition/mortality and market endpoints against existing GIVE sectors.
4. Estimate drought and other precipitation-pattern effects on agriculture as
   an incremental correction to the Moore agriculture replacement, not as a
   second total agriculture sector. Total precipitation, timing, dry spells,
   extremes, and drought indices compete in pre-specified models; irrigation
   is treated explicitly where data permit.
5. Develop municipal drought and water-supply damages later.
6. Screen the remaining RFF-identified omissions, prioritizing surface ozone,
   biodiversity, inland extreme-weather/flood damages, coral reefs, and other
   ocean services. Only reproducible, overlap-cleared pathways enter a combined
   SCC.

## Non-negotiable combination rule

The synthesis will report three quantities rather than one premature grand
total: (i) the existing GIVE SCC; (ii) the SCC after locally replicated,
overlap-cleared replacements/additions; and (iii) a non-additive evidence
envelope containing original bounded estimates and published external
benchmarks. This prevents missing sectors from being treated as zero without
pretending that overlapping partial SCCs can be summed.
