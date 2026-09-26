# MIRCA rice-season proportional-reconciliation sensitivity results

## Result

A transparent within-cell proportional reconciliation is numerically feasible
for the metadata-valid year-2000 MIRCA-OS v2 rice layers. No cell with positive
annual broad-rice area lacks season-specific support, and no season-positive
cell lacks annual support. Scaling Rice1--Rice3 together within each cell and
irrigation system therefore preserves their source shares and reconciles to
the official annual totals to floating-point precision.

The original global excess is 64,247 ha for irrigated rice (0.0632% of the
official 101.565 million ha) and 5,302 ha for rainfed rice (0.00828% of 64.017
million ha). The correction is highly localized:

| System | Annual area receiving >0.1% correction | >1% | >5% | >10% | Minimum scale |
|---|---:|---:|---:|---:|---:|
| Irrigated | 4.171% | 1.968% | 0.210% | 0% | 0.91085 |
| Rainfed | 0.314% | 0.0719% | 0.0438% | 0.00838% | 0.64236 |

For irrigated rice, the repair changes global Rice1, Rice2, and Rice3 area by
-36,316, -27,822, and -109 ha. For rainfed rice, the corresponding changes are
-5,302, +0.088, and +0.003 ha. The candidate table contains 30,903 Rice1/Rice2
crop cells, retains Rice3 only in the reconciliation audit, and explicitly sets
`production_eligible=false` and `scc_authorized=false`.

## Interpretation

This result shows that the failed exact source gate is driven by a small,
localized inconsistency that can be exposed and bounded. It does **not** prove
which MIRCA layer is correct, reproduce publisher data without repair, or
authorize rice response or SCC calculations. The unrepaired source remains the
primary record. The repaired weights are a sensitivity candidate only.

Before use, Rice1/Rice2 must pass a calendar/spatial crosswalk to the locked
GDHY/ISIMIP outcomes. The rice response also still needs season-separated
moderators, future/pulse weather, valuation, and a result sensitivity comparing
unrepaired-season totals, proportionally reconciled totals, and any publisher
correction that becomes available.

## Reproducibility

- Protocol: `MIRCA_RICE_PROPORTIONAL_RECONCILIATION_PROTOCOL_20260926.md`
- Builder: `scripts/audit_mirca_rice_proportional_reconciliation.py`
- Unit invariants: `scripts/test_audit_mirca_rice_proportional_reconciliation.py`
- Compact validator: `scripts/validate_mirca_rice_proportional_reconciliation.py`
- Receipt: `data/provenance/mirca_rice_proportional_reconciliation_sensitivity_20260926.json`
- Validation: `data/provenance/mirca_rice_proportional_reconciliation_validation_20260926.json`
- Candidate table: ignored
  `data/interim/mirca_os_v2/rice_season_proportional_reconciliation_candidate_2000.parquet`
