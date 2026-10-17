# Finished GIVE labor integration

Status date: 17 October 2026.

## Integrated result

The labor sector is integrated at the expected-value level in the exact
published Moore et al. updated-agriculture GIVE target. Each structural case is
a same-run 10,000-draw execution: the target total and all partial-sector means
come from the same receipt and sum within $10^{-9}$/tCO2.

| Structural case | Target without labor | Labor addition | Target with labor |
|---|---:|---:|---:|
| Lancet | 138.4121 | 29.2638 | 167.6759 |
| ISO | 138.7756 | 51.8647 | 190.6403 |
| Equal-weight structural mean | **138.5939** | **40.5643** | **179.1581** |

All values are 2020 USD/tCO2 for a 2025 CO2 pulse, RFF-SP socioeconomic paths,
and the paper's 2% Ramsey schedule. The original GIVE checkout contains no
labor-productivity component, while the target source graph adds labor once and
connects it separately to the damage aggregator. The additive labor
contribution is therefore validated for this target configuration.

## Uncertainty

The full within-case uncertainty is already present in the same target runs:
the Lancet target has a 5th–95th percentile range of 70.1464–310.7451 and the
ISO target 76.3476–364.9383. Labor-only within-case ranges are
0.1875–70.7842 and 1.0421–133.8827, respectively. These are separate
structural specifications. No pooled interval, pooled standard error, or
no-labor interval is inferred from summary statistics.

## Boundary

This closes labor integration, not precipitation-agriculture integration. The
target includes Moore et al.'s updated total-agriculture sector. The
precipitation module cannot be stacked wholesale; only a separately identified
residual or replacement can enter later. Cross-sector behavioral adaptation
interactions between labor, energy, and mortality remain a model limitation,
not an accounting duplication in the implemented component graph.

## Reproduce

```sh
python3 -m unittest test/test_labor_give_integration.py
python3 scripts/build_labor_give_integration.py \
  --output data/provenance/labor_give_integration_20261017.json
```

The contract hash-binds the source graph and both 10,000-draw receipts. It
fails closed on sector overlap, invariant mismatch, non-additivity, uncertainty
pooling, or precipitation stacking.
