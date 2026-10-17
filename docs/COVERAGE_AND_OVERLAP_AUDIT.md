# Coverage and overlap audit

## GIVE boundary

GIVE's energy component implements Rode et al. (2021, DOI `10.1038/s41586-021-03883-8`): temperature-related expenditures for electricity and other direct fuels across residential, commercial, and industrial end uses. It does not represent physical grid repair/replacement or outage welfare. T&D direct asset costs are therefore distinct from the existing demand expenditure endpoint.

## Published executable evidence

Fant et al. (2020, DOI `10.1016/j.energy.2020.116899`) estimate climate impacts and adaptation costs for U.S. electricity transmission and distribution infrastructure. EPA FrEDI v4.1.1 publishes state-level response surfaces for six GCM patterns and three adaptation variants. The infrastructure receptors include lines, poles/towers, transformers, and substations. Monetized impacts are direct repair/replacement costs.

The implementation uses the exact released aggregate and FrEDI mechanics: zero anchor, piecewise-linear temperature response, linear extension of the last two nonmissing points to 30 C, and state/year electricity-demand growth scalars. It reports six GCMs without treating their range as a probability interval.

## Exclusions and limitations

- `ElecSD` is excluded because it bundles power demand with generation/capacity expansion, overlapping GIVE energy expenditure.
- ElecTD excludes outage costs and direct/indirect welfare losses from interrupted service; the result is not a reliability SCC.
- Mortality, labor effects, customer energy expenditures, and general property losses are excluded.
- FrEDI's released ElecTD response has no activity decomposition. The underlying aggregate spans extreme temperature, extreme rain, lightning, vegetation growth, wildfire activity, and coastal flooding, including coastal substations.
- The model omits some extreme-temperature peak-load stress and broader consumer/producer welfare effects.
- Results are CONUS-only and must not be globally scaled.

## Additivity gate

The endpoint is asset-specific and does not overlap Rode et al.'s customer energy expenditures. However, the released aggregate cannot isolate coastal substations, wildfire repair, or other hazard channels. Before addition to a combined GIVE expansion, an overlap matrix must verify that CIAM coastal capital, inland-flood infrastructure, wildfire direct damages, and other infrastructure modules exclude the same T&D assets—or obtain activity-resolved Fant/FrEDI outputs. Until then `additivity_to_give_authorized=false`.

## Sources

- Rennert et al. (2022), DOI `10.1038/s41586-022-05224-9`.
- Rode et al. (2021), DOI `10.1038/s41586-021-03883-8`.
- Fant et al. (2020), DOI `10.1016/j.energy.2020.116899`.
- U.S. EPA (2024), *Technical Documentation for FrEDI*.
- EPA `FrEDI_Data` commit `b506a3e0085bb446f56acc8c7076a1aea599fbb6`; FrEDI release v4.1.1.
