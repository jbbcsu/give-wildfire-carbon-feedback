# Paired Moore labor/agriculture module preflight

Status date: 14 October 2026.

## Result

The pinned Moore et al. source contains a source-faithful paired integration
path. It starts from `MimiGIVE.get_model`, deletes the legacy agriculture
component and its eight supporting aggregators/disaggregators, replaces the
damage aggregator, then adds `AgricultureShare`, `Labor`, and the updated
`Agriculture` component in that order. Agriculture and labor enter the damage
aggregator through separate connections. The Monte Carlo definition deletes
all 48 legacy agriculture random variables (three coefficients by sixteen FUND
regions), adds labor GCM uncertainty, and adds seven updated-agriculture
coefficients per country.

The hash-bound preflight preserves two independent structural cases:
`labor_damage_function="Lancet"` and `labor_damage_function="ISO"`. Each case
is bound to its own author input and reproduced 10,000-draw receipt. No
cross-case quantile, interval, or pooled distribution is constructed.

## Accounting boundary

- Updated agriculture is replacement-only. It may not be added to legacy GIVE
  agriculture.
- Labor is an addition in the published implementation and remains a separate
  partial sector.
- The precipitation-agriculture diagnostic cannot be stacked with updated
  total agriculture. No moisture-channel allocation is made here.
- The verified source graph supports a future two-case execution; it does not
  by itself establish a target-model run, a converged legacy-to-updated
  agriculture delta, or a combined GIVE SCC.

## Reproduce the bounded preflight

```sh
/usr/bin/time -l python3 test/test_paired_module_preflight.py
/usr/bin/time -l python3 scripts/validate_paired_module_preflight.py
```

The validator reads only source text, small metadata, seven ignored runtime
inputs (hash/size only), and two JSON receipts. It does not load the 10,000-draw
arrays, import Julia, build a model, or calculate damages/SCCs.

## Next gate

Use the contract to run two separate target executions, one Lancet and one ISO,
under the frozen 2025-pulse/RFF-SP/seed/draw contract. Retain each case's
trial-level outputs separately and verify that the target graph contains one
updated agriculture component and one labor component, with no legacy
agriculture component. That execution requires a worker authorized above the
observed 2.36 GiB legacy-branch memory requirement; it is not eligible under a
512 MiB cap. Do not form a replacement-delta interval without a justified
joint coupling, and do not select a precipitation overlap allocation as part
of this gate.
