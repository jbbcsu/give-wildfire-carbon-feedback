# Cross-sector adaptation-cost accounting

This isolated audit prevents adaptation benefits from being treated as free and prevents costs already embedded in published sector totals from being charged twice.

Key finding: the current precipitation-agriculture `trend` and `upper` cases reduce the climate response while `adaptation_cost_share` returns zero. They are gross residual-damage sensitivities, not net SCC estimates. By contrast, the underlying FrEDI Roads, Rail, and electricity transmission/distribution studies include implementation, repair, delay, or capital costs in their scenario totals. GIVE's CIAM coastal component also includes protection, retreat, maintenance, relocation, and residual-damage costs in its optimized total. Those totals must not receive a second adaptation-cost add-on.

Run:

```bash
python3 adaptation_costs/scripts/build_ledger.py
python3 -m unittest discover -s adaptation_costs/tests -v
```

The builder emits a machine-readable readiness summary and a bounded external agriculture-cost benchmark. It never fills missing sector costs or produces a net SCC.
