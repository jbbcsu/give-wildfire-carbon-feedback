# Research and implementation plan

## Baseline audit (completed)

The baseline GIVE package has no general climate-to-precipitation module and
no riverine or pluvial flood-damage component.  Its apparent precipitation
references are Antarctic-ice-sheet accumulation parameters, used in the
BRICK sea-level pathway, not socio-economic rainfall damages.  `MimiCIAM`
calculates coastal sea-level-rise/storm costs.  `MooreAg.Agriculture` receives
only global temperature, so its agricultural damages are not a precipitation
response.  `DamageAggregator` currently combines mortality, agriculture,
energy, and optional aggregate damage functions; it is the eventual insertion
point, after an explicit overlap choice.

Relevant baseline locations (read-only for this project):

* `paper-2022-scc-give-zenodo/packages/MimiGIVE/src/main_model.jl`
* `paper-2022-scc-give-zenodo/packages/MimiGIVE/src/components/DamageAggregator.jl`
* `paper-2022-scc-give-zenodo/packages/MooreAg/src/core/AgricultureComponent.jl`
* `paper-2022-scc-give-zenodo/packages/MimiGIVE/src/main_ciam.jl`

## Phase 0 — scope and accounting (user decision before integration)

Define the estimand as the present value of the damage difference caused by a
one-tonne CO2 pulse through precipitation, conditional on the model's
temperature and socioeconomic paths.  Default scope: mean/seasonal
precipitation, heavy precipitation, and non-coastal riverine/pluvial flooding.

**Novelty gate:** a 2024 working paper by Wenz, Kotz, Callahan, and
Stechemesser reports a GIVE integration of total precipitation, wet-day
frequency, and extreme daily rainfall in a reduced-form subnational
productivity framework.  This checkout does not contain that implementation,
but the planned paper must not duplicate or stack it.  The proposed distinct
contribution is a sectorally disaggregated climate-to-hydrology-to-loss module
with flood validation and explicit overlap accounting.  Resolve the paper's
status and intended relationship before empirical estimation.

Do not run the new module alongside the optional DICE or Howard--Sterner
aggregate functions: those are broad reduced-form damage functions and their
overlap is unidentified.  Run it with GIVE's sectoral bundle only.  For
agriculture, choose one of: (A) replace MooreAg with a jointly estimated
temperature--water response; (B) estimate a precipitation residual orthogonal
to the MooreAg temperature response and add only that residual; or (C) report
agriculture separately.  For coastal flooding, use CIAM alone in the main
specification; a coastal-rainfall add-on requires event-level evidence that
excludes surge/sea-level damages already in CIAM.

## Phase 1 — published climate-to-precipitation emulators

Do not build a new free-standing emulator unless published systems fail
predeclared validation. The literature audit in
`CLIMATE_PRECIPITATION_EMULATOR_AUDIT.md` identifies MESMER-M-TP as the monthly
backbone candidate, the Kemsley et al. pattern-scaled Markov--gamma generator
for daily occurrence/intensity and dry-spell structure, MESMER-X for Rx1day,
and STITCHES as the principal daily multivariate benchmark.

The published-method chain is driven by each matched FAIR temperature draw:

`T(t) -> [P_ann, P_season, Rx1day, Rx5day, wet-day frequency, dry-spell]_(t,r)`.

Calibrate or reuse ESM-specific CMIP6/ScenarioMIP responses, retaining model,
scenario, internal-variability and downscaling uncertainty. Preserve
spatial dependence by sampling a model/member jointly across regions rather
than independently sampling country effects.  Bias-adjust and aggregate daily
fields to basin/country exposure weights before estimating extreme indices.
Annual SCC timesteps receive annual loss expectations; the extreme-value layer
converts subannual hazards into annual expected damage and retains tail risk.

For the prioritized agriculture path, resolve daily fields by crop calendar
and crop stage, not just country-year. Run existing GGCMI/ISIMIP process
ensembles and direct daily climate features as benchmarks. The first
empirical response should jointly model seasonal precipitation, dry spells,
water excess and temperature; selection of additional timing features must be
held-out validated and pre-specified.

## Phase 2 — damage functions (empirical work required)

1. **Riverine/pluvial flooding:** estimate event annual exceedance probability
   or expected annual loss as a function of basin heavy-rainfall indicators,
   antecedent wetness/proxy, exposure, protection/adaptation, and income.
   Use gridded/basin hazard data and losses with fixed effects; do not infer
   fluvial hazard from country-average annual rainfall alone.
2. **Agriculture (priority):** estimate crop/region responses jointly in
   temperature, growing-season water balance, onset/cessation, dry spells,
   water excess and extremes, then map once to welfare/food-price damages.
   It must **replace**, not be residualized onto, the temperature-only MooreAg
   channel.  Benchmark against GGCMI/ISIMIP; use ML only as a constrained,
   held-out predictive comparator after the transparent panel model.
3. **Other mechanisms:** include only with a separately identified response
   and accounting boundary: drought/water-supply losses, hydropower,
   landslides, and water-borne disease are candidates.  Avoid adding
   temperature-mortality or energy effects unless the empirical endpoint
   excludes the existing Cromar/energy channels.

Each estimated response must disclose adaptation assumptions, exposure
evolution, price/spillover treatment, loss valuation, and an out-of-sample
check.  Negative precipitation effects and benefits remain permitted.

## Phase 3 — model integration and SCC (directly implementable once estimated)

Use the isolated `PrecipitationDamages` component as the interface contract.
Add the climate emulator, then the component, then a new additive input to a
copy of `DamageAggregator`; do this in a new package/module rather than
altering the baseline or wildfire branches.  Connect annual country losses to
net consumption.  Compute paired baseline/pulse runs with matched FAIR,
climate-pattern, vulnerability, and socioeconomic draws.  Discount the
difference in consumption/welfare using GIVE's existing SCC procedure and
report global, domestic (only after a defined national allocation rule), and
sectoral marginal damages.

## Phase 4 — calibration, validation, and uncertainty

Calibrate historical climate patterns against reanalysis/observational
precipitation and validate projected index distributions against held-out GCMs.
Validate flood and crop models by spatial and temporal held-out loss/yield
prediction, not in-sample fit alone.  Propagate: FAIR climate draws, GCM and
downscaling choice, internal variability, extreme-value tails, exposure,
adaptation/protection, damage coefficients, SSPs, discounting, and accounting
choice.  Publish deterministic baselines, Sobol/variance decomposition,
leave-one-model-out checks, alternative basin-to-country mappings, and upper
tail SCC diagnostics.  Require conservation tests (zero warming => zero
incremental precipitation damage), unit tests, and a no-double-counting
reconciliation table.

## Phase 5 — paper strategy

Paper 1 should be a standalone, modular SCC contribution: data and emulator;
empirical damage estimates; accounting with existing GIVE sectors; paired SCC
results; and uncertainty/decomposition.  Release code/data provenance, frozen
draw IDs, and replication scripts.  Keep exploratory mechanisms in appendices
until they clear the overlap and validation criteria.  A pre-analysis plan
should lock the main sector set, counterfactual, and aggregation rule before
estimating SCC results.

## Decisions needed

1. Main estimand: global SCC only, or also a domestic allocation?
2. Agriculture: replacement, residualized add-on, or separate reporting?
3. Phase-1 scope: begin with riverine/pluvial flood plus agriculture, or flood
   only while agricultural estimation is developed?
4. Adaptation: hold present protection fixed, use SSP-consistent protection,
   or show both as named scenarios?
