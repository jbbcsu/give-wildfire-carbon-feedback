# Anchored marginal-response replacement sentinel

## Outcome

A paired GIVE replacement sentinel now passes for the ACCESS-CM2 smallest-
pulse, fixed-adaptation, uncapped, central national-market path. The benchmark
retains MooreAg's baseline regional agriculture damage *level* but deletes the
legacy Agriculture component and replaces its marginal pulse response with the
external maize precipitation-quantity path. This preserves baseline
consumption while avoiding stacking the new marginal response on MooreAg's
marginal response.

The replacement graph has exactly one producer for
`DamageAggregator.damage_ag`, the new `AnchoredAnnualMoney.agcost`; the legacy
`Agriculture` component is absent. All non-agriculture pulse responses remain
in the paired GIVE model.

## Validation

- Baseline agriculture damage maximum error: exactly $0.
- Baseline global net consumption per capita maximum error: exactly 0.
- Maximum regional increment round-trip error:
  `4.51e-13` billion 2005 USD.
- Maximum annual global aggregation error from adding a roughly dollar-scale
  increment to billion-dollar baseline levels and subtracting it: $0.00551.
- Maximum paired-replacement versus external discount-diagnostic difference:
  `4.08e-9` 2005 USD per tCO2.
- All four SCC differences are below error bounds derived from the observed
  annual aggregation error and the exact Ramsey weights.

The paired ACCESS-CM2 values in 2005 USD per tCO2 are -0.00826142,
-0.00570903, -0.00425054, and -0.00335929 under GIVE's 1.5%, 2.0%, 2.5%, and
3.0% Ramsey schedules. These agree with the independently built external
diagnostic to eight or more decimal places.

The successful paired job peaked at 1.63 GB sampled process-group RSS under a
3 GB ceiling. Earlier executions failed closed on bitwise-equality assertions
that were too strict for adding tiny increments to large level paths; the final
test uses a calculated numerical error bound rather than an outcome-based
tolerance.

## Interpretation and remaining gate

This establishes the accounting and software route for a defensible
**marginal-response replacement**: retain the existing baseline level so the
baseline economy is unchanged, remove the overlapping legacy pulse response,
and insert the precipitation response exactly once. It validates one pinned
sentinel, not the full 26-model ensemble and not a full agricultural damage
replacement. The external ensemble diagnostic remains the current numerical
result until the paired route is batch-executed and uncertainty draws are
added.

## Reproducible artifacts

- Regional sentinel exporter:
  `scripts/export_quantity_replacement_sentinel.py`
- Replacement component:
  `src/AnchoredAnnualAgriculture.jl`
- Paired GIVE runner:
  `scripts/run_quantity_anchored_replacement_sentinel.jl`
- Registrar/audit:
  `scripts/register_quantity_anchored_replacement_sentinel.py`
- Receipts:
  `data/provenance/quantity_replacement_sentinel_access_cm2_20260924.json`,
  `data/provenance/quantity_anchored_replacement_sentinel_job_20260924.json`,
  and
  `data/provenance/quantity_anchored_replacement_sentinel_20260924.json`
- Ignored derived inputs/results:
  `data/interim/quantity_replacement_sentinel_access_cm2_20260924.csv` and
  `data/interim/quantity_anchored_replacement_sentinel_results_20260924.csv`
