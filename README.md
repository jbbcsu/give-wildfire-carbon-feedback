# Winter recreation revenue benchmark for GIVE

This isolated project evaluates an omitted GIVE sector: U.S. winter recreation. It links the published Wobus et al. (2017) / EPA FrEDI response surfaces for alpine skiing, cross-country skiing, and snowmobiling to the validated GIVE 2025 CO2 matched-temperature pair.

The numeric result is a **marginal lost ticket/entry-revenue benchmark, not an additive welfare SCC**. The source study monetizes access prices. It does not estimate consumer surplus, producer profit, expenditure substitution, or national incidence. The code therefore fails closed on addition to GIVE.

Run with only the Python standard library:

```bash
python3 scripts/run_winter_recreation_benchmark.py
python3 scripts/validate_outputs.py
python3 -m unittest discover -s tests -v
```

Inputs are source-pinned and hash-checked. Raw archives are ignored. Outputs report each of six GCMs and both a response-support-oriented 2092 horizon and the official FrEDI-style extended 2300 horizon. See `docs/LITERATURE_AND_OVERLAP_AUDIT.md` for interpretation and exclusions.

To reacquire the open response artifact and reproduce the population extraction from an exact FrEDI v4.1.1 checkout:

```bash
python3 scripts/acquire_sources.py --fredi-sysdata /path/to/FrEDI/R/sysdata.rda
```

The validated GIVE temperature pair is a project input rather than an upstream download; its hash and lineage are recorded in `provenance/source_manifest_v1.json`.
