# Climate conflict and crime damages for GIVE

This isolated project separates two distinct questions:

1. Organized armed conflict: no defensible additive SCC is currently available.
2. Temperature-related U.S. crime: EPA FrEDI provides a published executable
   benchmark, reproduced here under a matched GIVE marginal pulse.

The crime benchmark is **$0.01927/tCO2** through 2300 and **$0.01291/tCO2**
through 2092 (2020 USD, six-GCM mean, 2% Ramsey). It is not yet additive because
the released valuations cannot remove possible overlap with mortality, labor,
health, enforcement, indirect costs, and transfers. It is CONUS-only and must not
be called an armed-conflict or global SCC.

Reproduce with Python 3 standard-library modules:

```sh
python3 scripts/acquire_sources.py
python3 scripts/run_crime_benchmark.py
python3 scripts/validate_outputs.py
python3 -m unittest discover -s tests -v
```

All sources are revision- and hash-pinned. Raw archives are ignored.

