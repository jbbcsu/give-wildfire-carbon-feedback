# Municipal water-supply damage feasibility

This directory contains a source-pinned, fail-closed screen of published routes
to municipal drought/water-supply damages for GIVE. Inland riverine flooding is
included only as a comparator.

No damage function or SCC is estimated here. The current screen admits no
candidate because no released package simultaneously provides a defensible
municipal-only welfare boundary, annual matched baseline/pulse paths, complete
geographic mapping, uncertainty, and resolved reuse terms.

## Files

- `FAST_ROUTE_AUDIT_20261014.md`: human-readable findings, overlap boundary,
  and exact artifact request.
- `config/fast_route_screen_v1.json`: machine-readable candidate gate matrix.
- `data/provenance/source_receipts_20261014.json`: pinned primary-source
  receipts and repository/release identifiers.
- `python/validate_fast_route_screen.py`: fail-closed audit validator.
- `test/test_validate_fast_route_screen.py`: focused synthetic mutation tests.

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
