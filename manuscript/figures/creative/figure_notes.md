# Figure Notes

These figures use `/output/wildfire_temperature_feedback_mcs_100_paired/all_scc_samples.csv` and focus on the 2.0% discount-rate case.

## SCC distribution figures

- `figure_scc_ridgeline_2pct.svg` shows full SCC distributions for the paired 100-run validation sample. Vertical lines mark means; open circles mark medians; horizontal bars mark the 5th-95th percentile span.
- `figure_paired_scc_delta_2pct.svg` subtracts each paired baseline draw from the corresponding wildfire-feedback draw. This is the cleanest visual for the incremental SCC effect because common RFF-SP, FAIR, and discounting draws are held fixed within each trial.
- `figure_scc_exceedance_2pct.svg` shows tail probabilities. This makes the stress scenarios' upper-tail effects easier to see than a single mean.
- `figure_scc_threshold_tiles_2pct.svg` summarizes the same tail information at four thresholds.

## Spatial proxy maps

The maps are not GIVE-native regional damage outputs. The current wildfire extension adds global CO2 to FAIR. That higher global CO2 stock then affects global forcing, temperature, and damages. The model run does not allocate the incremental SCC geographically.

- `figure_fire_source_proxy_map.svg` encodes a hand-auditable proxy for where additional climate-driven fire CO2 is most likely to originate. Boreal Canada and Siberia/Russia are weighted highest because this first-pass experiment is motivated by high-latitude carbon-stock and extreme-fire evidence.
- `figure_residual_source_proxy_map.svg` downweights gross fire regions where AFOLU/inventory overlap, regrowth, or gross-vs-net ambiguity creates high double-counting risk.
- `figure_global_fire_mechanism_map.svg` is a mechanism schematic: local source proxies feed a global atmospheric CO2 stock. Blue receptor rings are qualitative reminders that climate damages are distributed globally; they should not be cited as regional estimates.

The spatial proxy weights are saved in `spatial_proxy_regions.csv` so they can be replaced by gridded RESFire, GFED, FireMIP, or CMIP/land-model outputs in the next iteration.

## Source anchors

- Byrne et al. 2024, `Nature`, estimates the 2023 Canadian fires at 647 TgC and links the event to hot-dry conditions that climate projections suggest may become typical by the 2050s under SSP2-4.5: https://www.nature.com/articles/s41586-024-07878-z
- Chen et al. 2026, `Nature Geoscience`, uses CESM-RESFire and reports projected fire-emissions feedback quantities, including a 19% burned-area increase, 106% reactive-carbon increase, and a fire-CO2 burden-change calculation for 2000s-2050s: https://www.nature.com/articles/s41561-026-01926-1
- Jones et al. 2019, `Nature Geoscience`, is included as a gross-vs-net caution because it emphasizes global fire carbon emissions, pyrogenic carbon, and carbon-accounting ambiguity: https://www.nature.com/articles/s41561-019-0403-x
