# Next missing sector: heat-driven road and rail infrastructure

## Selection

After removing the active agriculture, labor, fisheries, wildfire-carbon, and
air-pollution tracks, heat-driven road and rail infrastructure is the fastest
defensible next sector. The RFF/GIVE inventory identifies it as an omitted
category with potentially material damages, and—unlike larger but currently
blocked biodiversity or ecosystem-service candidates—it has a public,
licensed, executable response surface in EPA FrEDI v4.1.1.

This selection is about implementation readiness, not a claim that transport
is globally larger than every omitted category. The result will be a **CONUS
partial SCC**, never a global estimate or a U.S.-to-world extrapolation.

## Published target now verified

The target contract pins FrEDI release commit
`08ead1b64821acd0ff0ee95fdf662a1a73f242e1` and FrEDI_Data commit
`b506a3e0085bb446f56acc8c7076a1aea599fbb6`. The full 13.55 MB official runtime
object and the official temperature-conversion source are hash-bound under
ignored `data/raw/` storage.

The runtime audit verifies:

- 9,114 road/rail response rows, 49 state/DC units, six GCM surfaces, and
  three adaptation variants;
- annual scalar support through 2300 for road miles, rail miles, Reactive road
  adjustment, and rail growth;
- EPA's official global-to-CONUS warming multiplier of 1.421;
- `Reactive` as the primary, aggregate-includable variant for both Roads and
  Rail; and
- each aggregate enters once. Roads bundles repair and road-user costs; Rail
  bundles replacement and delay costs. The public release does not support
  invented component shares.

## Accounting boundary

Only temperature-driven Roads and Rail are admitted. Coastal properties,
high-tide flooding, inland flooding, urban drainage, building energy, labor
heat productivity, mortality, agriculture, wildfire, and air pollution are
excluded. Transport delay/user costs remain inside the two published bundles;
they are not relabeled as labor-productivity damages.

## Gates and completed partial-SCC calculation

The response target is ready. A deterministic
matched GIVE baseline/pulse temperature and consumption path for a 2025 CO2
pulse has now been built and independently validated for 1750–2300. It has
exact pre-pulse identity, a positive post-pulse temperature response, an exact
1995 reference zero, the official 1.421 conversion, and a pulse-year Ramsey
discount factor of one. Annual Reactive road and rail damages have now been
evaluated only through 2092, the last year within the 3°C common support of all
six surfaces. The BEA/FRED 2015-to-2020 USD conversion and exact pulse
normalization are pinned and independently validated. The resulting truncated
CONUS partial SCC is $0.21448/tCO2 (six-surface range $0.10021–$0.41146).
Global extrapolation and cross-sector addition remain closed.

Reproduce the current target audit:

```sh
python3 scripts/acquire_pinned_fredi_sources.py
python3 scripts/audit_fredi_transport_matched_pulse_target.py \
  --output provenance/fredi_transport_matched_pulse_target_audit_20261017.json
python3 scripts/validate_give_transport_temperature_pair.py \
  --output provenance/fredi_transport_give_temperature_pair_validation_20261017.json
python3 -m unittest tests/test_fredi_transport_matched_pulse_target.py
```
