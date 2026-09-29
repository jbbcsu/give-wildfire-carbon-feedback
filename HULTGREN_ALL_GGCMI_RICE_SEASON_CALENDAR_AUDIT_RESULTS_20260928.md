# All-resident GGCMI rice-season calendar audit (2026-09-28)

## Decision

No authoritative or preregistered exact-concordance path from the published Hultgren second-season observations to a resident GGCMI rice season exists in the current pinned data. Neither independent resident season product, `ri1` nor `ri2`, has one exact author-calendar match even before the stricter full-cell spatial-ownership gate. No calendar product is selected and no new weather build is authorized.

This is a diagnostic result, not evidence that a particular GGCMI season is “closest” to the author season. Nearest-product selection was forbidden before comparison and was not performed.

## Preregistered contract and inventory

The comparison was frozen in `config/hultgren_all_ggcmi_rice_season_calendar_audit_v1.toml` before match results were calculated (SHA-256 `0c26e16bd0d65d19886410a96b411039b88bb73324c365797f1702ba781ad7d8`). It required:

- finite planting and maturity days plus positive publisher season fraction;
- a source-derived inclusive season length of 3–12 months;
- exactly one selected author UID, no positive-area competing terminal polygon, and full 0.5-degree-cell ownership within `1e-6`;
- exact planting month, exact harvest month, and exact inclusive season length;
- symmetric reporting of all resident branches, with `firr`/`noirr` treated as branch checks rather than additional independent seasons;
- no nearest-season or distance-based fallback.

The only resident GGCMI Phase 3 rice calendar files are `ri1_noirr`, `ri1_firr`, `ri2_noirr`, and `ri2_firr`, all version 1.01. There is no resident `ri3_noirr` or `ri3_firr` file. MIRCA crop layers were not treated as a missing GGCMI `ri3` calendar.

Within each season product, the rainfed and irrigated branches have identical strict-support/calendar signatures. Their NetCDF bytes differ, so both branches were still audited and reported.

## Author-domain attrition

The source panel contains 56 second-season UIDs: 25 in Sri Lanka and 31 in Vietnam. Their exact author calendar tuples are uniformly `5-8-4` in Sri Lanka and `5-9-5` in Vietnam. The already frozen hierarchy procedure yields:

- 43 uniquely matched ADM1 parents: 18 in Sri Lanka and 25 in Vietnam;
- 10 UIDs with no hierarchy match and 3 with two possible parents;
- 147 pinned terminal descendants: 38 in Sri Lanka and 109 in Vietnam.

Only the 43 unambiguous parents enter spatial comparison. No unmatched or ambiguous UID was imputed.

## Exact results

| Branch | Strict support cells | Intersect LKA/VNM terminals | Any selected UID | Exactly one UID | Exact author calendar before full-cell gate | Full-cell owner | Authorized |
|---|---:|---:|---:|---:|---:|---:|---:|
| `ri1_noirr` | 67,384 | 209 | 111 | 46 | 0 | 0 | 0 |
| `ri1_firr` | 67,384 | 209 | 111 | 46 | 0 | 0 | 0 |
| `ri2_noirr` | 6,197 | 156 | 79 | 27 | 0 | 0 | 0 |
| `ri2_firr` | 6,197 | 156 | 79 | 27 | 0 | 0 | 0 |

Country details are identical across irrigation branches within a product:

- `ri1`: 6 exactly-one-UID cells in Sri Lanka, all `4-8-5`; 40 in Vietnam, with tuples `1-5-5`, `11-2-4`, `12-2-3`, `12-3-4`, `12-4-5`, `2-6-5`, `4-12-9`, `5-10-6`, or `7-11-5`. None equals its UID's author tuple.
- `ri2`: 2 exactly-one-UID cells in Sri Lanka, both `10-2-5`; 25 in Vietnam, with tuples `11-3-5`, `12-4-5`, `12-5-6`, `4-7-4`, `6-10-5`, or `6-9-4`. None equals its UID's author tuple.

The strongest one-UID/no-competitor coverage fraction is `0.9999956531941584`, which still fails the frozen full-cell tolerance. More importantly, calendar concordance is already zero before this spatial gate, so relaxing polygon tolerance would not create a match.

The ledger has 147,162 rows and SHA-256 `36395c5b8711c4011e9339c49f1984944a6d050be1b422a0e011ee6e0458e2b0`.

## Independent validation and resource bound

`scripts/validate_hultgren_all_ggcmi_rice_season_calendar_audit.py` independently re-read all four raw NetCDF calendars, re-derived month/length fields, rebuilt the 56-UID hierarchy mapping and 147-terminal ownership, reprojected polygons, and recomputed every spatial and calendar flag. It reproduced every branch count and every overlap fraction; the maximum absolute overlap-fraction error was `0.0`.

- builder peak RSS: 358,350,848 bytes;
- independent validator peak RSS: 407,486,464 bytes;
- cap: 536,870,912 bytes.

Validation receipt: `data/provenance/hultgren_all_ggcmi_rice_season_calendar_audit_validation_20260928.json` (SHA-256 `c938aa3285ad9bb4cf7cbc3aad1df7a4fc1d86b18e64c454ed5645fc4c748f2c`).

## Fail-closed interpretation

There is no author-supplied season-product crosswalk in the pinned inputs, and the preregistered exact comparison yields zero matches for both resident independent products. Therefore an authoritative path and a non-post-hoc unique-exact-product path are both absent. Weather construction, response evaluation, MIRCA weighting, yield effects, damages, SCC, and GIVE integration remain closed.

The only safe next gate is external source recovery: pin an author- or publisher-supplied artifact that explicitly maps the Hultgren `second` season to a GGCMI rice season/calendar (or provides the exact source calendar raster used by the authors), then validate it without choosing among `ri1`/`ri2` based on these observed failures.
