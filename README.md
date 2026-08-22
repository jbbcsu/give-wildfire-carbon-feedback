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
The evidence-bounded manuscript and Methods/SI blueprints are in
[MANUSCRIPT_OUTLINE.md](MANUSCRIPT_OUTLINE.md) and
[METHODS_SI_OUTLINE.md](METHODS_SI_OUTLINE.md).
The executable crop-specific array, coverage, adaptation, and replacement
boundary is documented in
[SCC_INTEGRATION_DESIGN.md](SCC_INTEGRATION_DESIGN.md). It contains no fitted
coefficients or SCC estimates.

The empirical climate pipeline is deliberately staged: daily ISIMIP inputs are
converted to calendar-defined crop-year features, independently reconciled
against stage partitions, then joined to GDHY yields before any pilot response
diagnostic. Stage-resolved daily-maximum heat features now use the same
partition boundaries, require explicit temperature thresholds, and must
reconcile additive heat days and degree-days to the season. The stage fractions
are temporal proxies rather than asserted crop phenology. See the scripts
directory and [RESULTS_STATUS.md](RESULTS_STATUS.md) for the current evidence
boundary.

Before any empirical response array can approach GIVE wiring,
`scripts/validate_scc_response_bundle.py` enforces the frozen crop/FUND order,
full crop-value coverage, matched baseline/pulse identifiers, one declared
water-stress family, fixed-within-draw weights, finite coefficients, and
pre-divergence conservation. Passing this schema gate is not evidence of
held-out skill or authorization to calculate an SCC.

The approved calendar-to-yield season crosswalk is recorded in
[data/provenance/crop_calendar_gdhy_crosswalk.md](data/provenance/crop_calendar_gdhy_crosswalk.md).
It deliberately does not use GDHY convenience aggregate directories where a
season-specific outcome exists.

[METHODS_BENCHMARK_QIU_2025.md](METHODS_BENCHMARK_QIU_2025.md) records the
adapted ensemble/validation design benchmark used for the next specification.
The high-resolution US validation track is isolated in
[us_county_validation/README.md](us_county_validation/README.md).
