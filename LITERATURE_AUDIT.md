# Initial fisheries evidence audit

## Decision at this stage

An initial global fisheries damage function is feasible to research but not
ready to calibrate. Existing studies support climate-sensitive changes in
biomass/catch potential and demonstrate why mean warming alone is inadequate.
They do not supply a plug-in global marginal-welfare function that resolves
management, migration, price/substitution, and data limitations.

| Evidence | Usable contribution | SCC limitation / required treatment |
|---|---|---|
| Cheung et al. (2021), *Science Advances*, doi:10.1126/sciadv.abh0895 | Integrated global climate--biodiversity--fisheries--economic analysis of marine high-temperature extremes; motivates retaining extremes alongside mean ocean change. | Reports biomass/catch-potential and economic impacts under scenarios; not a matched small-CO2-pulse welfare function. Management assumptions and welfare translation must be exposed. |
| Blanchard et al. (2024), *Earth's Future*, doi:10.1029/2023EF004402 | FishMIP 2.0 ensemble architecture and explicit structural uncertainty. | Notes limited standardized historical fishing data, uncertain coastal/shelf projections, and inconsistent fishing representation; cannot be treated as validated welfare output. |
| Narita & Rehdanz (2016), *Ecological Economics*, doi:10.1016/j.ecolecon.2016.04.012 | Ecological-economic consumer-welfare approach for reef fisheries and warming/acidification. | Reef-associated branch only; overlaps potentially with future coral-reef services and needs separate accounting. |
| Moore et al. (2021), *Climate Change Economics*, doi:10.1142/S2010007821500020 | Consumer-surplus modeling for 16 US fisheries; useful welfare validation benchmark. | US-specific and not globally transferable. |

## Candidate primary architecture

1. Use an ocean-impact ensemble to map matched baseline/pulse climate paths
   into regional/species catch-potential changes, retaining mean warming,
   marine heat extremes, acidification, oxygen/productivity where available.
2. Map catch changes into welfare using an explicit demand/supply or trade
   model. Report producer and consumer surplus separately; do not equate
   landings revenue with welfare.
3. Treat harvest control, fishing effort, aquaculture, range shifts, and
   protein substitution as scenario/adaptation inputs with uncertainty.
4. Aggregate only after resolving country/EEZ allocation and trade incidence.

## Exclusion gate

No coral-reef tourism, nonuse value, or reef-mediated coastal protection enters
this initial module. No fish-food loss is stacked onto a terrestrial
agriculture/food-price welfare response without an explicit general-equilibrium
or overlap treatment.
