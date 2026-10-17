# Inland riverine-flood property damages for GIVE

This isolated project adds a reproducible **CONUS partial SCC benchmark** for
climate-driven riverine-flood property damage. It does not modify or depend at
runtime on the precipitation, wildfire, roads/rail, coastal, or fisheries projects.

## Result

Using the published FrEDI v4.1.1 response, the matched GIVE 2025 CO2 pulse and
2% Ramsey discounting produces **$0.01425 per tCO2 (2020 USD)** through 2300.
The result through 2092, where CONUS warming remains within 0--3 C, is $0.00906;
the result through 2246, entirely within FrEDI's released 0--5 C response knots,
is $0.01380. The 2300 result uses FrEDI's endpoint linear extrapolation after 2246.

This is not a global SCC estimate. FrEDI releases only a GCM-ensemble response,
so the calculation does not invent a confidence interval. State results show
spatial heterogeneity, not statistical uncertainty.

## Reproduce

Requirements are Python 3.11+ and standard-library modules only.

```sh
python3 scripts/acquire_sources.py
python3 scripts/run_inland_flood_scc.py
python3 scripts/validate_outputs.py
python3 -m unittest discover -s tests -v
```

Inputs are hash-pinned. Raw archives and binary runtime objects are ignored.
See `docs/LITERATURE_AND_OVERLAP_AUDIT.md` for endpoint boundaries and the global
interface contract, and `provenance/source_manifest_v1.json` for exact sources.

