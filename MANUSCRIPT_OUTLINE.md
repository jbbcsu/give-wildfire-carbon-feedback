# Manuscript blueprint: climate-driven precipitation patterns and the global SCC

## Working title

**Crop-calendar precipitation patterns, global agricultural damages, and the social cost of carbon**

Alternative while results remain preliminary: **A framework for incorporating climate-driven precipitation-pattern risks in global agricultural social-cost-of-carbon estimates**.

## Central contribution and claim boundary

The paper estimates a *replacement* agricultural damage sector for GIVE that jointly represents temperature and crop-calendar-aligned precipitation features, then evaluates a CO2-pulse welfare difference in matched global SCC simulations. Features include seasonal quantity, dry spells, and wet extremes, not annual precipitation alone. The sector replaces the temperature-indexed MooreAg pathway, which has no explicit separable precipitation input in this checkout; it is never an incremental add-on.

The empirical hierarchy is evidence-led: joint temperature plus crop-season
precipitation quantity is the parsimonious reference; timing/distribution terms
survive only with robust incremental outer-holdout value; PDSI/scPDSI and SPEI
are serious separate competitors. Null and adverse comparisons are reported,
and model choice is never based on SCC magnitude.

Allowed claims, contingent on passing the registered analyses:

1. Historical predictive/conditional response estimates for the declared data, crops, spatial support, and specification.
2. Model-conditional SCC implications, conditional on climate, adaptation, welfare mapping, and GIVE settings.
3. An accounting decomposition associated with precipitation features in the joint response—not a uniquely identified causal precipitation effect where weather variables covary.

Do not claim a global causal effect from predictive skill alone, a net-of-adaptation-investment result while adaptation cost remains zero, or any inland infrastructure-flood estimate. Temperature, CO2 fertilization, and market/trade feedback must each enter once in a named part of the model chain.

## Abstract template (180–220 words)

*Motivation:* Existing IAM agriculture sectors commonly compress climate into annual/global temperature and cannot test rainfall timing, dry spells, or water excess.

*Methods:* We construct crop-calendar/growth-stage daily-climate features for [crops], [years], and [spatial unit]; estimate a pre-specified joint temperature–precipitation response with fixed effects and uncertainty; and benchmark against multi-model gridded crop-model ensembles. We translate the replacement response once through [welfare layer] and run matched baseline/one-tonne-CO2-pulse GIVE simulations under fixed, trend, and upper adaptation scenarios.

*Results:* State only completed results: coverage, holdout skill, calibration, projected yield/welfare changes, and global SCC distribution. Report the joint agricultural result first; label precipitation-only results as decomposition.

*Interpretation:* This is a model-conditional agriculture extension; CIAM continues to own coastal effects and inland infrastructure flooding is deferred.

## Main-text architecture

### 1. Introduction (~900 words)

1. State the assessed physical basis for changes in mean and heavy precipitation (IPCC AR6 WGI Ch. 11).
2. Explain crop-stage relevance of water availability, dry spells, and water excess without presuming a universal response.
3. Identify the GIVE gap: MooreAg accepts global temperature and has no precipitation parameter.
4. Position global crop ensembles (Rosenzweig et al. 2014), empirical climate and agriculture work (Ortiz-Bobea et al. 2021), crop-model forcing/data (Jägermeyr et al. 2019), and the crop-to-GTAP-to-SCC design (Moore et al. 2017). None supplies an automatically additive rainfall coefficient.
5. Preview: crop-calendar features; joint replacement response; matched SCC accounting; explicit adaptation scenarios; reproducible provenance/tests.

### 2. Design and accounting boundary (~700 words)

Define the estimand as the discounted global welfare difference between matched pulse and baseline draws, produced by the replacement agriculture sector. Include this pathway:

CO2 pulse → climate realization → daily crop-season features → joint crop response → welfare mapping → consumption → SCC.

Explain MooreAg replacement, CIAM retention for sea-level/storm-surge coastal costs, and exclusion of inland infrastructure floods. Declare the pre-specified attribution rule (e.g., Shapley across temperature and precipitation feature groups), clearly as accounting attribution.

### 3. Data and feature construction (~900 words)

Describe the separate roles of GDHY yields, crop calendars, daily historical weather, ISIMIP daily projections/bias-adjusted climate, harvested-area and irrigation weights, and welfare inputs. Define eligible crop seasons, historical baseline, cross-calendar-year handling, spatial crosswalks, and missing-data exclusions before outcome inspection. Specify seasonal precipitation/water balance, dry spell, wet-day, and wet-extreme features.

Temperature, CO2, radiation, and—where defensible—VPD are joint covariates so their signal is not silently attributed to precipitation. Feature inclusion is subject to the preregistered validation gate.

### 4. Empirical response and adaptation (~1,100 words)

State the exact outcome scale and estimating equation: location/crop/year effects; crop-stage temperature and precipitation-pattern features; interactions; regime-specific response bases combined before fitting one aggregate crop-grid yield outcome; crop pooling/regularization; and spatially robust uncertainty. Prespecify nested, spatial-blocked, temporal, and extreme-year selection tests.

| Scenario | Interpretation | Permitted wording |
|---|---|---|
| Fixed | Historical response persists | Conditional no-additional-adaptation case |
| Trend | Configured attenuation schedule | Sensitivity, not realized-adaptation forecast |
| Upper | Configured upper-effectiveness schedule | Feasibility-style bound, not net-benefit forecast |

Name the CO2-fertilization treatment and whether it is estimated, sourced from crop-model scenarios, or held fixed. Quantify adaptation costs only with an independent cost model.

### 5. Validation, benchmarks, and uncertainty (~900 words)

Report spatial, temporal, and extreme-event holdouts before SCC projections. Compare empirical projections to GGCMI/ISIMIP ranges as a structural benchmark rather than pooling by default. Evaluate alternate weather/bias correction, crop calendar, feature set, response form, and welfare mapping. Propagate matched FAIR/climate, GCM, socioeconomic, response, adaptation, and discount draws; show importance decomposition and leave-one-GCM-out results.

### 6. SCC results (~1,000 words)

Lead with the total joint agricultural replacement SCC: global difference, uncertainty interval, sign probability, and crop/FUND-region breakdown. Then show adaptation and input uncertainty. Show precipitation attribution only after the joint total and with its decomposition rule. State explicitly that infrastructure-flood damages are absent. Give MooreAg as a comparator, never a summand.

### 7. Discussion (~900 words)

Separate historical identification from future extrapolation. Discuss limits from yield data, calendars, irrigation, CO2, market mediation, and tails. Set out a non-overlapping future inland-flood module. Close with code/data release commitments and strict isolation from wildfire work.

## Primary figures

1. **Accounting/data flow:** CO2 pulse to SCC; label MooreAg “replaced,” CIAM “retained,” and infrastructure flooding “deferred.”
2. **Crop-calendar features:** daily precipitation/temperature, stages, dry-spell and wet-extreme definitions for representative rain-fed/irrigated crop.
3. **Coverage and holdouts:** eligible observations/map plus space/time/extreme partitions.
4. **Joint response surfaces:** crop-specific aggregate-outcome panels with regime-weighted exposure bases and uncertainty; only retained feature responses receive central placement.
5. **Projection benchmark:** empirical regional crop effects versus GGCMI/ISIMIP ranges and alternate inputs; agreement is not causal validation.
6. **SCC distributions:** matched draws for fixed/trend/upper; joint total primary and precipitation attribution separately labeled.
7. **Robustness:** variance/importance decomposition, leave-one-GCM-out, and zero-warming conservation check.

## Primary tables

1. Scope/no-double-counting register: endpoint, inclusion, existing GIVE owner.
2. Provenance: source, version, license, coverage, checksums, access date.
3. Features: units, formula, stage, transformation, missingness/selection rule.
4. Estimation/validation: all holdout partitions and calibration metrics.
5. SCC: joint and attribution results, percentiles, scenario, welfare/discount settings, and draw count.

## Supporting-information allocation and wording discipline

Put all candidate-feature screens, coefficients, alternate forms, regional diagnostics, climate members, ML comparisons, exclusion logs, and SCC draws in SI, including null results. Cite primary/authoritative sources in `SOURCES.md`. Use “estimated conditional response” for historical fits, “consistent with” for process-model comparison, and reserve “caused by precipitation” for a model-defined counterfactual—not a Shapley attribution.
