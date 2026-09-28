# Hultgren–MIRCA rice-season weight crosswalk audit

Date: 2026-09-28

## Decision

The preserved artifacts permit an exact, non-imputed **Rice1 sensitivity crosswalk on restricted support**. They do not permit a defensible complete season-separated production crosswalk.

Three independent blockers remain:

1. corresponding Rice1 weight support is incomplete for both preserved Hultgren branches;
2. MIRCA Rice2 weights exist, but there are no preserved Hultgren `ri2_noirr` or `ri2_firr` weather-basis branches to receive them; and
3. the unrepaired MIRCA Rice1–Rice3 layers still fail the annual-rice reconciliation. The available repaired weights are explicitly a proportional-reconciliation sensitivity, not reproduced publisher data.

No nearest-neighbor matching, opposite-irrigation substitution, Rice3 transfer, country-average filling, unmatched-cell filling, or matched-support renormalization is used.

## Exact Rice1 support

The India-corrected Hultgren preflight preserves 10,104 distinct half-degree cells and 272,808 cell-years in each of `ri1_noirr` and `ri1_firr`. The two branch calendars are identical on these cells. Exact latitude/longitude matching to the MIRCA Rice1 candidate gives:

| Hultgren branch | Corresponding MIRCA weight | Cells with positive weight | Cell coverage | Missing cells | Matched cell-years | Global Rice1 area on Hultgren support |
|---|---|---:|---:|---:|---:|---:|
| `ri1_noirr` | Rainfed | 8,575 | 84.87% | 1,529 | 231,525 | 40.68% repaired; 40.68% unrepaired |
| `ri1_firr` | Irrigated | 6,017 | 59.55% | 4,087 | 162,459 | 43.24% repaired; 43.24% unrepaired |

For both branches, 10,089 of 10,104 coordinates have some Rice1 candidate row. The larger missing-weight counts are therefore primarily genuine zero support in the corresponding irrigation system, not coordinate mismatch.

Across the common preserved cell set:

- 4,503 cells have both positive rainfed and irrigated Rice1 weights;
- 4,072 have only a positive rainfed weight;
- 1,514 have only a positive irrigated weight; and
- 15 have neither Rice1 weight.

The repaired Rice1 area on preserved support is 16.092 million rainfed hectares and 26.316 million irrigated hectares. The independently reconstructed unrepaired values are 16.092 million and 26.329 million hectares. The small repaired/unrepaired difference does not cure the much larger calendar-support restriction.

## Rice2 blocker

The MIRCA candidate contains 8,836 Rice2 rows, including 7,143 positive rainfed-weight cells and 4,561 positive irrigated-weight cells. Their repaired areas total 23.713 million rainfed hectares and 34.061 million irrigated hectares.

However, the preserved Hultgren weather artifacts contain only `ri1_noirr` and `ri1_firr`. The number of preserved Hultgren Rice2 branches is zero. Attaching Rice2 weights to a Rice1 calendar or copying the Rice1 weather basis would be an unsupported season substitution, so the audit fails closed.

## Claim gates

- Exact Rice1 candidate-sensitivity crosswalk available: true.
- No imputation or substitution used: true.
- Complete Rice1 branch weight coverage: false.
- Preserved Hultgren Rice2 weather basis available: false.
- Unrepaired MIRCA source reconciliation passed: false.
- Production season weights, response fitting, published-response evaluation, damages, and SCC use: false.

The builder peaked at 230,129,664 bytes RSS and the independent validator at 188,891,136 bytes, both below 512 MiB. The validator independently reconstructs the exact Hultgren cell set, the MIRCA joins, and unrepaired areas from the repair scales.

## Artifacts

- Contract: `config/hultgren_mirca_rice_season_weight_crosswalk_audit_v1.toml`
- Builder: `scripts/audit_hultgren_mirca_rice_season_weight_crosswalk.py`
- Tests: `scripts/test_audit_hultgren_mirca_rice_season_weight_crosswalk.py`
- Validator: `scripts/validate_hultgren_mirca_rice_season_weight_crosswalk.py`
- Receipt: `data/provenance/hultgren_mirca_rice_season_weight_crosswalk_audit_20260928.json`
- Validation: `data/provenance/hultgren_mirca_rice_season_weight_crosswalk_validation_20260928.json`
- Compact audit table: `data/interim/hultgren_mirca_rice_season_weight_crosswalk_audit_20260928.parquet`

## Next gate

A complete crosswalk requires a separately validated Hultgren-compatible Rice2 weather basis and either a frozen restricted-support estimand for Rice1 or a publisher-consistent season map covering the missing corresponding weights. The unrepaired-versus-proportional-repair sensitivity must remain explicit. None of those source steps authorizes response fitting, valuation, damages, or a GIVE SCC.
