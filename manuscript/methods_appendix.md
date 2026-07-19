# Supplementary Information: Methods For The Wildfire-Carbon Feedback Extension

This Supplement describes the full research-programming workflow used to audit the
Rennert et al. GIVE replication code, construct wildfire-carbon scenarios, add those
scenarios to the carbon cycle, run social cost of carbon dioxide (SC-CO2)
experiments, and generate the figures and tables used in the manuscript. It is
written as a replication guide. The main text states the scientific design and
results; this document records the implementation details needed to reproduce or
audit the work.

The central methodological distinction is important. GIVE uses exogenous
socioeconomic and emissions pathways. The extension implemented here does not claim
that all wildfire CO2 is absent from the baseline pathway. Instead, it tests an
accounting-residual fire-carbon feedback: additional net-persistent wildfire CO2
that is caused by warming and is not already embedded in the aggregate baseline CO2
scenario. Gross wildfire cases are retained as mechanism and stress tests because
they show how large the effect could be if gross fire carbon were treated as an
additional persistent source. They are not interpreted as double-counting-safe
central estimates.

Repository paths in this Supplement use the following convention. Paths beginning
with `wildfire_extension/` refer to files in the public extension repository,
[jbbcsu/give-wildfire-carbon-feedback](https://github.com/jbbcsu/give-wildfire-carbon-feedback).

Paths beginning with `packages/`, `Project.toml` or `Manifest.toml` refer to the
original Rennert et al. GIVE replication archive, which is available from Zenodo
and GitHub. For full reproduction, download the original GIVE archive and place the
extension repository inside it as `wildfire_extension/`. Commands in this
Supplement use placeholder variables (`GIVE_ROOT`, `EXT_ROOT` and `USDA_RAW`) so
that no step depends on a particular user's computer directory.

## A. Roadmap Of The Replication Design

This Supplement is organized around the practical questions a reader would ask when
trying to reproduce the extension: what the baseline model contains, what new data
were added, how those data were cleaned, how the wildfire-carbon pathway was
constructed, where the pathway enters GIVE, how the experiments were run, and which
outputs support the manuscript figures.

The workflow has five parts.

First, the released GIVE replication code was audited to determine how baseline CO2
enters the model. That audit found that the RFF socioeconomic projections used in
the preferred GIVE run provide a single aggregate CO2 emissions pathway, in GtC per
year, without separate fossil, industrial, AFOLU, wildfire or natural-carbon stock
variables. GIVE connects that aggregate pathway directly into FaIR's carbon-cycle
module. Because the input is aggregated, the code can show that GIVE lacks an
endogenous warming-to-wildfire-to-CO2 feedback, but it cannot identify how much
wildfire-related carbon may already have been anticipated by the RFF expert
elicitation or embedded in AFOLU-related assumptions.

Second, external wildfire and fire-activity evidence was assembled. The project uses
two kinds of evidence. Literature values are used to set broad ranges for global
fire carbon, net persistence and accounting uncertainty. A USDA/Val Martin/Pierce/
Heald gridded data archive is processed to obtain growth ratios for future fire
activity under RCP4.5 and RCP8.5-style forcing pathways. These ratios are used as
diagnostic support for fire-growth scaling, not as a direct measurement of global
CO2 emissions.

Third, wildfire CO2 was parameterized in two ways. The main model extension is an
endogenous feedback:

`temperature increase -> additional wildfire CO2 -> carbon cycle -> forcing -> temperature -> damages`.

The additional annual CO2 flow is a function of lagged global mean temperature,
gross fire-carbon sensitivity, the net-persistent share of fire carbon, and the
share not already embedded in baseline emissions. A separate source-informed
exogenous pathway was also constructed for diagnostics and maps.

Fourth, the extension was wired into GIVE upstream of the CO2 carbon cycle, so the
added wildfire CO2 affects atmospheric concentration, radiative forcing,
temperature and damages through the same climate-economy machinery used by the
baseline model. For the endogenous version, the marginal CO2 pulse can also affect
future wildfire CO2 through the temperature feedback.

Fifth, deterministic and Monte Carlo experiments were run. The manuscript currently
uses 100 paired draws, not the full 10,000-draw production run. The scripts are
written so that the number of draws can be increased when the computational budget
is available.

## B. Baseline GIVE Accounting Audit

### B.1 RFF-SP CO2 Input

The preferred Rennert et al. GIVE run uses RFF socioeconomic projections
(`RFF-SPs`). In the MimiGIVE package, the socioeconomic projection component defines
and loads a single aggregate CO2 emissions variable. The relevant source file is:

`packages/MimiGIVE/src/SPs.jl`

The key points are:

- `SPs.jl` defines `co2_emissions` with unit `GtC/yr`.
- The RFF-SP pathway is loaded from `rffsp_co2_emissions.csv`.
- No separate RFF-SP variables are loaded for fossil CO2, industrial-process CO2,
  land-use CO2, wildfire CO2, managed forest carbon, biomass burning, AFOLU, LULUCF
  or natural stock change.

The practical implication is that the GIVE code sees one annual global CO2 pathway.
Any decomposition between fossil, industrial, land-use and fire-related sources is
not available inside the model.

### B.2 Connection To The Carbon Cycle

The model assembly file is:

`packages/MimiGIVE/src/main_model.jl`

In the baseline model, aggregate `:Socioeconomic => :co2_emissions` is connected to
a CO2-emissions identity component and then into FaIR's carbon-cycle representation.
The extension uses this same connection point, because it is the direct pathway by
which annual CO2 emissions enter concentrations. This means the added wildfire CO2
is treated physically like an additional annual CO2 emission entering the carbon
cycle, not like a post-hoc damage adjustment.

For non-RFF or fallback years, GIVE uses AR6 emissions data. The fallback total is
constructed from `FossilCO2 + OtherCO2` in the AR6 emissions files:

`packages/MimiGIVE/data/FAIR_ar6/AR6_emissions_<scenario>_1750_2300.csv`

For RFF-SP runs, GIVE also leaves FaIR's land-use forcing settings tied to a matched
SSP2-4.5 configuration because RFF-SP land-use CO2 is not available as a separate
time series. This is one reason the double-counting problem cannot be resolved only
by reading the model code. The code tells us that no separate wildfire feedback is
generated endogenously, but it does not tell us whether some expected fire-related
land carbon is implicit in the aggregate RFF-SP emissions pathway.

### B.3 What The Audit Supports

The audit supports the following public claims:

- GIVE does not internally generate a warming-driven wildfire CO2 feedback.
- GIVE does not expose a wildfire or biomass-burning CO2 variable that can be
  decomposed from aggregate RFF-SP CO2.
- The RFF-SP aggregate pathway may already include some fire-related or AFOLU-
  related expectations, but the released GIVE implementation cannot identify them.
- A double-counting-safe experiment should therefore add only the residual,
  net-persistent, not-already-embedded portion of climate-driven wildfire CO2.

The audit does not support the stronger claim that all wildfire CO2 is absent from
the baseline scenario.

## C. Data Inputs

This section lists every data source used by the wildfire extension and clarifies
which inputs affect model runs versus figures or interpretation.

### C.1 GIVE Replication Code And Data

Primary source:

- Rennert et al. replication archive: `https://zenodo.org/records/6932028`
- GitHub replication repository: `https://github.com/anthofflab/paper-2022-scc-give`
- MimiGIVE repository: `https://github.com/anthofflab/MimiGIVE.jl`

Extension repository:

- [GIVE wildfire-carbon feedback extension](https://github.com/jbbcsu/give-wildfire-carbon-feedback)

Role of the original GIVE archive:

- provides the original GIVE model code;
- provides RFF-SP socioeconomic and emissions draws;
- provides FaIR climate parameter draws and AR6 fallback emissions;
- provides sectoral damage modules, discounting code, pulse machinery and output
  conventions.

Role of the extension repository:

- provides the wildfire-carbon model extension;
- provides cleaned fire-projection summaries and uncertainty-framework files;
- provides run scripts, figure builders, manuscript files, SI files, slide deck,
  teaching notes and interactive-site materials.

Cleaning:

- no cleaning was applied to the original GIVE input data;
- the wildfire extension reads these inputs through MimiGIVE's existing APIs.

### C.2 USDA / Val Martin / Pierce / Heald Fire Projection Archive

Primary source:

- Val Martin et al. and associated USDA Forest Service Research Data Archive,
  `RDS-2018-0021`, DOI `https://doi.org/10.2737/RDS-2018-0021`.

Raw data archive:

- download `RDS-2018-0021_emissions_auxdata.zip` from the DOI landing page;
- extract it into a user-chosen directory, represented below as `USDA_RAW`.

Files used:

- `Data/Emissions/CESM_RCP45_CO_surface_2000-2050-2100_0.9x1.25.nc`
- `Data/Emissions/CESM_RCP85_CO_surface_2000-2050-2100_0.9x1.25.nc`
- `Data/AuxiliaryData/CESM_RCP45_AreaBurned_2000-2050-2100_0.9x1.25.nc`
- `Data/AuxiliaryData/CESM_RCP85_AreaBurned_2000-2050-2100_0.9x1.25.nc`
- `Data/AuxiliaryData/cesm130_clm5_firemodule_area_f09x125.nc`

Cleaned output:

- `wildfire_extension/source_data/usda_val_martin_fire_projection_summary.csv`
- GitHub: [usda_val_martin_fire_projection_summary.csv](https://github.com/jbbcsu/give-wildfire-carbon-feedback/blob/main/source_data/usda_val_martin_fire_projection_summary.csv)

Role in this project:

- provides future fire-activity growth ratios from gridded projected CO emissions
  and burned area;
- used to check whether the heuristic wildfire pathways are within a plausible
  climate-driven fire-growth range;
- used in diagnostics and sensitivity framing, not as a direct CO2 emissions input.

Important limitation:

The USDA archive files used here report CO emissions and burned area, not CO2
emissions. The project therefore uses the archive to estimate relative changes in
fire activity over time, not to convert CO into an absolute CO2 source. Absolute
CO2 scale is instead handled by the separate fire-carbon assumptions described
below.

### C.3 Canada 2023 Wildfire Carbon Scale

The Canada 2023 fire year is used as a scale check and as an anchor for one
source-informed diagnostic pathway. The values used are:

- gross Canada 2023 wildfire carbon: `647 TgC`;
- approximate prior 20-year average: `121 TgC`;
- Canada excess above that average: `647 - 121 = 526 TgC`;
- Canada share of global wildfire carbon in 2023: `26.7%`.

Conversions:

- `526 TgC = 0.526 GtC`;
- `0.526 GtC * 44/12 = 1.929 GtCO2`;
- implied gross global fire carbon in 2023, using the 26.7% share, is
  `647 / 0.267 = 2,423 TgC = 2.423 GtC = 8.884 GtCO2`.

Role in this project:

- provides a transparent high-fire-year scale check;
- helps communicate the difference between annual flow and atmospheric stock;
- anchors a diagnostic source-informed pathway in
  `WildfireGIVE.source_informed_wildfire_draws`.

It is not treated as the central estimate of persistent additional global fire CO2.
Most gross fire carbon is not automatically a long-lived atmospheric addition
because regrowth, ecosystem recovery and existing inventory accounting can offset or
already include part of the gross flow.

### C.4 Global Fire Carbon Reference

The main feedback code uses a gross reference fire-carbon flow of `2.2 PgC/yr`
(`2.2 GtC/yr`). This is a broad global biomass-burning scale used to translate a
per-degree fire-carbon response into an annual gross fire-carbon flow. The reference
flow is not itself added to GIVE. Only the temperature-induced increment multiplied
by net persistence and not-embedded fractions is added.

The distinction matters:

- reference gross fire carbon is a scale parameter;
- incremental climate-driven fire carbon is the response to warming;
- net-persistent residual fire carbon is the part added to GIVE.

### C.5 Natural Earth Geographic Data

Natural Earth country geometry is used only for maps. The repository file is:

- `wildfire_extension/data/natural_earth/ne_110m_admin_0_countries.geojson`
- GitHub: [ne_110m_admin_0_countries.geojson](https://github.com/jbbcsu/give-wildfire-carbon-feedback/blob/main/data/natural_earth/ne_110m_admin_0_countries.geojson)

Role in this project:

- provides country polygons for figures;
- does not enter the GIVE model or SCC calculation.

### C.6 Qiu et al. Smoke Mortality Paper

Qiu et al. was reviewed as contextual literature on wildfire smoke-related
mortality valuation. It is not used as a direct input to the CO2 feedback model
because the present extension is about wildfire carbon entering the global CO2
cycle. Smoke exposure, aerosols, ozone precursors and particulate-matter mortality
are distinct channels and are not included in the central CO2-only extension.

## D. Downloading And Organizing Data

### D.1 GIVE Code And Julia Environment

The replication uses the Julia environment supplied by the Rennert et al. archive,
including `Project.toml` and `Manifest.toml`. The extension was tested with Julia
1.6.4, matching the era of the released replication environment. A reader may use a
system Julia executable or any Julia installation compatible with the archived
manifest.

For public replication, use a directory structure like this:

```text
GIVE_ROOT/
  Project.toml
  Manifest.toml
  packages/
  wildfire_extension/
```

Here `GIVE_ROOT` is the root of the Rennert et al. replication archive and
`EXT_ROOT=$GIVE_ROOT/wildfire_extension` is a clone of the public extension
repository. One way to create that structure is:

```bash
git clone https://github.com/anthofflab/paper-2022-scc-give.git GIVE_ROOT
cd GIVE_ROOT
git clone https://github.com/jbbcsu/give-wildfire-carbon-feedback.git wildfire_extension
julia --project=. -e 'using Pkg; Pkg.instantiate()'
```

For exact reproduction of the archived package versions, the Zenodo replication
archive should be preferred if it differs from the live GitHub repository. The
extension does not overwrite the original replication scripts; all new scripts,
outputs and manuscript files live under `wildfire_extension/`.

### D.2 USDA Fire Projection Archive

The USDA archive was downloaded from the `RDS-2018-0021` landing page. The raw
archive file is `RDS-2018-0021_emissions_auxdata.zip`. After extraction, the
directory containing `Data/Emissions/` and `Data/AuxiliaryData/` is represented in
the commands below as `USDA_RAW`.

The cleaned summary used by the extension is tracked in the repository:

`wildfire_extension/source_data/usda_val_martin_fire_projection_summary.csv`

For a fresh replication, the user should download the archive from the DOI landing
page, preserve the archive's internal directory structure, and run:

```bash
GIVE_ROOT=/path/to/rennert-give-replication
EXT_ROOT="$GIVE_ROOT/wildfire_extension"
USDA_RAW=/path/to/extracted/RDS-2018-0021

julia --project="$GIVE_ROOT" \
  "$EXT_ROOT/process_usda_val_martin.jl" \
  "$USDA_RAW" \
  "$EXT_ROOT/source_data/usda_val_martin_fire_projection_summary.csv"
```

If the raw archive is not available, the cleaned summary CSV is sufficient to
reproduce the figures and parameter checks that depend on these ratios.

### D.3 Geographic Data

The Natural Earth GeoJSON file was placed in:

`wildfire_extension/data/natural_earth/ne_110m_admin_0_countries.geojson`

It is used by the R figure script. It is not used by Julia model runs.

## E. Cleaning And Aggregating The USDA Fire Projection Data

The processing script is `wildfire_extension/process_usda_val_martin.jl`
([GitHub](https://github.com/jbbcsu/give-wildfire-carbon-feedback/blob/main/process_usda_val_martin.jl)).

This script converts the raw NetCDF files into a compact CSV of annual fire-activity
statistics by scenario and time window. It performs two aggregations: one for
surface CO emissions and one for burned area.

### E.1 CO Emissions Aggregation

The CO NetCDF files provide gridded monthly biomass-burning CO fluxes. The script
reads variable `bb` from each CO file and grid-cell area from
`cesm130_clm5_firemodule_area_f09x125.nc`. Grid-cell area is converted from square
kilometres to square centimetres because the emissions flux is expressed per square
centimetre.

The conversion implemented in the script is:

```text
area_cm2 = area_km2 * 1e10
molecules_per_second = sum(bb[:, :, month] * area_cm2)
molecules_in_month = molecules_per_second * seconds_in_month
grams_CO = molecules_in_month / Avogadro * molecular_weight_CO
Tg_CO = grams_CO / 1e12
```

Constants:

- Avogadro constant: `6.02214076e23 molecules/mol`;
- CO molecular weight: `28.0101 g/mol`;
- month lengths: no-leap calendar with 365 days per year.

The monthly Tg CO values are summed to annual Tg CO. Annual values are then averaged
over three windows:

- baseline: 2001-2010;
- mid-century: 2041-2050;
- late-century: 2091-2100.

The output reports both the annual mean and the ratio of each future window to the
baseline window.

### E.2 Burned-Area Aggregation

The burned-area NetCDF files provide variable `areaburned`. The script sums finite
grid-cell values by year and averages those annual totals over the same three
windows. Missing or non-finite grid-cell values are excluded from the burned-area
sum. The cleaned output reports annual burned area in square kilometres and the
future-to-baseline ratio.

### E.3 Cleaned USDA Summary

The cleaned CSV contains 12 records: two RCP scenarios, two variables and three time
windows. The values used most often in the analysis are the CO-emissions ratios:

| Scenario | Variable | Baseline mean | Mid-century mean | Late-century mean | Mid ratio | Late ratio |
|---|---:|---:|---:|---:|---:|---:|
| RCP4.5 | CO, TgCO/yr | 372.49 | 443.38 | 495.91 | 1.190 | 1.331 |
| RCP8.5 | CO, TgCO/yr | 372.49 | 576.36 | 749.24 | 1.547 | 2.011 |
| RCP4.5 | burned area, km2/yr | 3,850,928 | 4,184,600 | 4,428,308 | 1.087 | 1.150 |
| RCP8.5 | burned area, km2/yr | 3,975,942 | 4,427,842 | 5,833,900 | 1.114 | 1.467 |

The CO ratios are larger than the burned-area ratios because emissions intensity,
fuel loading, combustion conditions and regional shifts can change even when total
burned area changes less. The extension does not use either ratio mechanically as
an absolute CO2 emission. They are used as evidence that climate-driven fire
activity can plausibly grow by tens of percent to roughly a doubling over the
century in high-forcing conditions.

## F. Constructing Wildfire CO2 Pathways

Two pathway families are implemented.

### F.1 Endogenous Temperature-Feedback Pathway

The central extension is implemented in `wildfire_extension/WildfireGIVE.jl`
([GitHub](https://github.com/jbbcsu/give-wildfire-carbon-feedback/blob/main/WildfireGIVE.jl)).

The component is named:

`wildfire_temperature_feedback_co2`

For model year `t`, the added wildfire carbon is:

```text
E_fire,t =
  E_ref * beta * max(T_t-1 - T_ref, 0)
        * phi_net
        * phi_missing
```

where:

- `E_fire,t` is additional wildfire CO2 emissions in `GtC/yr`;
- `E_ref` is gross reference global fire carbon, set to `2.2 GtC/yr`;
- `beta` is the fractional gross fire-carbon response per 1 C of warming;
- `T_t-1` is lagged global mean temperature from the GIVE temperature module;
- `T_ref` is the model temperature in the reference year;
- `phi_net` is the fraction of gross additional fire carbon that remains as a
  net-persistent atmospheric addition after regrowth and ecosystem recovery;
- `phi_missing` is the fraction not already embedded in the aggregate baseline CO2
  pathway;
- `max(..., 0)` prevents cooling relative to the reference year from generating
  negative fire emissions.

The code uses lagged temperature (`t-1`) rather than contemporaneous temperature to
avoid an algebraic loop between emissions and temperature inside a single Mimi
timestep. The default start year is 2020. The default reference temperature year is
also 2020 in the current specification, so the feedback adds no historical
emissions and only responds to warming after the SCC pulse year.

The component has a safeguard parameter `max_feedback_gtc`. In current runs the cap
is set high enough that it does not bind in normal scenarios. It prevents
pathological parameter draws or debugging experiments from producing numerically
unbounded annual fire emissions.

### F.2 Interpretation Of The Feedback Parameters

The three multiplicative parameters separate physical response from accounting.

`beta` is the gross fire-carbon sensitivity to warming. It answers: if the world
warms by 1 C relative to the reference year, what fraction of current gross global
fire carbon appears as additional gross fire carbon?

`phi_net` is the net-persistence fraction. It answers: what fraction of additional
gross fire carbon remains as a net CO2 addition after vegetation regrowth,
ecosystem recovery, changes in future fuel availability and other carbon-cycle
offsets? This is a physical and ecological parameter.

`phi_missing` is the not-embedded fraction. It answers: what fraction of the net
additional fire carbon is absent from the baseline aggregate emissions pathway?
This is an accounting parameter, not a physical parameter. It exists because RFF-SP
CO2 is aggregated and cannot identify whether fire-related expectations are already
included.

This decomposition is the main double-counting control. Gross wildfire emissions
are not added directly in the central runs. The model adds:

```text
gross additional fire carbon
* net-persistent fraction
* not-already-embedded fraction
```

### F.3 Monte Carlo Parameter Distributions

The current 100-draw Monte Carlo uses triangular distributions. These are
exploratory uncertainty distributions, not a formal posterior. They are designed to
separate baseline GIVE uncertainty from wildfire-accounting uncertainty while
keeping the central assumptions transparent.

The Monte Carlo script is `wildfire_extension/run_temperature_feedback_mcs.jl`
([GitHub](https://github.com/jbbcsu/give-wildfire-carbon-feedback/blob/main/run_temperature_feedback_mcs.jl)).

Scenario parameters:

| Scenario | beta | phi_net | phi_missing | Interpretation |
|---|---:|---:|---:|---|
| residual medium | triangular(0.07, 0.10, 0.15) | triangular(0.05, 0.10, 0.20) | triangular(0.25, 0.50, 0.75) | conservative residual feedback |
| residual high | triangular(0.25, 0.50, 0.75) | triangular(0.15, 0.30, 0.50) | triangular(0.50, 0.75, 1.00) | high residual feedback |
| half-gross stress | calibrated sensitivity * triangular(0.50, 1.00, 1.50) * 0.5 | 1.00 | 1.00 | stress test, not double-counting-safe |
| gross stress | calibrated sensitivity * triangular(0.50, 1.00, 1.50) | 1.00 | 1.00 | stress test, not double-counting-safe |

The residual cases are the defensible central accounting experiments because they
allow for regrowth and possible embedding in the baseline. The gross stress cases
are included to show mechanism sensitivity and to help interpret why the residual
effects are smaller than the total scale of fire carbon might suggest.

### F.4 RESFire-Style Stress Calibration

The gross stress cases use a calibration routine in
`wildfire_extension/run_temperature_feedback_scc.jl`
([GitHub](https://github.com/jbbcsu/give-wildfire-carbon-feedback/blob/main/run_temperature_feedback_scc.jl)).

The routine calibrates a temperature sensitivity so that cumulative gross additional
fire CO2 between 2021 and 2050 equals a target cumulative quantity under the
baseline deterministic temperature path. In the current script, the default
calibration target is `111.889 GtCO2` over 2021-2050.

The calibration is:

```text
sensitivity =
  target_cumulative_gtco2 /
  sum_{2021:2050} [E_ref_gtco2 * max(T_t-1 - T_2020, 0)]
```

The resulting sensitivity is then used with `phi_net = 1` and `phi_missing = 1` for
gross stress cases. These runs should not be read as central estimates. They answer
a different question: how responsive is the SCC if a large gross wildfire-carbon
feedback is treated as fully persistent and fully missing from baseline emissions?

### F.5 Source-Informed Exogenous Diagnostic Pathway

A separate source-informed diagnostic pathway is implemented by:

`WildfireGIVE.source_informed_wildfire_draws`

This pathway does not use the endogenous feedback component. Instead, it constructs
a transparent exogenous path anchored to the Canada 2023 excess fire-carbon scale.
The steps are:

1. Start from Canada 2023 excess fire carbon:
   `526 TgC = 0.526 GtC = 1.929 GtCO2`.
2. Draw a 2050 gross target fraction from
   `triangular(0.25, 1.00, 2.00)`.
3. Draw a net-persistence fraction from
   `triangular(0.25, 0.60, 1.00)`.
4. Draw a not-embedded fraction from
   `triangular(0.50, 0.80, 1.00)`.
5. Draw a 2100-to-2050 growth ratio from
   `triangular(1.06, 1.20, 1.32)`.
6. Convert the net target to a full annual path using the deterministic GIVE
   temperature trajectory as a scaling curve.

The source-informed mean path is used for sectoral diagnostics, temperature plots
and regional damage maps. It is not the central endogenous-feedback Monte Carlo.

## G. Adding Wildfire CO2 To GIVE

### G.1 Exogenous Adder

The function:

`WildfireGIVE.apply_wildfire_co2!`

adds an annual exogenous wildfire CO2 stream to the model. It inserts a Mimi
`adder` component before the existing CO2 emissions identity. The adder receives:

- baseline `:Socioeconomic => :co2_emissions`;
- wildfire `:wildfire_co2_emissions_add`;
- AR6 fallback emissions for years where RFF-SP emissions are not available.

The output of the adder becomes the input to the existing CO2-emissions identity.
The carbon cycle therefore sees:

```text
baseline aggregate CO2 + added wildfire CO2
```

in `GtC/yr`.

This function is used for exogenous diagnostic scenarios, including the
source-informed mean path and static stress tests.

### G.2 Endogenous Temperature-Feedback Component

The function:

`WildfireGIVE.apply_wildfire_temperature_feedback_co2!`

adds the feedback component. It connects:

- `baseline_co2` to `:Socioeconomic => :co2_emissions`;
- `temperature` to `:temperature => :T`;
- `output_co2` to the existing CO2-emissions identity.

The carbon cycle sees:

```text
baseline aggregate CO2
+ f(lagged global mean temperature, beta, phi_net, phi_missing)
```

in `GtC/yr`.

This is the central extension because it gives the marginal pulse a pathway to
affect future emissions: the pulse slightly raises temperature; that temperature
change slightly changes future wildfire CO2; the added CO2 then feeds back into
concentrations, forcing, temperature and damages.

### G.3 Placement Relative To The Marginal Pulse

GIVE estimates the SC-CO2 by comparing a baseline model run with a pulse model run.
The pulse is added using MimiGIVE's marginal-emissions machinery. The wildfire
extension is inserted upstream of the carbon cycle so that both baseline and pulse
worlds pass through the same CO2-cycle machinery.

This placement creates two different mechanisms:

- exogenous wildfire addition: the same wildfire path is added to the baseline and
  pulse worlds, so SCC changes only because the marginal ton occurs on a different
  baseline state;
- endogenous wildfire feedback: the pulse affects temperature, which affects future
  wildfire CO2, so SCC can also change through an emissions-feedback channel.

The negative-control logic is therefore straightforward. If the same exogenous fire
path is added to base and pulse worlds and SCC barely changes, the state-dependence
channel is small. If the endogenous feedback raises SCC more, the increase comes
from the marginal pulse's effect on future fire emissions.

### G.4 Unit Handling

The GIVE CO2 emissions input is in `GtC/yr`, not `GtCO2/yr`. Many wildfire
estimates are reported as CO2. The extension therefore uses explicit conversion
constants:

```julia
GTCO2_TO_GTC = 12.0 / 44.0
GTC_TO_GTCO2 = 44.0 / 12.0
```

The model input is always converted to `GtC/yr` before entering the carbon cycle.
Plots and manuscript tables often report `GtCO2/yr` because that is more familiar
for climate-policy readers.

## H. Model Experiments

### H.1 Deterministic Runs

The deterministic endogenous-feedback script is:

`wildfire_extension/run_temperature_feedback_scc.jl`

It produces quick, transparent comparisons between the original deterministic GIVE
baseline and a small number of wildfire-feedback scenarios. It writes:

- `deterministic_scc_summary.csv`;
- `deterministic_climate_damage_paths.csv`;
- `marginal_temperature_feedback_diagnostics.csv`;
- `benchmark_path_summary.csv`;
- `scenario_assumptions.csv`.

These runs are useful for mechanism checks because they are reproducible and cheap.
They are not a substitute for the Monte Carlo distribution.

### H.2 Paired Monte Carlo Runs

The paired Monte Carlo script is:

`wildfire_extension/run_temperature_feedback_mcs.jl`

The current manuscript uses 100 paired draws. The script accepts the number of draws
as a command-line argument, so the same code can run 10,000 draws later.

The pairing design is important. Each scenario is evaluated on the same sequence of
GIVE uncertainty draws as the baseline. This means scenario differences are less
noisy than unpaired differences because the same socioeconomic and climate
parameter draws appear in both the baseline and wildfire cases.

Current design:

- SCC year: 2020;
- pulse size: `1e-4 GtC`;
- random RFF-SP sample IDs: drawn from `1:10000`;
- random FaIR parameter IDs: drawn from `1:2237`;
- discounting: 2% near-term Ramsey configuration in the main reported figures;
- CIAM sea-level module: perfect foresight with GDP-per-capita option enabled;
- sectoral marginal-damage saving: disabled for the main SCC Monte Carlo to keep
  runtime manageable.

Output directory used for the current 100-draw run:

`wildfire_extension/output/wildfire_temperature_feedback_mcs_100_paired`

Key outputs:

- `all_scc_samples.csv`: one row per draw and scenario;
- `scc_summary.csv`: scenario-level SCC mean, median and percentiles;
- `all_feedback_parameter_draws.csv`: wildfire parameter draws used in each
  scenario and Monte Carlo replication.

### H.3 Separating Baseline And Wildfire Uncertainty

The current uncertainty presentation distinguishes:

- baseline GIVE uncertainty, represented by the spread of baseline SCC draws;
- wildfire-feedback parameter uncertainty, represented by the scenario-specific
  distributions of `beta`, `phi_net` and `phi_missing`;
- paired scenario-delta uncertainty, represented by the distribution of
  `SCC_scenario - SCC_baseline` for the same draw.

The R figure script creates separate outputs for these components:

- `paired_scc_delta_interval_summary_2pct.csv`;
- `wildfire_parameter_draw_summary.csv`;
- `uncertainty_source_diagnostics_2pct.csv`;
- `figure_paired_delta_intervals_2pct.png`;
- `figure_wildfire_parameter_uncertainty_2pct.png`;
- `figure_uncertainty_source_diagnostics_2pct.png`.

The limitation is that the current wildfire parameter distributions are stylized.
A submission-ready version should replace or supplement them with a formal
literature-derived uncertainty model.

## I. Sectoral And Mechanism Diagnostics

The sectoral diagnostic script is:

`wildfire_extension/run_sectoral_diagnostics.jl`

This script uses the source-informed exogenous wildfire pathway, not the endogenous
feedback Monte Carlo. It is designed to answer mechanism questions:

- Does added wildfire CO2 change global mean temperature?
- Do sectoral marginal damages move in expected directions?
- Are changes muted by logarithmic forcing, sectoral damage curvature, discounting
  or sea-level timing?
- Does the added CO2 actually enter the carbon cycle and persist?

The script calls GIVE with:

```julia
save_md = true
save_cpc = true
compute_sectoral_values = true
```

This causes the model to save marginal damages and sectoral outputs needed for
diagnostics. The outputs include:

- `sectoral_scc_samples.csv`;
- `sectoral_scc_summary.csv`;
- `sectoral_marginal_damage_summary_2pct.csv`;
- `sectoral_marginal_damage_difference_2pct.csv`;
- `deterministic_temperature_damage_paths.csv`;
- `unit_check_mean_wildfire_path.csv`;
- `wildfire_parameter_draws.csv`;
- `wildfire_emissions_draws.csv`;
- `mean_wildfire_emissions_path.csv`.

The sectoral outputs should be interpreted as diagnostics rather than final sectoral
incidence estimates. They are generated with a mean exogenous wildfire pathway to
keep the sectoral run manageable and visually interpretable.

### I.1 Why Some Sectoral Marginal Damages Can Fall

Some sectoral marginal damages can be lower under an added wildfire pathway even
when total damages rise. This is not a sign that the added carbon is ignored. It
reflects the definition of the SCC as a marginal effect, not total damages. A higher
baseline can change growth, adaptation, regional exposure and discounting in ways
that reduce the marginal difference between the pulse and no-pulse worlds in some
modules and periods. This can occur even if total damages are larger. The sectoral
diagnostics were added specifically to make these mechanisms visible rather than
infer them only from aggregate SCC values.

## J. Regional Damage Maps

The regional mapping script is:

`wildfire_extension/run_regional_damage_map_diagnostics.jl`

The maps are diagnostic. They do not estimate where fires occur, and they do not
claim to allocate the welfare burden of wildfire carbon comprehensively. They show
where selected modeled climate damages change under the source-informed mean
wildfire CO2 path.

Included modules:

- Cromar temperature-related mortality damages at country level;
- Clarke energy damages at country level;
- Moore agriculture damages at FUND-region level, allocated to countries by
  baseline GDP share within each FUND region.

Excluded modules and channels:

- CIAM sea-level-rise damages in the country map;
- wildfire smoke mortality;
- non-CO2 fire pollutants and aerosol effects;
- ecosystem damages not already represented in GIVE;
- adaptation, suppression and fuel-management responses outside the included GIVE
  modules.

Discounted marginal damages are calculated using the same near-term Ramsey logic as
the 2% headline SCC configuration. The maps use Natural Earth polygons for display.

Output directory:

`wildfire_extension/output/wildfire_regional_damage_diagnostics`

Key outputs:

- `regional_damage_delta_by_country.csv`;
- top-20 country and regional summary CSVs;
- figure files generated by `make_png_pdf_figures.R`.

## K. Figure Generation

The figure-generation script is:

`wildfire_extension/make_png_pdf_figures.R`

It reads the Julia outputs and writes PNG and PDF versions of the figures. SVG files
are no longer the primary deliverable because they were not convenient for the user
to open.

Main figure families:

1. conceptual/audit schematic;
2. wildfire emissions scale and atmospheric stock increment;
3. SCC distributions and paired scenario deltas;
4. mechanism decomposition;
5. source-attribution map;
6. regional damage diagnostics;
7. sectoral marginal-damage changes over time;
8. uncertainty-source diagnostics.

The source-attribution map is not a GIVE model output. It uses a transparent proxy
that assigns higher source weight to boreal and fire-prone regions emphasized by the
wildfire-carbon literature and by the Canada 2023 scale check. It is intended to
visualize potential source regions for additional fire carbon, not to allocate
damages or claim observed emissions by country.

The regional damage maps are separate. They use GIVE diagnostic outputs to show
where selected modeled damages change under the added CO2 pathway.

## L. Validation And Unit Checks

### L.1 Baseline Replication

The first validation step is to run the unmodified deterministic GIVE baseline and
confirm that it approximately reproduces the published preferred SC-CO2 magnitude.
The deterministic baseline used in the early diagnostic runs produced an SC-CO2 of
approximately `139.10 2020 USD/tCO2`. This is lower than the published preferred
mean because it is a deterministic configuration, not the full published Monte
Carlo.

The 100-draw paired Monte Carlo baseline produces a distribution closer to the
published result, but it is still a small sample relative to the 10,000-draw
published-style run. For submission, the 10,000-draw run should replace the 100-draw
numbers in the main text.

### L.2 CO2-To-Carbon Conversion Checks

Every path added to GIVE is converted to `GtC/yr` before entering the carbon cycle.
The key conversion checks are:

```text
1 GtC = 44/12 GtCO2 = 3.6667 GtCO2
1 GtCO2 = 12/44 GtC = 0.2727 GtC
```

Example:

```text
Canada excess 2023 = 526 TgC
                   = 0.526 GtC
                   = 1.929 GtCO2
```

This conversion is coded in `WildfireGIVE.jl`, not performed manually in plotting
scripts.

### L.3 Atmospheric Stock Scale Checks

Annual emissions are flows. Atmospheric CO2 is a stock. Large annual fire events can
look small when expressed as a fraction of the atmospheric carbon stock because the
atmosphere contains roughly hundreds of gigatonnes of carbon. For example, a
1.929 GtCO2 annual increment is `0.526 GtC`. Relative to an atmospheric stock near
`~880 GtC`, that is about `0.06%` of the atmospheric stock in that year. The same
flow can be several percent of annual anthropogenic emissions. This distinction is
made explicit in the manuscript because it is easy to confuse flow shares with stock
shares.

### L.4 Double-Counting Checks

Double-counting is addressed in four ways:

1. The code audit confirms that GIVE lacks an endogenous fire-carbon feedback.
2. The manuscript does not claim that all fire carbon is absent from aggregate
   baseline emissions.
3. The central scenarios multiply gross additional fire carbon by `phi_net` and
   `phi_missing`.
4. Gross fire cases are labeled as stress tests rather than central estimates.

The unresolved limitation is that `phi_missing` is not empirically identified from
the RFF-SP source data. It is an accounting uncertainty parameter introduced because
the aggregate RFF-SP pathway cannot be decomposed.

## M. Reproducible Run Order

The following commands reproduce the current analysis after the original GIVE
replication archive has been installed, the extension repository has been cloned as
`wildfire_extension/`, the Julia environment has been instantiated, and the USDA
archive has been downloaded and extracted. The commands use portable placeholders:

```bash
GIVE_ROOT=/path/to/rennert-give-replication
EXT_ROOT="$GIVE_ROOT/wildfire_extension"
USDA_RAW=/path/to/extracted/RDS-2018-0021
```

### M.1 Process USDA Fire Projection Data

```bash
julia --project="$GIVE_ROOT" \
  "$EXT_ROOT/process_usda_val_martin.jl" \
  "$USDA_RAW" \
  "$EXT_ROOT/source_data/usda_val_martin_fire_projection_summary.csv"
```

### M.2 Run Deterministic Endogenous Feedback Scenarios

```bash
julia --project="$GIVE_ROOT" \
  "$EXT_ROOT/run_temperature_feedback_scc.jl" \
  "$EXT_ROOT/output/wildfire_temperature_feedback"
```

### M.3 Run 100-Draw Paired Monte Carlo

```bash
"$EXT_ROOT/run_temperature_feedback_mcs.sh" \
  100 \
  "$EXT_ROOT/output/wildfire_temperature_feedback_mcs_100_paired" \
  20260503 \
  all
```

For a 10,000-draw run, replace `100` with `10000`. The code path is the same, but
runtime is much longer.

### M.4 Run Sectoral Diagnostics

```bash
julia --project="$GIVE_ROOT" \
  "$EXT_ROOT/run_sectoral_diagnostics.jl" \
  100 \
  "$EXT_ROOT/output/wildfire_sectoral_diagnostics_100" \
  20260502
```

### M.5 Run Regional Damage Diagnostics

```bash
julia --project="$GIVE_ROOT" \
  "$EXT_ROOT/run_regional_damage_map_diagnostics.jl" \
  "$GIVE_ROOT" \
  "$EXT_ROOT/output/wildfire_regional_damage_diagnostics"
```

### M.6 Generate Figures

```bash
Rscript "$EXT_ROOT/make_png_pdf_figures.R" "$GIVE_ROOT"
```

### M.7 Render Manuscript And Supplement

```bash
pandoc "$EXT_ROOT/manuscript/wildfire_carbon_feedback_ncc_draft.md" \
  -o "$EXT_ROOT/manuscript/wildfire_carbon_feedback_ncc_draft.html"

pandoc "$EXT_ROOT/manuscript/wildfire_carbon_feedback_ncc_draft.md" \
  -o "$EXT_ROOT/manuscript/wildfire_carbon_feedback_ncc_draft.pdf"

pandoc "$EXT_ROOT/manuscript/methods_appendix.md" \
  -o "$EXT_ROOT/manuscript/methods_appendix.html"

pandoc "$EXT_ROOT/manuscript/methods_appendix.md" \
  -o "$EXT_ROOT/manuscript/methods_appendix.pdf"
```

The rendered files are written to:

`wildfire_extension/manuscript/`

## N. Output Files And Their Roles

The most important output files are:

- `output/wildfire_temperature_feedback_mcs_100_paired/scc_summary.csv`:
  scenario-level SCC summary statistics;
- `output/wildfire_temperature_feedback_mcs_100_paired/all_scc_samples.csv`:
  draw-level SCC values;
- `output/wildfire_temperature_feedback_mcs_100_paired/all_feedback_parameter_draws.csv`:
  draw-level wildfire-feedback parameters;
- `output/wildfire_temperature_feedback_mcs_100_paired/paired_scc_delta_interval_summary_2pct.csv`:
  paired scenario-delta intervals;
- `output/wildfire_sectoral_diagnostics_100/sectoral_marginal_damage_difference_2pct.csv`:
  sectoral marginal-damage differences over time;
- `output/wildfire_sectoral_diagnostics_100/deterministic_temperature_damage_paths.csv`:
  deterministic concentration, temperature and damage paths;
- `output/wildfire_regional_damage_diagnostics/regional_damage_delta_by_country.csv`:
  country-level diagnostic damage changes used for maps;
- `source_data/usda_val_martin_fire_projection_summary.csv`:
  cleaned USDA fire-activity ratios.

These CSVs are the authoritative source for the manuscript numbers and figures.
Figures should be regenerated from these files rather than edited manually.

## O. Current Limitations Of The Replication Package

The current package is close to a reproducible research archive but is not yet a
submission-grade archive. The remaining gaps are:

- the main SCC results use 100 paired Monte Carlo draws, not 10,000;
- wildfire parameter distributions are transparent but stylized;
- `phi_missing` is an accounting uncertainty parameter, not empirically identified;
- raw USDA NetCDF files are external to the GitHub repository and must be
  downloaded from the USDA DOI, while the cleaned summary CSV is tracked in the
  extension repository;
- the source-attribution map uses a proxy rather than a gridded global fire-carbon
  forecast;
- smoke mortality and non-CO2 fire pollutants are not included in the CO2-only SCC
  extension;
- the current manuscript should not be interpreted as estimating total wildfire
  damages.

For submission, the raw-data download script, 10,000-draw outputs, formal wildfire
uncertainty model and archived code release should be finalized.

## P. AI-Assisted Research Programming

A generative AI coding assistant was used as a research-programming aid. The human
author specified the research question, modeling hypotheses, acceptance criteria and
interpretation. The assistant was used to inspect replication code, identify
relevant files, search and summarize candidate literature, draft and revise Julia,
R, Python, HTML and LaTeX/Markdown scripts, generate preliminary figures and
tables, and identify unit, model-wiring and double-counting checks. All source
selection, modeling choices, code execution, numerical results, manuscript text and
interpretation were reviewed and approved by the human author, who takes
responsibility for the accuracy and integrity of the work. The AI system is not
listed as an author because it cannot satisfy authorship accountability criteria. A
prompt-history appendix can be provided for transparency.

| Research task | AI role | Human verification | Output |
|---|---|---|---|
| Code audit | Located model paths and variables | Human reviewed interpretation | Audit appendix |
| Literature search | Suggested candidate papers and datasets | Human selected sources and claims | Reference set |
| Model extension | Drafted implementation | Human reviewed assumptions and results | Julia scripts |
| Figures | Generated plotting scripts | Human selected and revised figures | Main and SI figures |
| Manuscript drafting | Produced draft text | Human revised and accepts responsibility | Manuscript and SI |

## Q. Supplementary Figure Inventory

The figure script writes both PNG and PDF files. The main manuscript should include
a small number of high-information figures; the remaining figures can appear in the
Supplement.

Recommended main-text figures:

- `figure_conceptual_audit_small.png`;
- `figure_fire_carbon_scale.png`;
- `figure_scc_distribution_truncated.png`;
- `figure_mechanism_decomposition.png`;
- one map figure, preferably the source-attribution or incremental-damage map.

Recommended Supplement figures:

- `figure_paired_delta_intervals_2pct.png`;
- `figure_wildfire_parameter_uncertainty_2pct.png`;
- `figure_uncertainty_source_diagnostics_2pct.png`;
- `figure_sectoral_marginal_damage_delta_2pct.png`;
- `figure_temperature_paths.png`;
- `figure_regional_damage_map.png`;
- `figure_source_proxy_map.png`.

## R. Minimum Information Needed To Replicate The Extension

A reader can reproduce the current analysis with the following information:

1. the Rennert et al. GIVE replication repository and MimiGIVE package;
2. Julia 1.6.4 and the supplied Julia package environment;
3. the wildfire extension files under `wildfire_extension/`;
4. the cleaned USDA summary CSV, or the raw USDA archive plus
   `process_usda_val_martin.jl`;
5. the Natural Earth GeoJSON file for map generation;
6. the run order in Section M;
7. the parameter distributions in Section F;
8. the output file map in Section N.

The scientific interpretation requires one additional assumption: the central
scenarios estimate only residual net-persistent wildfire CO2 that is not already
embedded in the aggregate baseline emissions pathway. Without that assumption, a
gross additive wildfire pathway would risk double counting.
