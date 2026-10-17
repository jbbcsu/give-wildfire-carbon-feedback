# Municipal water-supply damage feasibility

This directory contains a source-pinned, fail-closed screen of published routes
to municipal drought/water-supply damages for GIVE. Inland riverine flooding is
included only as a comparator.

The original transfer screen admits no municipal-only candidate because no
released package simultaneously provides a defensible municipal welfare
boundary, annual matched baseline/pulse paths, complete geographic mapping,
uncertainty, and resolved reuse terms. A follow-on executable benchmark now
reproduces MimiFUND's **aggregate** water-resources marginal value. It is not
relabeled municipal and is not additive to GIVE.

## Files

- `FAST_ROUTE_AUDIT_20261014.md`: human-readable findings, overlap boundary,
  and exact artifact request.
- `config/fast_route_screen_v1.json`: machine-readable candidate gate matrix.
- `data/provenance/source_receipts_20261014.json`: pinned primary-source
  receipts and repository/release identifiers.
- `python/validate_fast_route_screen.py`: fail-closed audit validator.
- `test/test_validate_fast_route_screen.py`: focused synthetic mutation tests.
- `MIMIFUND_AGGREGATE_WATER_BENCHMARK_20261017.md`: reproduced global
  aggregate-water benchmark, regional heterogeneity, and claim limits.
- `scripts/compute_mimifund_aggregate_water_benchmark.jl`: pinned marginal-run
  implementation with one-year and official ten-year pulse sensitivities.
- `python/validate_mimifund_aggregate_water_benchmark.py`: independent output,
  price-year, pulse-sensitivity, reconciliation, and fail-closed validation.

## Validation

```bash
python3 python/validate_fast_route_screen.py \
  config/fast_route_screen_v1.json \
  data/provenance/source_receipts_20261014.json
python3 -m unittest discover -s test -v
```

The validator checks evidence bindings, the seven transfer gates, a strict
municipal-only overlap boundary, and the rule that a candidate is not marked
GIVE-ready unless every gate passes. Passing the validator means the negative
screen is internally consistent; it does **not** authorize estimation.

The follow-on central aggregate-water benchmark is $2.283770/tCO2 in 2020 USD
under a 2025 one-year pulse and constant 2% discounting. It remains an external
sensitivity benchmark because municipal isolation, hydrology, uncertainty,
and cross-sector overlap gates are closed.
