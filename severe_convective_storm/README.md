# Severe convective storm / hail property benchmark

This isolated project audits whether non-agricultural severe-convective-storm property damages can be added to GIVE. GIVE contains no hail-specific property-damage component. The closest published, executable climate-to-damage evidence is a bounded Swiss building-hail benchmark from Schmid, Gebhart, and Bresch (2026).

The benchmark is **not an SCC estimate**. It records a constant-exposure comparison between 2011–2021 present-day weather and a pseudo-global-warming simulation at +3 °C relative to preindustrial: annual average Swiss building losses rise from CHF 74 million to CHF 90 million (published rounded change: 22%). The study does not provide the annual marginal temperature response, CO2-pulse response, socioeconomic path, or a fully specified currency price year required for GIVE integration.

Run with only Python's standard library:

```bash
python3 severe_convective_storm/scripts/build_benchmark.py
python3 -m unittest discover -s severe_convective_storm/tests -v
```

The builder fails closed: it writes a bounded benchmark and a readiness report, but refuses to emit USD, global, or per-tCO2 results.

See `docs/AUDIT_AND_DECISION.md` for the evidence review, overlap boundaries, and exact integration gates.
