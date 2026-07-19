# Teaching Module: Auditing and Extending GIVE for Wildfire-Carbon Feedbacks

## Learning Goals

By the end of this module you should be able to:

- Trace how GIVE moves from emissions to concentrations, forcing, temperature, damages, and SCC.
- Explain why adding baseline emissions does not automatically change the SCC.
- Identify where double counting can enter when adding wildfire or biomass-burning CO2.
- Distinguish gross fire emissions from net persistent additions to atmospheric CO2.
- Run and interpret deterministic and Monte Carlo wildfire-feedback experiments.
- Distinguish source-side wildfire proxies from damage-side regional outputs.

## Readings

1. Rennert et al. (2022), "Comprehensive evidence implies a higher social cost of CO2," Nature.
   Focus on the methods sections for RFF-SPs, FaIR, damage functions, discounting, and the SCC calculation.

2. Rennert et al. (2021/2022), "The social cost of carbon: advances in long-term probabilistic projections of population, GDP, emissions, and discount rates," plus online appendix.
   Focus on the Future Emissions Survey categories, especially fossil/process CO2 and net CO2 from natural stocks, AFOLU, DAC, and BECCS.

3. Qiu et al. (2026), "Valuing wildfire smoke-related mortality benefits from climate mitigation."
   Focus on how the authors add wildfire smoke mortality as a damage component inside GIVE. This is a damages extension, not a carbon-cycle extension.

4. Byrne et al. (2024), "Carbon emissions from the 2023 Canadian wildfires."
   Focus on the distinction between large gross fire carbon emissions and their treatment in national inventories and land-carbon accounting.

5. Chen et al. (2026), "Climate feedback of forest fires amplified by atmospheric chemistry."
   Focus on the RESFire fire-emissions increment and the authors' treatment of fire CO2 burden and atmospheric chemistry feedbacks.

6. Jones et al. (2019), "Global fire emissions buffered by the production of pyrogenic carbon."
   Focus on why gross fire carbon is not identical to a net persistent atmospheric perturbation.

## Code Walkthrough

### 1. RFF-SP CO2 Input

Read:

```text
/Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/packages/MimiRFFSPs/src/components/SPs.jl
```

Key locations:

- Lines 76-78 define aggregate CO2, CH4, and N2O emissions variables.
- Lines 140-147 load `rffsp_co2_emissions.csv`, `rffsp_ch4_emissions.csv`, and `rffsp_n2o_emissions.csv`.

Then read:

```text
/Users/jbb/Dropbox/GIVE/.julia_depot_1_6/datadeps/rffsps_v5/README.md
```

Key locations:

- Lines 30-42 document the three emissions files and units.

The important audit finding is that the RFF-SP data package gives aggregate global CO2 in GtC/yr. It does not provide a released wildfire or biomass-burning split.

### 2. GIVE to FaIR

Read:

```text
/Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/packages/MimiGIVE/src/main_model.jl
```

Key locations:

- Lines 403-406 connect RFF-SP aggregate CO2 into `:co2_cycle`.
- Lines 416-422 explain that land-use CO2 is not broken out and the model leaves the FAIR land-use forcing path on SSP2-4.5 settings for RFF-SP runs.

### 3. Marginal CO2 Pulse

Read:

```text
/Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/packages/MimiGIVE/src/scc.jl
```

Key locations:

- Lines 789-807 create the base and marginal model.
- Lines 825-835 add the CO2 pulse before `:co2_cycle`, in GtC.

This matters because the wildfire feedback is inserted upstream of the pulse. Both base and pulse runs inherit the same baseline feedback, and only pulse-induced additional warming can create additional feedback emissions in the marginal run.

### 4. FaIR Carbon Cycle

Read:

```text
/Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/packages/MimiFAIRv1_6_2/src/components/co2_cycle.jl
```

Key locations:

- Lines 20-21 define annual CO2 emissions and temperature inputs.
- Lines 61-63 compute the state-dependent integrated impulse response using cumulative carbon uptake and lagged temperature.
- Lines 79-89 update atmospheric reservoirs and CO2 concentration.

The original GIVE model already has a carbon-cycle feedback in the sense that warmer, higher-carbon states affect CO2 uptake. It does not have an emissions feedback in which warming causes additional wildfire CO2 emissions.

### 5. New Wildfire Feedback

Read:

```text
/Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/wildfire_extension/WildfireGIVE.jl
```

Key ideas:

- Inputs are in GtC/yr when entering FaIR.
- Scenario assumptions are often easier to express in GtCO2/yr, so the module uses `12/44` to convert CO2 to C.
- The temperature-feedback component uses lagged temperature above each run's 2020 temperature.
- Added fire CO2 equals gross reference fire carbon times sensitivity per degree C times net-persistence and not-embedded fractions.

The equation is:

```text
E_fire,t = E_gross_reference * beta * max(T[t-1] - T[2020], 0) * phi_net * phi_missing
```

Where:

- `beta` is `sensitivity_per_c`.
- `phi_net` is `net_persistence_fraction`.
- `phi_missing` is `not_embedded_fraction`.

### 6. Scale and Regional Diagnostics

Read:

```text
/Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/wildfire_extension/run_regional_damage_map_diagnostics.jl
/Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/wildfire_extension/make_png_pdf_figures.R
```

Key ideas:

- The scale figure compares fire CO2 flows to annual baseline CO2 emissions and compares the induced atmospheric CO2-C stock to the baseline atmospheric stock. These are different denominators.
- The source proxy map is a hand-coded 0-1 index for plausible fire-carbon source regions. It is not an emissions inventory and not a model result.
- The damage map is a model diagnostic. Mortality and energy are country-level in GIVE; agriculture is FUND-region-level and is allocated to countries by GDP share.
- The old GIVE-region map is only an appendix diagnostic because it documents model aggregation rather than a scientific result.

## Exercises

1. Reproduce the deterministic scenario table.

```bash
/Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/wildfire_extension/run_temperature_feedback_mcs.sh 5
```

2. Open `scc_summary.csv` and compare mean and median SCC. Why are they different?

3. Change `not_embedded_fraction` in a deterministic scenario from 0.5 to 0.0. What should happen to the SCC and why?

4. Change `net_persistence_fraction` in a stress case from 1.0 to 0.1. Interpret the result as a regrowth correction.

5. Compare Qiu et al.'s smoke mortality extension to this carbon-cycle extension. Which one affects damages directly? Which one affects the physical climate state?

6. Compare `figure_fire_source_country_proxy_map.png` and `figure_incremental_damage_country_map.png`. Why are the source countries and damage countries not the same?

7. In `fire_scale_check_source_informed_mean.csv`, compare the 2050 annual flow share to the 2050 atmospheric stock share. Why is the stock share so much smaller?

## Conceptual Takeaways

- The SCC is marginal. It asks how much damage one extra tonne causes, not how bad the baseline climate path is.
- If an added baseline source is identical in the base and pulse runs, it changes SCC only through nonlinear state dependence.
- A true fire-carbon feedback can affect SCC because the marginal pulse causes marginal warming, which can trigger marginal additional fire CO2.
- Double counting is the central scientific hazard because RFF-SP aggregate CO2 already includes broad natural-stock and AFOLU expert judgments, but not in a transparent decomposed file.
- Gross wildfire emissions are much larger than the net persistent perturbation that belongs in a carbon-cycle SCC calculation.
- A map of where fires occur is not a map of where damages occur. The damage geography is produced by temperature response, socioeconomic exposure, sectoral damage functions and discounting.
