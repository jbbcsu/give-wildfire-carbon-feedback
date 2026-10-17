# Grid transmission/distribution direct-cost benchmark

This isolated project evaluates climate-driven U.S. electricity transmission and distribution (T&D) infrastructure costs omitted from GIVE's existing energy-expenditure module. It uses the published Fant et al. (2020) surfaces released in EPA FrEDI v4.1.1 and the validated GIVE 2025 matched temperature pulse.

The benchmark includes direct repair/replacement costs for combined T&D assets under NoAdapt, Proactive, and Reactive adaptation. It excludes building energy demand, generation capacity, outage/reliability welfare, mortality, labor, and indirect production effects.

The output is **not authorized for addition to GIVE** because the released aggregate includes several climate stressors, including wildfire and coastal flooding, and endpoint overlap must first be reconciled with other modules. It must not be described as an outage SCC.

```bash
python3 scripts/run_grid_td_benchmark.py
python3 scripts/validate_outputs.py
python3 -m unittest discover -s tests -v
```

See `docs/COVERAGE_AND_OVERLAP_AUDIT.md` for interpretation and the additivity gate.

The open EPA inputs can be reacquired with `python3 scripts/acquire_open_sources.py`. The validated GIVE matched pair and GDP deflator are hash-pinned in `provenance/source_manifest_v1.json`.
