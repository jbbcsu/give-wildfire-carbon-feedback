# Heat, education, and human-capital formation: GIVE integration audit

This isolated project asks whether published evidence on heat-related learning losses can support a marginal social cost of CO2 (SCC) endpoint in GIVE.

## Status

**Blocked; no SCC estimate is produced.** GIVE's published damage modules do not contain a distinct education endpoint, and causal evidence links school-day heat to lower test scores. However, the available evidence does not supply a defensible, globally transferable welfare valuation and matched baseline-versus-pulse climate calculation. Converting test-score changes to lifetime earnings would require an unvalidated causal bridge and would overlap labor-productivity and top-down macroeconomic damages. This repository therefore fails closed.

## What is executable

```bash
python3 scripts/finalize_contract.py
python3 scripts/validate_contract.py
python3 -m unittest discover -s tests
```

These commands create and validate a machine-readable readiness receipt. They intentionally create no SCC result.

## Scope boundaries

- Candidate endpoint: learning or attendance changes attributable to heat exposure on school days.
- Excluded valuation: lifetime earnings, aggregate GDP/growth, teacher productivity, mortality, health morbidity, and household or economy-wide cooling demand.
- Adaptation: school air conditioning is evidence-supported as a moderator, but its capital and electricity costs are not yet globally measured or cleanly separated from GIVE energy damages.
- Integration rule: the module remains non-additive until a separable welfare measure, matched marginal climate exposure, global transfer protocol, and overlap audit all pass.

See `docs/LITERATURE_AND_INTEGRATION_AUDIT.md` for the evidence and exact unlock requirements.
