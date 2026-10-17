# Literature and integration audit

## Scope and GIVE coverage

This project concerns only additional atmospheric CO2 caused by climate-driven Amazon forest carbon loss. It does not monetize forests, biodiversity, hydrology, agriculture, or wildfire, and it does not overlap the separate market-forestry or wildfire-carbon projects by design.

The published GIVE implementation uses MimiFAIR v1.6.2. Its CO2 cycle includes a temperature-dependent uptake term, so it already represents a generic climate-carbon feedback. It has no named Amazon forest stock, stochastic dieback state, or Amazon emissions input. EPA/NCEE's 2025 SCC appendix independently describes explicit Amazon dieback as absent from FaIR 1.6.2. Those facts establish a structural omission, but not a zero-overlap conclusion: adding Amazon carbon loss without adjusting the generic land sink may count part of the same response twice.

## Shortest executable literature path

Dietz et al. (2021; DOI 10.1073/pnas.2103081118) is the strongest directly executable benchmark located. The open META-2021 code implements:

1. An annual hazard after GMST exceeds 1 degree C: `1 - exp[-b * max(0,T-1)]`, with `b=0.00163443 / degree C`.
2. A persistent trigger once a common uniform draw falls below the annual hazard.
3. A total release calibrated to 50 GtC, represented as 183.3333333 GtCO2.
4. A central 50-year release, with a triangular 10/50/250-year uncertainty distribution.
5. Amazon emissions from year t entering the carbon cycle in year t+1.

The authors report that Amazon alone raises expected SCC in their META main specification from $52.03 to $52.07/tCO2, a rounded 0.1%. This is a useful external benchmark only. It uses different baseline scenarios, climate and damage functions, discounting/welfare assumptions, pulse year, and stochastic structure from GIVE.

## Mechanical source findings

The vendored source exactly preserves the upstream commit and GPL-3.0 license. The deterministic 10-, 50-, and 250-year calibrations divide the stock exactly into annual installments. In Monte Carlo mode, however, the duration is a continuous triangular draw. The release condition pays a full installment while cumulative release remains below `max - 0.01`; therefore `ceil(duration)` installments can be paid and total release can exceed the nominal stock whenever duration is not an integer. This must be fixed with a final `min(installment, remaining_stock)` payment and validated before coupling.

The benchmark triggers in 2090 and releases 3.666666667 GtCO2/y for the central 50-year case. The source carbon-cycle component adds the prior year's Amazon release, confirming a one-year lag.

## Why the GMST hazard is only a benchmark

Recent climate literature does not support treating GMST as a complete physical description of Amazon dieback. Local precipitation, drought and soil moisture, CO2 fertilization, vegetation mortality, land use, and fire affect resilience and carbon flux. Tanaka et al. (2024; DOI 10.1038/s41467-024-51474-8) constrain continuous climate-driven Amazon carbon loss in CMIP6, explicitly excluding CO2-fertilization and land-use effects; their estimate is valuable as a process benchmark, but is not an annual tipping-hazard recursion. Bochow and Boers (2021; DOI 10.1038/s41612-021-00162-1) further demonstrates the importance of precipitation for Amazon land-surface response and dieback probability.

A defensible implementation should therefore report at least two structurally distinct cases: the legacy META stochastic tipping benchmark and a continuous climate-carbon-loss sensitivity grounded in current CMIP6 evidence. Neither is authorized here as a production GIVE estimate until the overlap boundary is solved.

## Marginal-pulse contract

For each Monte Carlo draw, baseline and pulse runs must share the same FaIR parameters, Amazon parameters, and annual trigger uniforms. Each run must recursively use its own temperature path. Historical trigger status must be conditioned identically through the pulse year. Amazon emissions generated in t enter FaIR in t+1. Outputs must be converted from GtCO2/y to the target FaIR carbon unit exactly once.

The comparison must pass pre-pulse identity, zero-feedback identity, mass conservation, pulse-size convergence, time-step, and horizon tests. A combined EPA permafrost-plus-Amazon percentage is prohibited because it does not identify the Amazon contribution.

## Decision

The literature supports an executable readiness benchmark, not an immediate GIVE SCC. The current status remains fail closed until land-carbon overlap, updated hazard uncertainty, historical conditioning, exact stock conservation, and recursive matched-pulse behavior are validated.

