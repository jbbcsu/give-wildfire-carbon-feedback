# FrEDI transport-heat interface audit

This isolated project pins public EPA FrEDI v4.1.1 surfaces for temperature-driven transport and electricity-infrastructure responses. It now reports a validated, truncated **CONUS partial SCC** for the released Roads and Rail aggregates. It does not extrapolate outside CONUS, use flood/coastal/wildfire sectors, infer unavailable components, or authorize addition to other GIVE sectors before overlap reconciliation.

## Current result

The deterministic aggregate-interface smoke test passes for 49 geographic units (48 contiguous states plus DC), six GCM response surfaces, three adaptation variants, and the two public aggregate sectors `Roads` and `Rail`. The public v4.1.1 runtime and input tables do not expose separate response rows for road repair, road user costs, rail replacement, or rail delay. Those four component gates remain closed.

The electricity audit separately admits only `ElecTD`, the released combined transmission/distribution infrastructure sector. It excludes `ElecSD`: EPA documents that surface as combining heating/cooling-driven power demand with required generation-capacity expansion, while the runtime exposes no component split. The electricity sentinel passes for 49 state/DC units, six GCMs, and three adaptation variants (18 rows). Generation/capacity, building demand, transmission-only, and distribution-only gates remain closed.

The audit uses:

- FrEDI tag `v4.1.1`, commit `08ead1b64821acd0ff0ee95fdf662a1a73f242e1`;
- FrEDI_Data commit `b506a3e0085bb446f56acc8c7076a1aea599fbb6`;
- only state-level GCM response tables and the associated road/rail scalars;
- a 1.5°C CONUS anomaly relative to 1995 and the exact 2020 scalar values as a deterministic interpolation sentinel.

All copied upstream material is under `data/raw/` and ignored by Git. Exact sizes, SHA-256 hashes, Git blob IDs, official URLs, versions, and licenses are in `provenance/fredi_source_manifest_v4_1_1.json`.

## Reproduce

From this directory:

```bash
python3 scripts/acquire_pinned_fredi_sources.py
python3 scripts/run_fredi_transport_heat_smoke.py
python3 scripts/validate_fredi_transport_heat_smoke.py
python3 scripts/run_fredi_electricity_td_heat_sentinel.py
python3 scripts/validate_fredi_electricity_td_heat_sentinel.py
python3 -m unittest discover -s tests -v
```

The acquisition command verifies local files by default and performs no network access. Reacquisition requires the explicit `--download-missing` flag and uses commit-pinned official EPA GitHub URLs.

See `docs/FREDI_TRANSPORT_HEAT_GATE.md` and `docs/FREDI_ELECTRICITY_HEAT_GATE.md` for source audits, units, endpoint blockers, and fail-closed routes to matched GIVE pulse runs. Both outputs are implementation sentinels, not policy scenarios or SCC estimates.

## Matched-pulse transport track

Heat-driven road and rail infrastructure is now the selected next uncovered
sector. The exact public runtime target, primary Reactive variant, official
1.421 global-to-CONUS temperature conversion, six GCM surfaces, 49 state/DC
units, and annual scalar support through 2300 are validated and hash-bound.
See `TRANSPORT_SECTOR_SELECTION_AND_TARGET_20261017.md`. The matched GIVE
temperature pair now passes.

## Validated Roads + Rail partial SCC

The matched-pulse pipeline now passes all within-sector gates. The primary
`Reactive` mean is **$0.21448/tCO2 in 2020 USD**, with a six-surface range of
$0.10021–$0.41146/tCO2. This is a CONUS-only result truncated at 2092, the last
year in which the baseline and pulse temperatures stay inside the 0–3°C common
support of all six released GCM-pattern surfaces. See
`results/FREDI_TRANSPORT_CONUS_PARTIAL_SCC_V1.md` for interpretation and claim
limits.

Reproduce after acquiring the pinned raw inputs:

```bash
python3 scripts/acquire_pinned_fredi_sources.py --download-missing
python3 scripts/acquire_fred_gdpdef_price_source.py --download-missing
python3 scripts/run_fredi_transport_conus_partial_scc.py
python3 scripts/validate_fredi_transport_conus_partial_scc.py
python3 -m unittest tests/test_fredi_transport_conus_partial_scc.py -v
```
