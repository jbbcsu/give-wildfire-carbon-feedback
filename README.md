# Global infrastructure SCC feasibility

This directory records a bounded, primary-source screen of global road/rail
heat and electricity-supply/grid climate-damage models that might eventually
complement the CONUS-only FrEDI infrastructure module.

The screen is fail-closed: no candidate currently supplies all of global
coverage, annual monetized damage paths, uncertainty, a documented climate
response, an open/pinned implementation, and matched marginal-pulse inputs.
No FrEDI extrapolation, damage function, or SCC is produced here.

Files:

- `FAST_ROUTE_AUDIT_20261014.md`: findings, accounting boundaries, and exact
  artifact requests.
- `config/candidate_screen_v1.json`: machine-readable evidence and gate matrix.
- `python/validate_candidate_screen.py`: structural and fail-closed validator.
- `test/test_validate_candidate_screen.py`: focused mutation tests.

Validation:

```bash
python3 python/validate_candidate_screen.py config/candidate_screen_v1.json
python3 -m unittest discover -s test -v
```

Passing validation means only that the negative feasibility record is
internally consistent. It does not authorize an estimate.
