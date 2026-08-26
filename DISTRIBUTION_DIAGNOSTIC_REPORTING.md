# Precipitation-distribution diagnostic reporting

`scripts/render_precipitation_distribution_table.py` converts one or more
already validated distribution-diagnostic summaries into a compact Markdown
table. It never fits a model and never reads or emits coefficients.

The renderer fails closed unless every input has the exact validated status
and diagnostic contract, all noncausal/nonproduction/non-SCC boundary flags,
declared coefficient suppression, the current specification hash, a supplied
lock's exact file hash, and the source-panel hash registered for that crop in
the matching lock. It also checks the complete model/holdout product and
reconciles every reported incremental RMSE used in the table. This is a report
gate over validator-produced summaries; it does not replace the upstream
locked-source recomputation performed by
`scripts/validate_precipitation_distribution_diagnostic.py`.

From the project root, reproduce the table for both diagnostic periods with:

```bash
./.venv/bin/python scripts/render_precipitation_distribution_table.py \
  outputs/irrigation_basis/maize_mirca2000_1982_1989_distribution_diagnostic_v1_summary.json \
  outputs/irrigation_basis/soy_mirca2000_1982_1989_distribution_diagnostic_v1_summary.json \
  outputs/irrigation_basis/maize_mirca2000_2012_2016_distribution_diagnostic_v1_summary.json \
  outputs/irrigation_basis/soy_mirca2000_2012_2016_distribution_diagnostic_v1_summary.json \
  --out outputs/irrigation_basis/precipitation_distribution_diagnostic_table.md
```

By default, the renderer discovers the versioned diagnostic locks in
`config/`. For a separate reproducible bundle, pass its specification and each
allowed lock explicitly:

```bash
./.venv/bin/python scripts/render_precipitation_distribution_table.py \
  VALIDATED_summary.json \
  --spec DIAGNOSTIC_SPEC.toml \
  --lock PERIOD_A.lock.toml \
  --lock PERIOD_B.lock.toml
```

The reported extension is the lowest-RMSE `quantity_plus_*` candidate, not the
lowest-RMSE model overall. Thus the table retains a negative improvement when
every distribution extension performs worse than the parsimonious seasonal-
quantity model. The results remain descriptive held-out predictive evidence:
they are not causal effects, production-model selection, damages, or SCC
inputs.

Run the synthetic fail-closed tests with:

```bash
./.venv/bin/python scripts/test_render_precipitation_distribution_table.py
```
