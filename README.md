# Climate migration and displacement audit for GIVE

This isolated project evaluates whether climate-driven migration outside coastal
CIAM can be added to GIVE. Its defensible result is **not a numerical SCC**:
no screened source provides a marginal-pulse, sector-separable welfare endpoint
that avoids double counting existing or planned damage sectors.

The audit verifies that coastal relocation costs already enter CIAM's optimal
sea-level-rise costs. It then screens the open global structural models of Cruz
and Rossi-Hansberg and Burzynski et al., the World Bank Groundswell projections,
and reduced-form migration evidence. The structural models are useful non-additive
sensitivities; migration-count projections are not monetary damage functions.

Run the standard-library-only audit and tests:

```sh
python3 scripts/audit_migration_readiness.py
python3 -m unittest discover -s tests -v
```

The output status is `BLOCKED_NO_ADDITIVE_SCC`, not zero damages. See the
literature audit and implementation contract for the exact route to reopening
the gate.

