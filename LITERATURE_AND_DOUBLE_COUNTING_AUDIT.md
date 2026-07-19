# Literature And Double-Counting Audit

## Bottom Line

The GIVE implementation does not expose a wildfire, biomass-burning, or non-anthropogenic CO2 emissions variable. It uses an aggregate RFF-SP global CO2 emissions pathway in GtC/yr. The RFF-SP elicitation documentation is broad enough that some wildfire, AFOLU, natural-stock, or negative-emissions expectations may be embedded in that aggregate pathway, but the released model input cannot identify them.

Therefore:

- Adding gross wildfire emissions is not double-counting safe.
- Adding a residual net persistent fire-carbon feedback with an explicit not-already-embedded fraction is the most defensible first-pass extension.
- Gross RESFire-style cases should be labeled stress tests.

## Relevant Literature

### Rennert et al. 2022 / GIVE

Rennert et al. use RFF-SP socioeconomic and emissions projections, FaIR v1.6.2, BRICK sea-level rise, sectoral damage functions and stochastic discounting. The paper states that RFF-SP experts provided uncertainty ranges for fossil/process CO2 and for changes in natural CO2 stocks and negative-emissions technologies. It also states that FaIR is emissions based and has state-dependent carbon uptake.

Interpretation for this project:

- GIVE is physically capable of responding to added CO2 emissions.
- GIVE does not separately identify wildfire-carbon feedbacks.
- If fire-carbon feedbacks are in the RFF-SP expert forecasts, they are inside aggregate CO2.

### RFF-SP Appendix

The RFF Future Emissions Survey asked experts about broad non-overlapping categories. The natural-stock / AFOLU / NETs category is broad. It is not an itemized wildfire forecast. I did not find a source that says, expert by expert, whether wildfire, boreal fire, peat fire or climate-driven biomass burning was included.

Interpretation:

- We cannot say wildfire emissions are definitely absent.
- We also cannot say they are explicitly represented.
- The appropriate experiment is residual sensitivity, not unconditional addition.

### Qiu et al. 2026

Qiu et al. add climate-induced wildfire smoke mortality damages to GIVE. They estimate a partial U.S. domestic SCC contribution from wildfire smoke mortality and show that this omitted damages channel can be large. Their extension is a damage function linked to GMST and smoke exposure, not a carbon-cycle CO2 feedback.

Interpretation:

- Their work supports the idea that wildfire-related SCC channels are underrepresented.
- Their mechanism should not be conflated with adding fire CO2 to the carbon cycle.
- A complete wildfire SCC accounting would need both smoke damages and fire-carbon feedbacks, carefully linked to avoid double counting the same climate-fire relationship.

### Byrne et al. 2024, Canadian Wildfires

Byrne et al. estimate 2023 Canadian fire carbon emissions of 647 TgC, with top-down estimates far above the 2010-2022 average. They emphasize that hot-dry conditions drove the event and that 2023-like temperatures may become typical by the 2050s under SSP2-4.5.

Interpretation:

- The magnitude of gross fire carbon can be enormous.
- Gross fire carbon is not automatically equal to a persistent net atmospheric perturbation.
- Large boreal fires motivate a feedback test, but do not by themselves justify adding all gross emissions to GIVE.

### Chen et al. 2026 / RESFire

Chen et al. use RESFire to estimate a first-half-century increase in fire CO2 burden and associated forcing, alongside atmospheric chemistry effects that amplify methane. Their reported gross CO2 increment is useful as a stress calibration.

Interpretation:

- RESFire provides an upper-bound style scale for climate-driven fire emissions.
- The gross increment is not adjusted for RFF-SP baseline embedding in GIVE.
- The gross and half-gross RESFire cases should be presented as stress tests.

### Jones et al. 2019 / Pyrogenic Carbon

Jones et al. report global fire emissions of about 2.2 PgC/yr and emphasize pyrogenic carbon formation. This supports the distinction between gross combustion emissions and net carbon-cycle effects.

Interpretation:

- A gross reference fire flux is useful for scaling.
- Net persistence must be modeled separately.

## What The Extension Does Correctly

- Inserts added fire CO2 into the annual CO2 emissions stream before FAIR's carbon cycle.
- Uses GtC/yr inside GIVE and converts from GtCO2 with 12/44.
- Uses lagged temperature so the feedback is endogenous but avoids an algebraic loop.
- Uses trial-specific 2020 temperature as the reference, so each Monte Carlo draw has its own baseline climate state.
- Separates residual scenarios from gross stress scenarios.
- Saves feedback parameter draws so assumptions are auditable.
- Reports paired SCC deltas, interval summaries and exceedance probabilities rather than only SCC levels.
- Separates physical fire-response uncertainty, net-persistence uncertainty and accounting/double-counting uncertainty.

## Parameter Uncertainty Interpretation

The current 100-draw validation is not a formal literature-derived posterior. It is a bounded uncertainty analysis.

- `beta` is the physical gross fire-carbon response to warming. The residual values are broad exploratory ranges informed by global fire-emissions inventories, heterogeneous fire-projection studies, boreal fire-carbon evidence and RESFire-style feedback studies.
- `phi_net` is the physical gross-to-net persistence share. It represents regrowth, future sink change, soil carbon, peat/permafrost vulnerability and pyrogenic carbon buffering.
- `phi_missing` is not physical. It is an accounting parameter for the share of net persistent fire carbon not already embedded in RFF-SP aggregate CO2. The public GIVE/RFF-SP files do not identify it.

The new figure/table outputs that document this are:

- `wildfire_extension/source_data/wildfire_parameter_uncertainty_framework.csv`
- `wildfire_extension/manuscript/figures/png_pdf/paired_scc_delta_interval_summary_2pct.csv`
- `wildfire_extension/manuscript/figures/png_pdf/wildfire_parameter_draw_summary.csv`
- `wildfire_extension/manuscript/figures/png_pdf/uncertainty_source_diagnostics_2pct.csv`

## What Remains Weak

- The residual distributions are stylized.
- The parameter ranges are bounded by literature and accounting judgement, but they are not a formal evidence synthesis.
- `phi_missing` cannot be empirically identified from public GIVE/RFF-SP inputs.
- The 100-draw diagnostic does not factorially separate GIVE uncertainty from wildfire-parameter uncertainty.
- The model is global, not spatially explicit.
- It lacks explicit boreal Canada/Russia regional dynamics.
- It omits fire CH4, CO, ozone chemistry, aerosols, albedo and smoke damages.
- It does not reconcile against a decomposed RFF-SP natural-stock/AFOLU baseline because no such released decomposition exists.

## Recommended Interpretation

Use the residual-medium and residual-high runs as first-pass uncertainty bounds for a potentially missing net wildfire-carbon feedback. Use RESFire half-gross and gross only to show how large the SCC effect could be if a large gross fire-carbon feedback were entirely persistent and absent from baseline emissions. Do not present the gross cases as policy central estimates.
