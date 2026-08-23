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
damages must replace, not be added to, the current temperature-only MooreAg
sector.

See [PLAN.md](PLAN.md) for the phased protocol, [SOURCES.md](SOURCES.md) for
authoritative inputs, and [src/PrecipitationDamages.jl](src/PrecipitationDamages.jl)
for the isolated Mimi component contract.  The literature-first recommendation
and ML contingency are in [AGRICULTURE_RESEARCH.md](AGRICULTURE_RESEARCH.md).
The climate-emulation literature and published-method reuse decision are in
[CLIMATE_PRECIPITATION_EMULATOR_AUDIT.md](CLIMATE_PRECIPITATION_EMULATOR_AUDIT.md).
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
through its panel join. It does not substitute observed CRU scPDSI for a
matched future drought path. See the scripts directory and
[RESULTS_STATUS.md](RESULTS_STATUS.md) for the current evidence boundary.

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
declared sector-inclusion flags, and reconnects `damage_ag` once. The
build-only integration test in `scripts/test_give_replacement_harness.jl`
passes against the unmodified GIVE model with synthetic zero-response inputs.
Mimi requires those externally supplied arrays on the full GIVE model time
dimension, including years before the components' 2020 start. This is a
topology/build result, not a successful marginal run or damage result.

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
`scripts/validate_response_evaluation_audit.py` then fails unless the audit
matches the exact configuration hash and contains the complete explicitly
declared crop/model/holdout product with reconciled folds, benchmarks, metrics,
and row counts. Its descriptive ranking is not a model-selection rule.

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
  --summary-out outputs/response_evaluation_summary.json
```

The approved calendar-to-yield season crosswalk is recorded in
[data/provenance/crop_calendar_gdhy_crosswalk.md](data/provenance/crop_calendar_gdhy_crosswalk.md).
It deliberately does not use GDHY convenience aggregate directories where a
season-specific outcome exists.

GDHY does not provide separate rainfed and irrigated yield outcomes. The
production path must therefore never duplicate one observed yield into two
regime-specific estimation rows. `scripts/allocate_outcome_exposures.py`
implements the admissible alternative: after both calendar exposures exist,
an independently sourced, fixed-baseline crop-area-share table collapses them
to exactly one area-weighted exposure row per crop-grid-year outcome. It fails
on missing regimes, inconsistent yields, time-varying or non-independent
weights, incomplete shares, nonfinite features, and duplicate keys. The
synthetic test exercises these gates; no production area source or irrigated
response is yet claimed.

[METHODS_BENCHMARK_QIU_2025.md](METHODS_BENCHMARK_QIU_2025.md) records the
adapted ensemble/validation design benchmark used for the next specification.
The high-resolution US validation track is isolated in
[us_county_validation/README.md](us_county_validation/README.md).
