# Initial fisheries evidence audit

## Decision at this stage

An initial global fisheries damage function is feasible, and a newly audited
published SCC implementation now provides a direct replication benchmark.
It does not eliminate the project's welfare and overlap problems: its market
pathway is profit-based and augmented with regional output multipliers rather
than an explicit consumer-plus-producer-surplus model, while most of its
fisheries SCC comes from a separate nutrition/mortality valuation pathway.

| Evidence | Usable contribution | SCC limitation / required treatment |
|---|---|---|
| Bastien-Olvera et al. (2025/2026), *Nature Climate Change*, doi:10.1038/s41558-025-02533-5; code and source data at https://github.com/berbastien/blue-scc | Open, country-level fisheries and nutrition damage-function workflow plus RICE50+ SCC integration. The audited Figure 4 source data report a 2020 fisheries SCC of $22.09755/tCO2: $0.05704 market and $22.04051 non-market use/nutrition under the paper's baseline settings. This is the required published benchmark for GIVE. | The market code starts from Free et al. profit projections under full adaptation, compares them with an RCP2.6 path, applies regional output multipliers, and fits country GDP-share slopes to temperature. It is not consumer plus producer surplus. The nutrition result depends on nutrient-availability, relative-risk, dependence, substitution, and VSL assumptions. The audited repository has no explicit root license file, so code/data may be inspected but are not copied into this project pending license clarification. |
| Cheung et al. (2021), *Science Advances*, doi:10.1126/sciadv.abh0895 | Integrated global climate--biodiversity--fisheries--economic analysis of marine high-temperature extremes; motivates retaining extremes alongside mean ocean change. | Reports biomass/catch-potential and economic impacts under scenarios; not a matched small-CO2-pulse welfare function. Management assumptions and welfare translation must be exposed. |
| Blanchard et al. (2024), *Earth's Future*, doi:10.1029/2023EF004402 | FishMIP 2.0 ensemble architecture and explicit structural uncertainty. | Notes limited standardized historical fishing data, uncertain coastal/shelf projections, and inconsistent fishing representation; cannot be treated as validated welfare output. |
| Narita & Rehdanz (2016), *Ecological Economics*, doi:10.1016/j.ecolecon.2016.04.012 | Ecological-economic consumer-welfare approach for reef fisheries and warming/acidification. | Reef-associated branch only; overlaps potentially with future coral-reef services and needs separate accounting. |
| Moore et al. (2021), *Climate Change Economics*, doi:10.1142/S2010007821500020 | Consumer-surplus modeling for 16 US fisheries; useful welfare validation benchmark. | US-specific and not globally transferable. |
| RFF (2024), *Improving the Treatment of Catastrophic Climate Risk in the Social Cost of Carbon*, ocean systems report, https://media.rff.org/documents/Report_24-17_IX6Vq3m.pdf | Authoritative audit of ocean omissions in GIVE and candidate fisheries, coral, and acidification pathways; recommends integrated modeling and makes management, migration, aquaculture, and data constraints explicit. | A research roadmap rather than a calibrated pulse-response dataset; it does not justify a numeric fisheries damage function by itself. |

## Revised architecture

1. Reproduce the published Blue-SCC fisheries coefficients and sectoral SCC as
   a literature benchmark, conditional on obtaining clearly licensed inputs.
2. Keep the FishMIP BOATS/EcoOcean ensemble as an independent biophysical
   structural check. Do not map its total-catch density mechanically into the
   published country-profit coefficients; the inputs and estimands differ.
3. Separate market profit, consumer surplus, producer surplus, and nutrition
   mortality. Only additive components with explicit overlap rules may enter
   GIVE; regional output multipliers are a sensitivity, not an automatic
   welfare expansion.
4. Pair the selected damage function with matched GIVE baseline and one-ton
   CO2-pulse climate paths. Scenario contrasts remain presentation benchmarks,
   not substitutes for the marginal pulse.

## Transferability conclusion

The literature now supplies a published global fisheries-to-SCC benchmark, but
not a universal resolution of economic welfare. It still does **not** support
transferring the US fisheries surplus response, valuing FishMIP total catch at
observed prices, or calling gross revenue welfare. The first executable GIVE
version should therefore replicate the published country damage coefficients
as a benchmark, then test a stricter market-welfare treatment separately. The
exact interface and exclusions are fixed in
[`MODEL_CONTRACT.md`](MODEL_CONTRACT.md) so source acquisition can proceed
without silently choosing coefficients.

The frozen external-repository audit is documented in
[`BLUE_SCC_FISHERIES_BENCHMARK_AUDIT.md`](BLUE_SCC_FISHERIES_BENCHMARK_AUDIT.md)
and its aggregate-only receipt. It copies no country coefficient or external
source file.

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
