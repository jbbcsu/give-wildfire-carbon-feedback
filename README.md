# GIVE precipitation and hydrologic-damages extension

This directory is a standalone research/implementation track for adding the
marginal damages of CO2-induced precipitation change to GIVE's social cost of
carbon (SCC).  It does not modify or import any wildfire/biomass-burning work.
The files here are specifications and an unintegrated component interface;
they are intentionally not wired into the baseline model.

## Current boundary

The first build prioritizes **global agricultural damages from precipitation
patterns**—seasonality, timing, dry spells, wet-day frequency, and extremes—in
a joint temperature--precipitation response. Coastal storm-surge and
sea-level-rise costs remain the responsibility of CIAM. Inland flood/built
infrastructure is a secondary, separately accounted track. Agricultural
damages must replace, not be added to, the current temperature-indexed MooreAg
sector, which has no explicit separable precipitation input in this checkout.

See [PLAN.md](PLAN.md) for the phased protocol, [SOURCES.md](SOURCES.md) for
authoritative inputs, and [src/PrecipitationDamages.jl](src/PrecipitationDamages.jl)
for the isolated Mimi component contract.  The literature-first recommendation
and ML contingency are in [AGRICULTURE_RESEARCH.md](AGRICULTURE_RESEARCH.md).
The climate-emulation literature and published-method reuse decision are in
[CLIMATE_PRECIPITATION_EMULATOR_AUDIT.md](CLIMATE_PRECIPITATION_EMULATOR_AUDIT.md).
The primary matched baseline/pulse route and its acquisition/validation gates
are fixed in [PAIRED_CLIMATE_FEATURE_DRIVER.md](PAIRED_CLIMATE_FEATURE_DRIVER.md):
derive the exact crop features from version-pinned daily ISIMIP3b fields, fit
ESM-specific feature responses to same-realization GMST, and evaluate matched
FAIR paths with common random numbers. Scenario differences are training data,
not one-tonne CO2 experiments.
The outcome-blind selection is now frozen to the five complete ISIMIP3b ESM
realizations across historical, SSP1-2.6, SSP3-7.0, SSP5-8.5 and the four daily
variables (80 version-`20210512` datasets). Bounded complete-file `pr`/`tas`
coverage now includes historical plus all three SSPs for all five frozen ESM
realizations. Every available file is API-identity/version/checksum bound and
passes decoded global-grid, units, exact daily chronology, missingness, and
physical-value gates. Same-realization annual GMST and two-latitude
maize/rainfed feature cells pass for every bounded scenario. MRI's newly closed
SSP1-2.6 and SSP5-8.5 block adds four complete files (4,953,940,488 bytes) and
its exact historical/four-scenario product passes 44 whole-scenario engineering
folds; the simple GMST adjustment improves 24 folds, with median RMSE ratio
0.99971 and worst ratio 1.09903, so it is not promoted. The UKESM expansion
adds six complete files (6,680,992,736 bytes), exact historical/future
boundaries, same-realization GMST, and exact-reconciliation feature cells. Its
four-scenario diagnostic improves 23/44 folds (median RMSE ratio 0.99985;
worst 1.03248). The exact five-ESM joint product has 565,950 rows. Whole-ESM
folds improve 41/55 (median 0.99760; worst 1.05145) and whole-scenario folds
improve 36/44 (median 0.99744; worst 1.01605). It remains an engineering gate
and is not promoted. These
are seven-year, one-crop/two-latitude engineering smokes, not acquisition of
the 1.757 TB matrix or a production feature response. A separate
area-unweighted aggregate numerical smoke produces 880 common-residual
baseline/pulse rows across all 55 ESM-feature fits. Zero-pulse and
pre-divergence identity, separate support flags, direct/centered agreement, and
three decreasing positive pulse scales pass; 19 pulse rows are above and 10
below bounded training support. These artificial Kelvin perturbations are not
FAIR paths. Actual FAIR pairing, spatial support, and production convergence
remain open.
The evidence-bounded manuscript and Methods/SI blueprints are in
[MANUSCRIPT_OUTLINE.md](MANUSCRIPT_OUTLINE.md) and
[METHODS_SI_OUTLINE.md](METHODS_SI_OUTLINE.md).
All claims and results are governed by
[SCIENTIFIC_INTEGRITY_PROTOCOL.md](SCIENTIFIC_INTEGRITY_PROTOCOL.md); an
independent replication and adversarial-review path is provided in
[INDEPENDENT_REVIEW_CHECKLIST.md](INDEPENDENT_REVIEW_CHECKLIST.md).
The executable crop-specific array, coverage, adaptation, and replacement
boundary is documented in
[SCC_INTEGRATION_DESIGN.md](SCC_INTEGRATION_DESIGN.md). It contains no fitted
coefficients or SCC estimates.

The empirical climate pipeline is deliberately staged: daily ISIMIP inputs are
converted to calendar-defined crop-year features, independently reconciled
against stage partitions, then joined to GDHY yields before any pilot response
diagnostic. Stage-resolved daily-maximum heat features now use the same
partition boundaries, require explicit temperature thresholds, and must
reconcile additive heat days and degree-days to the season. Seasonal and stage
validators also enforce the necessary nesting of day counts and degree-day
totals across ordered thresholds. The stage fractions
are temporal proxies rather than asserted crop phenology. A parallel historical
drought-benchmark path day-weights monthly CRU scPDSI over those same windows,
requires exact 0.5-degree grid correspondence and complete monthly coverage,
and preserves an explicit `historical_benchmark_not_future_scc_input` role
through regime-first allocation. The global 1982--1989 and 2012--2016 maize
and soybean candidate panels now pass raw-source/calendar manifest binding and
complete derived-input allocation recomputation; they remain unfitted and
contain no direct-weather terms. It does not substitute observed CRU scPDSI
for a matched future drought path. See the scripts directory and
[RESULTS_STATUS.md](RESULTS_STATUS.md) for the current evidence boundary.
The resumable `scripts/run_historical_crop_chunk.sh` command executes the
seasonal and stage extraction, completeness checks, independent
reconciliation, GDHY join, and precipitation-pattern construction for one
crop, irrigation calendar, and historical time block. All generated products
remain below the ignored `data/interim/` boundary.
Daily precipitation, mean-temperature, and maximum-temperature builders accept
chronologically ordered file lists. They reject coordinate or unit changes,
duplicate or missing boundary dates, and non-daily steps before crop-season extraction;
they then read only the calendar years that can enter the requested harvest
years. This permits cross-year seasons to span version-pinned decadal files
without silent edge loss and is also required for historical/future ISIMIP3b
blocks in the matched-feature driver.

Before any empirical response array can approach GIVE wiring,
`scripts/validate_scc_response_bundle.py` enforces the frozen crop/FUND order,
full crop-value coverage, matched baseline/pulse identifiers, one declared
water-stress family, fixed-within-draw weights, finite coefficients, and
pre-divergence conservation. Passing this schema gate is not evidence of
held-out skill or authorization to calculate an SCC.

After wiring, `src/AgricultureReplacementAudit.jl` inspects Mimi's component
graph and fails unless `DamageAggregator.damage_ag` has exactly one internal
producer, `JointAgriculture.agcost`, and no component named `Agriculture`
remains instantiated. Synthetic missing-source, wrong-source, and coexistence
cases are tested. The unmodified GIVE baseline is a deliberate negative
control: it is rejected because `Agriculture.agcost` still supplies
`damage_ag`. A graph pass establishes the replacement topology only; it does
not clear empirical, welfare, coverage, support, paired-run, or SCC gates.

`src/AgricultureReplacementHarness.jl` now performs that replacement on a
MimiGIVE-style model: it deletes the legacy component and its MooreAg-only
parameters, installs the crop response and joint agriculture components,
reuses the existing regional socioeconomic aggregators, preserves the
declared sector-inclusion flags, and reconnects `damage_ag` once. The executed
integration control in `scripts/test_give_replacement_harness.jl` passes
against the unmodified GIVE model with synthetic zero-response inputs: every
active-year crop and regional response output is complete, coverage is one,
and both `JointAgriculture.agcost` and GIVE's aggregated agriculture damage are
zero. Mimi requires externally supplied arrays on the full GIVE model time
dimension, including years before the components' 2020 start. This is a
synthetic execution/connectivity result, not a paired marginal run, empirical
damage estimate, or SCC result.

That control was executed with the archived GIVE runtime (Julia 1.6.4
x86_64 under Rosetta). The archived dependency lock does not currently run
natively on Apple silicon because its Electron artifact is unavailable for
`aarch64-apple-darwin`; `REPOSITORY.md` records the exact reproducible command.

`src/PairedAgricultureAudit.jl` checks the next component boundary after the
response and replacement components run: matched dimensions, finite values,
pre-divergence conservation, and an all-years zero-pulse identity control. It
remains an output-contract gate rather than a full GIVE marginal run or SCC.

The pre-integration validation layer now also includes
`scripts/evaluate_crop_response_models.py`, driven by the frozen
`config/response_evaluation_spec.toml`. It evaluates crop-specific
first-difference predictions across outcome-blind spatial, temporal, and
climate-extreme holdouts and intentionally emits no coefficients. Its output
is diagnostic and cannot be used as an SCC response bundle.
That diagnostic comparison is deliberately smaller than the production estimand:
it omits wet-day frequency, conditional wet-day intensity, Rx5day, heat, and
the two alternative drought families, and represents normalized stage
timing/distribution only indirectly through stage totals. The response audits
reported before the purged-split revision used temporal and extreme
first-difference pairs that could share a level-yield endpoint across training
and test. Those values are legacy dependent stress tests and become stale when
the hashed diagnostic specification changes; they are not production outer
holdouts. The revised evaluator and audit validator now enforce zero endpoint
overlap and pass synthetic tests. Corrected 1982--1989 MIRCA-2000 maize and
soybean minimal diagnostics pass under the new hash; other historical panels
remain stale or pending. The complete not-yet-frozen registry and the required
purged-split promotion gate are documented in
[RESPONSE_SPECIFICATION_BOUNDARY.md](RESPONSE_SPECIFICATION_BOUNDARY.md).
`scripts/validate_response_evaluation_audit.py` then fails unless the audit
matches the exact configuration hash and contains the complete explicitly
declared crop/model/holdout product with reconciled folds, benchmarks, metrics,
and row counts. When an expected year range is declared, it also requires the
exact contiguous harvest-year list. Its descriptive ranking is not a
model-selection rule.

Run the independent scope boundary before any response work:

```bash
./.venv/bin/python scripts/validate_response_spec_boundaries.py
```

This check confirms omissions and non-authorization; it does not freeze or fit
a production model.

For a panel that already contains stage features, create the outcome-blind
labels and run the audit with:

```bash
./.venv/bin/python scripts/make_validation_folds.py \
  --panel data/interim/STAGE_PANEL.parquet \
  --out data/interim/STAGE_VALIDATION_PANEL.parquet
./.venv/bin/python scripts/evaluate_crop_response_models.py \
  --panel data/interim/STAGE_VALIDATION_PANEL.parquet \
  --out outputs/response_evaluation.json
./.venv/bin/python scripts/validate_response_evaluation_audit.py \
  --audit outputs/response_evaluation.json \
  --expected-crop mai --expected-crop ri1 --expected-crop ri2 \
  --expected-crop soy --expected-crop swh --expected-crop wwh \
  --expected-year-start 1982 --expected-year-end 1989 \
  --summary-out outputs/response_evaluation_summary.json
```

The approved calendar-to-yield season crosswalk is recorded in
[data/provenance/crop_calendar_gdhy_crosswalk.md](data/provenance/crop_calendar_gdhy_crosswalk.md).
It deliberately does not use GDHY convenience aggregate directories where a
season-specific outcome exists.
The aligned GDHY method can clip a negative aligned yield to zero. The join
preserves that source zero in `gdhy_yield_raw_t_ha` and flags it with
`yield_nonpositive`, but marks it unobserved for the log-yield response; it
never silently adds an arbitrary positive offset.

GDHY does not provide separate rainfed and irrigated yield outcomes. The
production path must therefore never duplicate one observed yield into two
regime-specific estimation rows. `scripts/allocate_outcome_exposures.py`
enforces the one-outcome and independent-share contract. For a nonlinear
response, every regime-specific transform, extreme, drought index, spline,
threshold, and interaction must be built before the fixed shares are applied;
averaging primitive weather and transforming it afterward is invalid.
`scripts/allocate_irrigation_response_basis.py` implements this order for the
minimal predictive diagnostic. Its output is accepted only by the evaluator's
explicit contract-aware prebuilt-basis mode, which consumes supplied basis
columns without rebuilding them. The complete production basis and causal
estimator remain to be frozen. The allocator fails
on missing regimes, inconsistent yields, time-varying or non-independent
weights, incomplete shares, nonfinite features, and duplicate keys. The
synthetic test exercises these gates. MIRCA-OS v2 is now acquired and
checksum/grid validated as that independent area source.
`scripts/build_mirca_irrigation_shares.py` constructs fixed 2000 shares and
the registered 2005--2020 vintage sensitivities on the common 0.5° grid.
Maize and soybean mappings are exact; annual rice and wheat weights carry
`production_eligible=false` because they cannot identify the two rice seasons
or spring/winter wheat, and the allocator now rejects them. The source closes
a weighting-input gate but does not supply an irrigated yield outcome,
response coefficient, damage, or SCC.
`scripts/allocate_irrigation_distribution_basis.py` extends the same ordering
to a 54-column direct-pattern candidate contract: seasonal and three-window
amounts, normalized shares/timing/concentration, wet-day occurrence and
conditional intensity, CDD, Rx1day, Rx5day, mean temperature, and registered
temperature-by-log-amount terms. The current 1 mm wet-day definition remains
a recorded candidate/QA definition, not a selected production threshold. The
script validates stage/season reconciliation and emits `fit_authorized=false`;
heat and alternative drought-family features remain separate open gates.
`scripts/allocate_irrigation_scpdsi_basis.py` implements the separate
historical climatic-water-balance candidate: it builds seasonal/stage scPDSI
means, minima, monthly-index threshold day-equivalents, and fractions within each irrigation
calendar before fixed-area weighting, removes only complete outcome keys when
coverage is missing, and emits no direct precipitation or temperature terms.
`scripts/validate_irrigation_scpdsi_basis.py` hash-checks the raw-source and
calendar manifest chain and fully recomputes the candidate from its derived
stage tables. It does not label that derived-input check as full raw-metric
recomputation. `scripts/run_scpdsi_candidate_chunk.sh` composes the complete
partition-to-validation route; it performs no response fit and authorizes no
future, causal, damage, or SCC use.
`scripts/build_direct_scpdsi_common_support.py` then constructs four data-only
common-support bundles while keeping the 54-feature direct-weather and
16-feature scPDSI views separate. Common rows/observed outcomes and direct-only
dropped rows/observed outcomes are: maize 1982--1989,
240,784/115,758 and 24,744/1,921; soybean 1982--1989,
176,537/47,653 and 14,935/269; maize 2012--2016,
150,490/59,772 and 15,465/1,046; and soybean 2012--2016,
110,336/26,601 and 9,334/147. scPDSI-only drops are 0/0 in every bundle.
`scripts/validate_direct_scpdsi_common_support.py` verifies hashes and exactly
recomputes both views and the intersection from the immediate candidate
tables. It does not rerun upstream raw sources or bind upstream validation
receipts; running those validators and retaining their receipts is an external
prerequisite. These bundles fit no model and report no coefficient, causal
effect, model selection, future projection, damage, or SCC result. Seasonal
quantity remains the direct-weather reference, distribution terms require
robust stable outer-holdout value, and drought families remain mutually
exclusive competitors rather than stacked controls. See
[DIRECT_SCPDSI_COMMON_SUPPORT_CONTRACT.md](DIRECT_SCPDSI_COMMON_SUPPORT_CONTRACT.md).
The matched comparison now also has a separate, validated heat-control basis
constructed within rainfed and fully irrigated calendars before fixed-share
aggregation. It uses crop-stage mean temperature plus daily-maximum
degree-days above 29 C for maize and 30 C for soybean; the parallel 30 C maize
basis is retained as a sensitivity. See
[HEAT_CONTROL_BASIS_CONTRACT.md](HEAT_CONTROL_BASIS_CONTRACT.md) and
[HEAT_THRESHOLD_EVIDENCE_NOTE.md](HEAT_THRESHOLD_EVIDENCE_NOTE.md).

The resulting coefficient-suppressing historical diagnostic contains 209,036
maize and soybean consecutive-year pairs. Across five unbuffered 5-degree
spatial folds, direct seasonal precipitation quantity has the lowest mean RMSE
for both crops and lowers RMSE in all ten crop-fold comparisons, but the gains
are below 1% and MAE rankings are less uniform. Richer scPDSI summaries add
stress-specific rather than stable general predictive value. All 110 aggregate
metrics pass exact recomputation and a separate clean-room refit. This is not a
causal response, production-model selection, climate-change projection,
damage estimate, or SCC input. Exact results, hashes, and limitations are in
[GLOBAL_DIRECT_SCPDSI_DIAGNOSTIC_RESULTS.md](GLOBAL_DIRECT_SCPDSI_DIAGNOSTIC_RESULTS.md);
the executable contract is documented in
[DIRECT_SCPDSI_PREDICTIVE_DIAGNOSTIC.md](DIRECT_SCPDSI_PREDICTIVE_DIAGNOSTIC.md).
The paired geographic loss sensitivity and its narrower uncertainty boundary
are documented in
[DIRECT_SCPDSI_PAIRED_LOSS_UNCERTAINTY.md](DIRECT_SCPDSI_PAIRED_LOSS_UNCERTAINTY.md).

The primary SPEI competitor is now literature- and source-locked without
reusing a later-period standardized field. It will compute separate SPEI-1,
SPEI-3, and SPEI-6 candidates from the already acquired nClimGrid-Daily and
ISIMIP3a GSWP3-W5E5 precipitation/temperature, using daily Hargreaves-Samani
reference ET, monthly water balance, and a grid-cell/calendar-month
three-parameter log-logistic unbiased-PWM fit over 1982--2011 frozen before
the 2012 terminal holdout. NOAA's published U.S. SPEI and SPEIbase 2.11 remain
retrospective implementation/PET checks because their calibration/source
boundaries do not match the terminal diagnostic. The contract and physical/
time primitives pass; full SPEI fields and crop/outcome models do not yet
exist. See [SPEI_COMPETITOR_DESIGN.md](SPEI_COMPETITOR_DESIGN.md).
`scripts/run_irrigation_basis_chunk.sh` composes these gates for one completed
maize or soybean period: it constructs the corrected minimal basis, assigns
fixed outcome-blind validation folds, runs and validates the coefficient-
suppressing predictive audit, then constructs and validates the broader
distribution candidate without fitting it. All products remain ignored and
explicitly ineligible for causal, damage, or SCC use.
`scripts/filter_complete_yield_support.py` creates a separate sample-
composition sensitivity for periods in which GDHY's finite spatial support
changes by year. It retains only cells observed in every declared year, imputes
nothing, and warns that complete-support conditioning can itself select a
nonrepresentative subset; it does not replace the unbalanced primary panel.
Cell-count support is not welfare support. The fail-closed audit in
`scripts/audit_mirca_welfare_support.py` shows that the current 1982--1989
response-pair cells cover 79.02% of positive MIRCA maize area and 89.29% of
soybean area, despite roughly 98% coverage when the denominator is only
GDHY-observed cells. A same-vintage MIRCA-area-times-GDHY-yield proxy is
undefined over the remaining 20.98%/10.71% of global MIRCA area, and no pinned
spatial crop-value input exists. [WELFARE_SUPPORT_AUDIT.md](WELFARE_SUPPORT_AUDIT.md)
therefore blocks interpreting the current sample as global production/value
coverage or normalizing it to global welfare.
The aggregate observation equation, identification restrictions, distinction
between area, production, and revenue weights, and required sensitivities are
recorded in [IRRIGATION_AGGREGATE_ESTIMAND.md](IRRIGATION_AGGREGATE_ESTIMAND.md).
Legacy maize/soybean all-area response outputs constructed nonlinear terms
after primitive-weather weighting are withdrawn; only their source/support
audits remain valid.
The season-specific evidence and executable 5′ rice validation gate are
recorded in [MIRCA_SEASON_CROSSWALK_GATE.md](MIRCA_SEASON_CROSSWALK_GATE.md).
The real 2000 Rice1--Rice3 reconstruction does not reconcile to the annual
Rice maps, so the builder records a failure audit and emits no production
weights. Wheat remains blocked without an explicit spring/winter area source.

Reproduce the candidate rice source gates with the following commands. The
inventory command is expected to exit nonzero because nine publisher files
carry inconsistent year metadata; the 2000 builder is also expected to exit
nonzero after writing its annual-reconciliation audit. Neither emits rice
weights.

```bash
./.venv/bin/python scripts/download_mirca_rice_seasons.py
./.venv/bin/python scripts/audit_mirca_rice_inventory.py
./.venv/bin/python scripts/build_mirca_rice_season_shares.py \
  --monthly-root data/raw/mirca_os_v2/monthly_rice \
  --annual-root data/raw/mirca_os_v2/extracted_30arcmin --year 2000 \
  --out data/interim/mirca_os_v2/rice_season_irrigation_shares_2000.parquet \
  --audit-out data/interim/mirca_os_v2/rice_season_irrigation_shares_2000_audit.json
```

Rebuild the ignored source and fixed-2000 table with:

```bash
./.venv/bin/python scripts/download_mirca_os_v2.py
./.venv/bin/python scripts/build_mirca_irrigation_shares.py \
  --input-root data/raw/mirca_os_v2/extracted_30arcmin --year 2000 \
  --out data/interim/mirca_os_v2/irrigation_shares_2000.parquet \
  --audit-out data/interim/mirca_os_v2/irrigation_shares_2000_audit.json
```

[METHODS_BENCHMARK_QIU_2025.md](METHODS_BENCHMARK_QIU_2025.md) records the
adapted ensemble/validation design benchmark used for the next specification.
The high-resolution US validation track is isolated in
[us_county_validation/README.md](us_county_validation/README.md).
