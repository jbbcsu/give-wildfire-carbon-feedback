# Wildfire CO2 Extension Audit Memo

Date: 2026-05-01

## Bottom Line

The Rennert et al. 2022 replication code does not contain an explicit wildfire,
fire, or biomass-burning CO2 component. Searches for `wildfire`, `fire`,
`biomass`, `land-use`, `land use`, `AFOLU`, `LULUCF`, `forestry`,
`deforestation`, `emissions`, `carbon cycle`, `CO2 concentration`, `baseline`,
`scenario`, `RFF-SPs`, `SSP`, `FAIR`, `impulse response`, and `exogenous`
found no wildfire-specific CO2 pathway in GIVE.

However, this does not mean wildfire-relevant carbon is absent from the
baseline. The default Rennert/GIVE SCC run uses RFF socioeconomic projections
for aggregate CO2 emissions after 2020. The RFF emissions elicitation includes
broad non-fossil categories such as changes in natural CO2 stocks / AFOLU-like
sources. Therefore an additive wildfire experiment should be interpreted as
**net additional wildfire CO2 above what the RFF-SP baseline already embeds**,
not gross biomass-burning CO2.

## Code And Environment

The frozen replication archive is the Zenodo release:
`RennertEtAl2022ReplicationCodeData.zip` from
https://zenodo.org/records/6932028.

The GitHub URL in the paper (`https://github.com/anthofflab/paper-2022-scc-give`)
was not cloneable from this environment, so the implementation uses the Zenodo
snapshot.

Environment facts:

- Top-level model package: `packages/MimiGIVE` (`Project.toml` lines 11-13).
- Main replication driver: `src/main.jl`.
- Full paper run: `julia --procs auto src/main.jl` (`README.md` lines 17-25).
- Tested Julia version in the archive: Julia 1.6.4 (`README.md` lines 9-15).
- Expected full runtime: about one day on the authors' reference workstation
  (`README.md` line 15).
- Outputs are written to `output` (`README.md` lines 27-29).
- Julia 1.6.4 was installed locally at
  `/Users/jbb/Dropbox/GIVE/tools/julia-1.6.4/bin/julia` and run with
  `JULIA_DEPOT_PATH=/Users/jbb/Dropbox/GIVE/.julia_depot_1_6`. The deterministic,
  sectoral, 100-draw paired Monte Carlo, scale-check and regional damage-map
  diagnostics were executed in this local environment.

Important package versions from `Manifest.toml`:

- `Mimi` 1.4.0.
- `MimiGIVE` 0.1.0-DEV, path `packages/MimiGIVE`.
- `MimiFAIRv1_6_2` 0.1.0, path `packages/MimiFAIRv1_6_2`.
- `MimiRFFSPs` 0.1.0, path `packages/MimiRFFSPs`.
- `MimiSSPs` 0.1.0, path `packages/MimiSSPs`.

The RFF-SP data are not fully embedded in the source tree. `MimiRFFSPs` registers
a DataDep named `rffsps_v5` that downloads `rffsps_v5.7z` from Zenodo record
6016583 (`packages/MimiRFFSPs/src/MimiRFFSPs.jl` lines 10-17). The file is about
1.46 GB compressed.

## Baseline SCC Entry Point

The paper baseline SC-CO2 estimate is produced by:

- `src/main.jl` lines 1-6: default `num_trials = 10_000`.
- `src/main.jl` lines 23-25: triggers the RFF-SP data dependency.
- `src/main.jl` lines 29-36: launches the RFF, DICE, and Howard-Sterner SCC
  runs.
- `src/compute_scc.jl` lines 4-27: `compute_rff_scc`, the main GIVE run.

The default GIVE SC-CO2 call uses:

- `MimiGIVE.get_model(socioeconomics_source = :RFF)`.
- `year = 2020`, `last_year = 2300`.
- `fair_parameter_set = :random`.
- `rffsp_sampling = :random`.
- `gas = :CO2`.
- `pulse_size = 1e-4` GtC.
- sectoral values enabled, domestic values disabled.
- CIAM perfect foresight and GDP caps enabled.

## Baseline Model Mechanics

GIVE builds on FAIR, then connects socioeconomic emissions into FAIR:

- `MimiGIVE.get_model` starts with `MimiFAIRv1_6_2.get_model` over 1750-2300
  (`packages/MimiGIVE/src/main_model.jl` lines 139-147).
- The socioeconomic component is inserted before FAIR's GHG cycles
  (`main_model.jl` lines 158-163).
- CO2 is routed through `:co2_emissions_identity`, then into
  `:co2_cycle.E_co2` (`main_model.jl` lines 403-406).
- Before the socioeconomic component starts, the backup stream is AR6
  `FossilCO2 + OtherCO2` (`main_model.jl` lines 396-405).

FAIR then runs:

1. Emissions to atmospheric CO2:
   `co2_cycle.E_co2` is annual CO2 emissions in GtC/yr
   (`packages/MimiFAIRv1_6_2/src/components/co2_cycle.jl` lines 20 and 80-95).
2. CO2 concentration to forcing:
   `co2_forcing` computes radiative forcing from `co2_cycle.co2`
   (`co2_forcing.jl` lines 17-24 and 67-68).
3. Total forcing to temperature:
   `total_forcing` feeds `temperature.forcing`
   (`MimiFAIRv1_6_2.jl` lines 262-312).
4. Temperature, sea level, ocean pH, GDP/population, and mortality enter damage
   components and the `DamageAggregator`.

The carbon cycle is state dependent. The 100-year integrated impulse response is
a function of cumulative emissions, airborne emissions, and temperature
(`co2_cycle.jl` line 62). A higher baseline can therefore affect both the
thermal/damage state and the carbon-cycle response.

## Marginal Ton And SCC Calculation

`MimiGIVE.compute_scc` deep-copies the model, creates a base and modified
MarginalModel, and adds a gas pulse to the modified model
(`packages/MimiGIVE/src/scc.jl` lines 120-129 and 790-808).

For CO2, `add_marginal_emissions!` inserts a `Mimi.adder` before
`:co2_cycle`, adds `pulse_size` in the requested year, and reconnects
`:co2_cycle.E_co2` to that modified stream (`scc.jl` lines 825-835).

In the Monte Carlo SCC code:

- Base and marginal damages are differenced (`scc.jl` lines 249-276).
- The result is converted from GtC pulse units to USD per tCO2 using molecular
  and pulse-size conversion factors (`scc.jl` lines 258-263).
- Discounted marginal damages are summed from the emission year through
  `last_year` using Ramsey discounting and per-capita consumption
  (`scc.jl` lines 220-235).

Raising baseline CO2 does not mechanically guarantee a higher SCC. It can raise
the SCC through nonlinear damages, state-dependent carbon uptake, sea-level
response, GDP/population interactions, or discounting. It can also have muted or
mixed effects where damages are locally linear, where discounting pushes most
incremental effects far into the future, or where higher damages reduce future
consumption and change Ramsey discount factors.

## Is Wildfire Already Included?

Findings:

- No explicit wildfire/fire/biomass-burning CO2 variable exists in `MimiGIVE`.
- The only relevant "biomass" hits are RCP biomass aerosol labels in BRICK data,
  not a GIVE CO2 emissions channel.
- FAIR's land-use forcing component uses `OtherCO2` as a proxy for land-use
  albedo forcing, not wildfire CO2 (`landuse_forcing.jl` lines 5-24).
- GIVE does not connect RFF-SP land-use subcategories to `landuse_forcing`;
  it leaves FAIR land-use forcing on the matched AR6 scenario (`main_model.jl`
  lines 416-422).
- RFF-SP CO2 enters as an aggregate `co2_emissions` variable in GtC/yr
  (`packages/MimiRFFSPs/src/components/SPs.jl` lines 76 and 127-147).

Conclusion:

The model has aggregate net CO2 pathways that may implicitly include some
wildfire-related net land-carbon effects, but there is no explicit wildfire
module, no gross fire CO2 stream, and no decomposition that would let the user
separate wildfire from other natural-stock or land-use terms.

## Extension Designs Considered

### A. Add Wildfire CO2 To Annual Emissions

Scientific interpretation:
Net additional wildfire CO2 enters the same carbon cycle as other CO2.

Where it enters:
Annual `co2_cycle.E_co2`, upstream of the existing marginal SCC pulse.

Required data:
Annual net wildfire CO2 above baseline in GtCO2/yr, converted to GtC/yr with
12/44.

Double-counting risk:
High if interpreted as gross fire emissions. Lower if interpreted as residual
net emissions not already embedded in RFF-SP aggregate CO2.

Consistency with GIVE:
High. GIVE already uses emissions -> concentration -> forcing -> temperature.

Pros:
Transparent, preserves FAIR carbon-cycle dynamics, exposes nonlinear carbon
uptake and damage interactions.

Cons:
Requires a defensible net wildfire pathway; cannot distinguish managed fires,
natural fires, deforestation fires, or regrowth without better data.

### B. Add A Baseline Concentration Adjustment

Scientific interpretation:
Wildfire is treated as an exogenous atmospheric CO2 concentration perturbation.

Where it enters:
`co2_cycle.co2` or downstream forcing.

Required data:
Annual ppm increments or a concentration trajectory.

Double-counting risk:
Moderate to high, because the carbon-cycle fate of emitted CO2 is imposed
outside FAIR.

Consistency with GIVE:
Lower. It bypasses the model's emissions-to-concentrations machinery and can
break consistency with cumulative emissions and carbon uptake.

Pros:
Useful if the best evidence is a concentration reconstruction rather than an
emissions inventory.

Cons:
Harder to audit; does not preserve mass-balance interpretation.

### C. Scale Existing Land-Use / Non-Fossil Emissions

Scientific interpretation:
Wildfire is treated as part of existing land-use or natural-stock emissions.

Where it enters:
Scale RFF-SP aggregate CO2 or AR6 `OtherCO2`.

Required data:
A decomposition of wildfire within land-use / natural-stock CO2.

Double-counting risk:
Potentially lower than pure addition if wildfire is already embedded, but only
if the decomposition is known.

Consistency with GIVE:
Moderate. It is a useful sensitivity if wildfire is partially embedded.

Pros:
Good for "what if the land-use component is under/overstated?" sensitivity.

Cons:
GIVE's default RFF-SP CO2 is aggregate; there is no native wildfire subseries to
scale.

Chosen first pass:
Approach A, with the very explicit caveat that the path is net additional
wildfire CO2 above baseline. This is the cleanest way to test the mechanism
without overriding the original replication run.

## Implemented Extension

New files:

- `wildfire_extension/WildfireGIVE.jl`.
- `wildfire_extension/run_wildfire_scc.jl`.
- `wildfire_extension/run_wildfire_experiments.sh`.
- `wildfire_extension/TECHNICAL_MEMO.md`.

No original replication files were modified.

Implementation details:

- `WildfireGIVE.wildfire_co2_path` builds low/medium/high/stress/custom paths
  in GtCO2/yr and GtC/yr (`WildfireGIVE.jl` lines 20-70).
- `WildfireGIVE.apply_wildfire_co2!` inserts `:wildfire_co2_emissions` before
  `:co2_emissions_identity` (`WildfireGIVE.jl` lines 101-153).
- This placement means the standard GIVE marginal pulse is added after the
  wildfire-adjusted baseline, so base and marginal runs share the same wildfire
  scenario and the pulse remains the marginal ton (`WildfireGIVE.jl` lines
  105-112).
- The original pre-2020 AR6 backup behavior is preserved
  (`WildfireGIVE.jl` lines 137-145).

Scenario assumptions:

- Low: 0.10 GtCO2/yr from 2020 onward.
- Medium: 0.25 GtCO2/yr in 2020, growing 0.5%/yr.
- High: 0.50 GtCO2/yr in 2020, growing 1.0%/yr, capped at 5.0 GtCO2/yr.
- Optional stress: 2.00 GtCO2/yr in 2020, growing 1.5%/yr, capped at
  20.0 GtCO2/yr.

These are deliberately stylized net-residual scenarios. They are not gross fire
emissions.

## Reproducible Run Script

Smoke test:

```bash
cd /Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo
./wildfire_extension/run_wildfire_experiments.sh 100 false
```

Full-size run:

```bash
cd /Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo
./wildfire_extension/run_wildfire_experiments.sh 10000 false
```

Include the stress scenario:

```bash
./wildfire_extension/run_wildfire_experiments.sh 1000 true output/wildfire_extension_stress
```

Expected outputs under `output/wildfire_extension`:

- `scc_summary.csv`: mean, median, 5th, 95th percentile SCC and baseline
  differences.
- `scc_samples.csv`: SCC draws for distribution plots.
- `wildfire_emissions_paths.csv`: added wildfire path in GtCO2/yr and GtC/yr.
- `deterministic_climate_damage_paths.csv`: baseline vs modified CO2,
  forcing, temperature, and damage paths for deterministic diagnostics.
- `discounted_marginal_damages.csv`: discounted marginal damage paths.
- `discounted_marginal_damage_differences.csv`: scenario minus baseline
  discounted marginal damages.
- `plots/*.html`: simple VegaLite plots when plotting succeeds.

## Follow-up: Double Counting And Climate-Responsive Fire

The RFF-SP archive confirms that `rffsp_co2_emissions.csv` is an aggregate
annual global CO2 pathway with columns `sample`, `year`, and `value`, in GtC.
There is no fossil/industrial/AFOLU/wildfire decomposition in the downloaded
pathway. The RFF-SP documentation says the emissions files contain projected
annual global gas emissions only, and `packages/MimiRFFSPs/src/components/SPs.jl`
loads that single aggregate file into `:co2_emissions`.

The RFF-SP emissions elicitation was deliberately broad. The appendix defines
global CO2 emissions in terms of fossil and industrial CO2, AFOLU / natural
stock changes, DAC, and BECCS, and instructs experts to avoid double-counting
between categories. Therefore the most careful reading is:

- explicit wildfire or biomass-burning forecasts are not represented in GIVE or
  MimiRFFSPs;
- wildfire-related net land-carbon effects may already be implicit in expert
  judgments about AFOLU / natural CO2 stocks;
- an additive wildfire experiment should only add a residual: net additional
  climate-driven fire CO2 not already embedded in RFF-SP aggregate CO2.

Relevant projection papers/data identified for the next step:

- Park et al. 2023, Global Environmental Change, "Impact of climate and
  socioeconomic changes on fire carbon emissions in the future." This is the
  best conceptual match: global 21st-century fire carbon emissions, driver
  decomposition, meteorology/biomass/land-use/population/GDP, and boreal
  increases even when global totals can fall under socioeconomic development.
- Tian et al. 2023, Environmental Pollution, projects fire emissions under
  1.5 C and 2 C warming, with global fire emissions rising roughly 10-15% at
  1.5 C and 15-23% at 2 C. This supports a simple temperature-response
  heuristic, though the paper focuses on air quality species rather than a net
  CO2 stock perturbation.
- Val Martin, Pierce, and Heald 2018 USDA Forest Service data release,
  "Global fire emissions, fire area burned and air quality data projected using
  a global earth system model (RCP45/SSP1 and RCP8.5/SSP3)." This has public
  gridded CESM fire-emissions files. The emissions/auxiliary archive is about
  603 MB and is the first practical candidate for making the extension data
  driven.
- Byrne et al. 2024, Nature, "Carbon emissions from the 2023 Canadian
  wildfires," is not a global forecast, but it is highly relevant for boreal
  plausibility: it estimates 647 TgC from 2023 Canadian fires and reports that
  2023-like temperatures become typical in the 2050s under SSP2-4.5.
- Phillips et al. 2022, Science Advances, estimates projected gross and net
  CO2 from North American boreal wildfires through mid-century. It is valuable
  for net-vs-gross treatment and fire-management counterfactuals.

## Quick Climate-Response Heuristic

The new quick script is:

```bash
cd /Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo
./wildfire_extension/run_wildfire_quick.sh output/wildfire_quick
```

It does not run the 10,000-trial Monte Carlo. It uses one deterministic GIVE
configuration, the default RFF-SP sample in MimiRFFSPs, and
`MimiGIVE.compute_scc(..., n=0)`.

The heuristic path is generated from the baseline deterministic temperature
trajectory:

```text
added_net_gtco2 =
    gross_reference_fire_gtco2
    * sensitivity_per_c
    * max(T_baseline(t) - T_baseline(2020), 0)
    * net_persistence_fraction
    * not_embedded_fraction
```

Defaults:

- gross reference global fire carbon: 2.2 PgC/yr, equal to 8.07 GtCO2/yr.
- low: 7% gross fire response per C, 5% net persistence, 25% not embedded.
- medium: 10% per C, 10% net persistence, 50% not embedded.
- high: 15% per C, 20% net persistence, 75% not embedded.

Those parameters are intentionally conservative and transparent. They are not a
claim about the true global wildfire feedback. They encode the double-counting
defense directly: only a fraction of the gross climate-driven increment is
treated as long-lived and missing from the RFF-SP baseline.

Smoke-test output written to `output/wildfire_quick_smoke`:

- `deterministic_scc_summary.csv`
- `wildfire_emissions_paths.csv`
- `deterministic_climate_damage_paths.csv`

For the one deterministic 2.0% discount-rate configuration, the baseline SCC was
about $139.10/tCO2 in 2020 dollars. The low, medium, and high heuristic changes
were tiny: about -$0.006/tCO2, -$0.111/tCO2, and +$0.065/tCO2 respectively.
Because these changes are much smaller than the finite-pulse and deterministic
noise floor, they should be read only as a mechanism smoke test. The climate
paths did move in the expected direction: maximum CO2 rose from 857.8 ppm in the
baseline to 858.2, 859.9, and 867.1 ppm in low, medium, and high; maximum
temperature rose from 4.692 C to 4.694, 4.700, and 4.728 C.

## Source-Informed 100-Draw Uncertainty Run

The follow-up source-informed run downloaded the USDA Forest Service archive for
Val Martin, Pierce, and Heald 2018:

```text
/Users/jbb/Dropbox/GIVE/fire_data/usda_val_martin_2018/RDS-2018-0021_emissions_auxdata.zip
```

The archive contains projected fire-emissions netCDFs for many air-quality
species, but not CO2 directly. I extracted CO fire emissions and burned-area
changes as source-based scaling information in:

```text
wildfire_extension/source_data/usda_val_martin_fire_projection_summary.csv
```

Key extracted ratios relative to the 2001-2010 baseline:

- RCP4.5 CO fire emissions: 1.19 by 2041-2050, 1.33 by 2091-2100.
- RCP8.5 CO fire emissions: 1.55 by 2041-2050, 2.01 by 2091-2100.
- RCP4.5 burned area: 1.09 by 2041-2050, 1.15 by 2091-2100.
- RCP8.5 burned area: 1.11 by 2041-2050, 1.47 by 2091-2100.

The 100-draw experiment combines these with the Byrne et al. Canada-2023 excess
fire-carbon anchor:

```text
647 TgC - 121 TgC = 526 TgC = 0.526 GtC = 1.929 GtCO2/yr
```

For each draw, the model samples:

- gross 2050 target fraction of the Canada-2023 excess: triangular
  0.25 / 1.00 / 2.00.
- net persistence fraction: triangular 0.25 / 0.60 / 1.00.
- not-already-embedded fraction: triangular 0.50 / 0.80 / 1.00.
- 2100-to-2050 growth ratio: triangular 1.06 / 1.20 / 1.32, based on the USDA
  late/mid-century CO and burned-area ratios.

The added emissions are temperature-scaled using the deterministic GIVE baseline
temperature path. Draw summaries:

| Year | Mean added GtCO2/yr | Median | 5th | 95th |
| --- | ---: | ---: | ---: | ---: |
| 2030 | 0.358 | 0.368 | 0.131 | 0.635 |
| 2050 | 1.034 | 1.064 | 0.378 | 1.832 |
| 2100 | 1.232 | 1.266 | 0.446 | 2.242 |
| 2200 | 1.483 | 1.482 | 0.532 | 2.698 |
| 2300 | 1.653 | 1.607 | 0.595 | 3.043 |

For the 100-draw run, paired FAIR and RFF-SP sample IDs were used across the
baseline and wildfire cases. The 2.0% discount-rate SCC summary was:

| Scenario | Mean SCC | Median SCC | 5th | 95th |
| --- | ---: | ---: | ---: | ---: |
| Baseline | 218.98 | 185.64 | 49.30 | 568.96 |
| Wildfire uncertainty | 219.48 | 185.85 | 53.63 | 565.91 |

The wildfire case increased the mean SCC by $0.50/tCO2, about 0.23%, and the
median by $0.21/tCO2. The paired 2.0% SCC delta had mean +$0.50/tCO2, median
-$0.09/tCO2, 5th percentile -$3.27/tCO2, and 95th percentile +$5.67/tCO2.

Main outputs:

- `output/wildfire_source_uncertainty_100/scc_summary.csv`
- `output/wildfire_source_uncertainty_100/scc_samples.csv`
- `output/wildfire_source_uncertainty_100/wildfire_parameter_draws.csv`
- `output/wildfire_source_uncertainty_100/wildfire_emissions_draws.csv`
- `output/wildfire_source_uncertainty_100/wildfire_emissions_summary.csv`
- `output/wildfire_source_uncertainty_100/scc_distribution_2pct.svg`

## Validation Checklist

Before interpreting wildfire results:

1. Run the original replication with a small `n` and verify that the code
   executes.
2. Run the extension with `n=10` or `n=100` only as a smoke test.
3. Run the original 10,000-trial baseline and confirm the central SC-CO2
   estimate approximately reproduces Rennert et al.'s published result.
4. Confirm `wildfire_emissions_paths.csv` uses GtCO2/yr and that
   `wildfire_gtc = wildfire_gtco2 * 12/44`.
5. Confirm the marginal pulse remains `1e-4` GtC and is not changed by the
   wildfire scenario.
6. Compare deterministic CO2 and temperature paths to ensure the wildfire
   scenarios move in the expected direction.
7. Inspect `discounted_marginal_damage_differences.csv` to see whether changes
   come from near-term or far-future damages.
8. Treat any high-scenario result as a sensitivity, not an empirical estimate.

## Assumptions And Caveats

- Wildfire CO2 may already be partly included in historical inventories,
  land-use emissions, and RFF-SP natural-stock emissions.
- Gross fire CO2 is not the right perturbation for SCC unless it is net of
  regrowth and other carbon-cycle recovery.
- Some fire CO2 is part of the short-run biogenic carbon cycle and may be
  reabsorbed.
- Climate-driven wildfire increases are partly endogenous to warming. Adding
  them exogenously can double-count feedbacks if the baseline or damage modules
  already capture parts of that process.
- The SCC is the marginal damage of one additional ton, not total damage from
  all wildfire emissions.
- A higher baseline stock raises SCC only through model nonlinearities,
  state-dependent carbon uptake, damage curvature, sea-level dynamics, GDP and
  consumption interactions, and discounting.

## Where This Could Be Wrong

- The RFF-SP aggregate CO2 pathway may already include expert assumptions about
  future wildfire-related net emissions. If so, the correct experiment is not
  additive; it is a decomposition or rescaling of the relevant RFF-SP category.
- The stylized scenarios may be too high or too low for net wildfire CO2.
- The extension does not add fire aerosols, methane, ozone precursors, black
  carbon, albedo change, health impacts from smoke, or ecosystem damages.
- The extension starts in 2020. It does not alter historical pre-2020 CO2 stock.
- The deterministic diagnostics use a single RFF-SP sample and are not a
  substitute for Monte Carlo path diagnostics.
- Julia 1.6.4 x86_64 was installed under `/Users/jbb/Dropbox/GIVE/tools` and
  run through Rosetta. The project instantiated, MimiGIVE loaded, and the
  RFF-SP DataDep downloaded and unpacked.
- The full Monte Carlo path still needs validation after we settle the
  double-counting and data-source assumptions.
