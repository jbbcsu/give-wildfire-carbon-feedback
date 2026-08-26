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
| RFF (2024), *Improving the Treatment of Catastrophic Climate Risk in the Social Cost of Carbon*, ocean systems report, https://media.rff.org/documents/Report_24-17_IX6Vq3m.pdf | Authoritative audit of ocean omissions in GIVE and candidate fisheries, coral, and acidification pathways; recommends integrated modeling and makes management, migration, aquaculture, and data constraints explicit. | A research roadmap rather than a calibrated pulse-response dataset; it does not justify a numeric fisheries damage function by itself. |

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

## Transferability conclusion

The literature supports a global biophysical ensemble and makes a welfare
translation scientifically defensible in principle. It does **not** support
transferring the US fisheries surplus response, valuing global projected catch
at observed prices, or interpreting FishMIP biomass as damages. The first
executable global version therefore requires either licensed model outputs plus
an identified surplus layer or auditable output from an integrated global
fishery model. The exact interface and exclusions are fixed in
[`MODEL_CONTRACT.md`](MODEL_CONTRACT.md) so source acquisition can proceed
without silently choosing coefficients.

## ISIMIP3b source-discovery result (2026-08-25)

The public ISIMIP API has a compact, balanced `tc` catalogue: BOATS and
EcoOcean crossed with GFDL-ESM4 and IPSL-CM6A-LR, each with historical and
historical preindustrial-control records plus future preindustrial-control,
SSP1-2.6, and SSP5-8.5 records. All 20 records report public, unrestricted CC0
access and one monthly global NetCDF file. This makes a bounded multi-model
biophysical benchmark feasible, subject to local checksum and content checks
after acquisition. It remains structurally narrow (two ecosystem models and
two forcings), contains no SSP3-7.0 `tc` record in the audited query, and does
not identify welfare or a marginal emissions pulse. The catalogue therefore
does not change the no-numeric-damage decision.

## Exclusion gate

No coral-reef tourism, nonuse value, or reef-mediated coastal protection enters
this initial module. No fish-food loss is stacked onto a terrestrial
agriculture/food-price welfare response without an explicit general-equilibrium
or overlap treatment.
