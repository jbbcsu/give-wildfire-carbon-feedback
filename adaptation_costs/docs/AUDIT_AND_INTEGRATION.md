# Adaptation-cost audit and integration rules

## Finding

The cross-sector problem is not a universal omission. It has two opposite forms:

1. **Unpriced adaptation:** the precipitation-agriculture `trend` and `upper` scenarios attenuate the estimated climate response but return a zero adaptation-cost share. Their outputs are residual-damage sensitivities, not net welfare or net SCC estimates.
2. **Already-priced adaptation:** FrEDI Roads, Rail, and electricity transmission/distribution totals include specified repair, capital, sensor, delay, operations, or maintenance costs. GIVE's CIAM coastal `OptimalCost` includes adaptation and residual damages. Adding a generic cost term would double count.

Inland flooding is neither: its current partial SCC assumes no additional adaptation beyond existing protection and therefore remains an unadapted-damage result.

## Exact source audit

### Precipitation agriculture

`precipitation_scc/src/AdaptationScenarios.jl` creates linear damage-response attenuation for `trend` (0.003 per year, capped at 35%) and `upper` (0.007 per year, capped at 70%). The same file returns arrays of zeros from `adaptation_cost_share`. The scenario configuration calls both controls uncalibrated and labels `upper` an upper-bound scenario rather than a forecast. Fixed adaptation is the only current case not requiring a new implementation-cost schedule.

### Roads and Rail

Neumann et al. (2021) explicitly itemize costs by adaptation scenario. Proactive Roads includes upfront strengthening, repairs, and delays; Reactive Roads includes repairs and delays. Proactive Rail includes purchasing, installing, and maintaining track-temperature sensors and related software plus risk-based delay costs; Reactive Rail includes track repair and blanket-speed-restriction delays. EPA FrEDI preprocesses these source totals. Therefore, the current FrEDI partial-SCC outputs must be treated as cost-inclusive but component-inseparable.

One nuance is important: FrEDI subtracts variant-specific baselines before constructing climate response surfaces. The output is the climate-attributable change in the scenario total, not the entire infrastructure program budget. That is appropriate for marginal climate accounting, but it means the absolute adaptation budget cannot be reconstructed from the released response surface.

### Electricity transmission and distribution

Fant et al. (2020) state that reported Reactive and Proactive totals include adaptation costs and measure changes relative to a no-climate-change scenario. FrEDI carries those totals into the `ElecTD` surfaces. A second adaptation charge is prohibited. This does not resolve the existing hazard-overlap gate for coastal substations, wildfire, or vegetation management.

### Inland flooding

The existing contract fixes current property values and assumes no additional adaptation beyond currently implemented protection. Its partial SCC is not a net-adaptation result. Future protection scenarios would require matched protection cost and residual loss paths.

### GIVE coastal adaptation

MimiCIAM explicitly calculates no-adaptation, protection, and retreat costs, including protection construction and maintenance, relocation, land and wetland losses, storm capital loss, and mortality. GIVE selects an option by discounted cost and uses `OptimalCost` in its SCC calculation. A separate coastal adaptation-cost module would duplicate those costs.

Outside CIAM, the inspected GIVE source contains no separate generic adaptation-cost component. Empirical damage functions may reflect behavior present in their estimation samples, but the source does not separate the cost of that behavior; this ledger does not invent it.

## Published agriculture cost evidence

The strongest readily reusable open cost scale located is the OECD's 2014 assessment. It estimates average annual 2010–2050 spending of USD 15.7–20.2 billion (2005 USD) in OECD countries for additional agricultural R&D plus irrigation-efficiency improvement. The authors explicitly warn that the costs do not correspond exactly to the adaptation measures in their modeled yield scenarios and should be treated as orders of magnitude.

This range is therefore recorded only as a bounded external benchmark. It cannot be divided among crops or countries, assigned to `trend` or `upper`, converted into an SCC, or interpreted as global. Minoli et al. (2022) provides global crop-calendar/cultivar yield benefits but no matched implementation-cost schedule, so it cannot close the gap.

## No-double-counting interface

Every sector-scenario must carry one of the ledger's five cost treatments. Integration behavior is mechanical:

- `not_applicable_baseline`: retain as unadapted/current-practice damage; do not add new adaptation spending.
- `explicitly_zero_unpriced`: allow sensitivity reporting, but block net-damage and net-SCC labels.
- `embedded_in_total`: use the source total once; prohibit any additional adaptation-cost term.
- `explicit_modeled`: use the model's total-cost output once.
- `unresolved`: block net claims until documentation or a new model resolves cost coverage.

For marginal SCC work, an annual adaptation cost level cannot be bolted onto an existing SCC. The same decision rule and cost function must be evaluated under matched baseline and marginal CO2-pulse climate paths. The SCC contribution is the discounted difference in **total** costs, including both residual damage and adaptation expenditure.

## Shortest defensible agriculture path

1. Keep `fixed` as the primary agriculture case until costs are identified.
2. Relabel current `trend` and `upper` outputs as gross residual-damage sensitivities.
3. Replace the generic attenuation schedules with named adaptation packages: at minimum calendar/cultivar change and irrigation expansion/efficiency must remain separate.
4. For each package, estimate region-crop-year adoption, capital cost, operating cost, water/energy cost, lifetime, and yield-response effect from compatible evidence.
5. Run adoption and costs on both baseline and pulse paths with identical decision rules; difference annual total costs.
6. Test overlap with agricultural market impacts, water supply, energy demand, and public R&D. Only then authorize a net adaptation SCC.

No currently available global evidence maps the OECD aggregate cost range to the existing attenuation multipliers. That mapping is an empirical research need, not a parameter choice that can be safely assumed.
