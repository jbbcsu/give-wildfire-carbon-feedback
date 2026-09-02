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

## Phase 0 — scope and accounting (authorized)

The primary estimand is the model-conditional global agricultural SCC from a
joint temperature--water replacement for MooreAg. It includes mean/seasonal
precipitation, within-season timing and distribution, drought, and heavy/wet
exposure jointly with temperature. Precipitation quantity and distribution are
predeclared accounting decompositions within that joint prediction, not a
separately observed causal SCC. Non-coastal riverine/pluvial infrastructure
flooding is deferred behind a preserved separate interface.

Model hierarchy is evidence-led. The parsimonious direct-weather reference is
joint temperature plus crop-calendar growing-season precipitation quantity.
Timing, concentration, occurrence, intensity, dry-spell, and wet-extreme terms
are retained only if pre-specified outer holdouts show robust, stable
incremental value; null, unstable, and worse results are reported, and the
quantity reference may become primary. PDSI/scPDSI and SPEI are serious
competing climatic-water-balance representations, not minor checks. Direct
precipitation-pattern, climatic-water-balance, and soil-moisture families are
evaluated separately and never summed or mechanically stacked unless a
separate pre-specified attribution design establishes nonoverlap.

**Novelty and overlap gate:** a 2024 working paper by Wenz, Kotz, Callahan, and
Stechemesser reports a GIVE integration of total precipitation, wet-day
frequency, and extreme daily rainfall in a reduced-form subnational
productivity framework. This checkout does not contain that implementation,
and the planned paper must not duplicate or stack it. The proposed distinct
contribution is an evidence-led test of whether crop-stage precipitation
distribution improves on seasonal quantity, a defensible single-outcome
treatment of rainfed/irrigated exposures, serious comparison with drought-index
families, and an explicit replacement of GIVE agriculture with no overlapping
precipitation add-on. A null distribution result is publishable information,
not a reason to privilege a more elaborate model.
Flood validation is outside the current paper.

Do not run the new module alongside the optional DICE or Howard--Sterner
aggregate functions: those are broad reduced-form damage functions and their
overlap is unidentified.  Run it with GIVE's sectoral bundle only.  For
agriculture, the authorized choice is to replace MooreAg with a jointly
estimated temperature--water response, not add a precipitation residual.
For coastal flooding, use CIAM alone in the main specification; a
coastal-rainfall add-on requires event-level evidence that excludes
surge/sea-level damages already in CIAM.

## Phase 1 — matched climate-to-crop-feature driver

The project owner selected the direct daily ISIMIP3b crop-feature response
route as primary on 25 August 2026. Derive exact crop-calendar features from
version-pinned daily ESM/member fields, fit ESM-specific feature responses to
same-realization GMST, and evaluate matched FAIR baseline/pulse paths with
common residual innovations. Scenario contrasts are training support, not
one-tonne CO2 experiments.

Do not build a new free-standing weather emulator unless this route fails
predeclared validation. The previously proposed MESMER-M-TP plus
pattern-scaled Markov--gamma chain is now a fallback/benchmark, superseded as
the primary route. MESMER-X remains an Rx1day benchmark and STITCHES a daily
multivariate sequence benchmark. RIG and ACE2-SOM remain external candidates
until their crop-feature and small-pulse behavior can be tested.

The USEPA `pattern-scaled-climate-variables` workflow is an additional
annual-mean benchmark, not the primary route. Its PEEPS precipitation slopes,
country aggregation, model-continuity screen, and FAIR--GCM rank-pairing idea
will be tested under the fixed contract in `EPA_PATTERN_SCALING_BENCHMARK.md`.
Agricultural results continue to use crop-calendar daily features and
crop-area/value weights; annual area/GDP/population-weighted patterns cannot
substitute for the joint crop response.

The primary feature-response chain is driven by each matched FAIR
forcing/temperature draw, according to its validated input contract:

`T(t) -> [P_ann, P_season, Rx1day, Rx5day, wet-day frequency, dry-spell]_(t,r)`.

Fit ESM-specific CMIP6/ScenarioMIP feature responses while retaining model,
scenario, internal-variability, and bias-adjustment uncertainty. Preserve
spatial dependence by sampling a model/member jointly across crop grids rather
than independently sampling country effects. Derive crop-stage totals,
distribution, wet-day, dry-spell, and extreme indices from daily fields before
welfare aggregation. Annual SCC timesteps receive crop-year response
expectations and their retained uncertainty.

For the prioritized agriculture path, resolve daily fields by crop calendar
and crop stage, not just country-year. Run existing GGCMI/ISIMIP process
ensembles and direct daily climate features as benchmarks. The first
empirical response should establish the parsimonious joint
temperature--seasonal-quantity benchmark. Direct dry-spell, water-excess, and
timing extensions must add stable held-out value. PDSI/scPDSI and SPEI must be
evaluated as alternative water-stress families under the same outer splits;
selection of any added timing or drought representation must be held-out
validated and pre-specified.

**Current empirical checkpoint.** Hash-locked screens for maize and soybean in
1982--1989 and 2012--2016 are complete. The early panel contains small,
heterogeneous gains from distribution features; the later panel has no
distribution family that improves seasonal quantity across all three
holdouts. All maize extensions are worse spatially and temporally in the later
panel, and all soybean extensions are worse temporally. A separate
minimal-basis complete-support sensitivity also ranks joint temperature plus
seasonal quantity first in every crop/holdout cell, although conditioning on
complete GDHY support can select the sample. Therefore seasonal quantity
remains the reference and no distribution extension has cleared the retention
gate. Historical aggregate-regime scPDSI candidate inputs now pass raw-source
and calendar manifest binding plus complete derived-input allocation
recomputation for maize and soybean in both periods, but they remain unfitted.
Four data-only common-support bundles are now validated as separate 54-feature
direct-weather and 16-feature scPDSI views. Their common rows/observed outcomes
and direct-only dropped rows/observed outcomes are maize 1982--1989,
240,784/115,758 and 24,744/1,921; soybean 1982--1989,
176,537/47,653 and 14,935/269; maize 2012--2016,
150,490/59,772 and 15,465/1,046; and soybean 2012--2016,
110,336/26,601 and 9,334/147. Every scPDSI-only drop count is 0/0. Validation
recomputes only from the immediate candidate inputs; upstream raw-source
validation receipts are not bound and remain an external prerequisite. The
subsequent coefficient-suppressing historical diagnostic is now complete on
209,036 consecutive-year pairs. Seasonal quantity has the lowest mean spatial-
fold RMSE for maize and soybean, but improvements over controls are below 1%
and MAE rankings are less uniform; richer scPDSI summaries add stress-specific
rather than stable general predictive value. A paired 10-degree-cell loss
sensitivity places zero inside all 12 scPDSI-versus-direct RMSE/MAE intervals
and remains conditional on fixed OOF fits. Neither result identifies a causal
response or selects a production model. SPEI and soil-moisture families,
buffered/leave-region validation, a continuous all-year panel, and causal
identification remain next empirical gates. Seasonal quantity remains the
reference; distribution and drought families may not be stacked or selected
by SCC magnitude.

The SPEI route is now source-locked before construction. Separate 1-, 3-, and
6-month fields will be computed on each panel's native weather grid from the
already acquired direct-weather inputs, using Hargreaves-Samani reference ET
and calendar-month log-logistic UBPWM fits calibrated on 1982--2011 and frozen
before the 2012 terminal block. Published NOAA SPEI and SPEIbase are
retrospective checks rather than terminal-score inputs. The current scaffold
authorizes only index construction and common-support auditing; it does not
authorize an outcome fit, causal interpretation, damage, or SCC use.

## Phase 2 — damage functions (empirical work required)

1. **Riverine/pluvial flooding (deferred):** preserve an interface for a later
   event annual exceedance probability or expected annual loss as a function
   of basin heavy-rainfall indicators,
   antecedent wetness/proxy, exposure, protection/adaptation, and income.
   Use gridded/basin hazard data and losses with fixed effects; do not infer
   fluvial hazard from country-average annual rainfall alone.
2. **Agriculture (priority):** estimate crop/region responses jointly in
   temperature, growing-season water balance, onset/cessation, dry spells,
   water excess and extremes, then map once to welfare/food-price damages.
   It must **replace**, not be residualized onto, the temperature-indexed MooreAg
   channel.  Benchmark against GGCMI/ISIMIP; use ML only as a constrained,
   held-out predictive comparator after the transparent panel model.
   Compare against OSCAR-crop v1.0 as the mandatory aggregate growing-season
   water benchmark. Test rather than assume whether daily/stage timing,
   dry/wet persistence, or extremes add value beyond seasonal quantity, and
   compare direct-weather results with separately specified PDSI/scPDSI and
   SPEI families.
3. **Other mechanisms:** include only with a separately identified response
   and accounting boundary: drought/water-supply losses, hydropower,
   landslides, and water-borne disease are candidates.  Avoid adding
   temperature-mortality or energy effects unless the empirical endpoint
   excludes the existing Cromar/energy channels.

Each estimated response must disclose adaptation assumptions, exposure
evolution, price/spillover treatment, loss valuation, and an out-of-sample
check.  Negative precipitation effects and benefits remain permitted.

## Phase 3 — model integration and SCC (directly implementable once estimated)

Use the isolated `CropResponseAggregation` and `JointAgriculture` components
as the executable contract. Add the selected climate driver and estimated
response, then replace MooreAg's `agcost` pathway; do not add a second
agricultural input to `DamageAggregator`. Keep this in the isolated project
rather than altering the baseline or wildfire branches. Connect annual
regional losses to net consumption. Compute paired baseline/pulse runs with
matched FAIR, climate-pattern, vulnerability, and socioeconomic draws.
Discount the difference in consumption/welfare using GIVE's existing SCC
procedure and report global and sectoral marginal damages.

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

## Decisions resolved

1. Main estimand: global SCC.
2. Agriculture: joint temperature--precipitation replacement for MooreAg.
3. Priority: agriculture; separate non-coastal infrastructure flooding is
   deferred while its interface remains documented.
4. Adaptation: report fixed, trend, and upper scenarios separately.

No additional user decision is required to continue data, estimation, climate
benchmark, and validation work. A later decision will be requested only if
multiple climate-emulation chains pass the predeclared gates with a material
accuracy--compute tradeoff.
