# Rice2 second-season parent crosswalk — 2026-09-28

## Result

The frozen Sri Lanka/Vietnam parent-descendant gate was executed and independently validated. It yields **zero authorized Rice2 cells** and therefore zero authorized 1982–2019 cell-years in either `ri2_noirr` or `ri2_firr`.

No coefficient, moderator-weighted response, MIRCA weight, yield effect, damage, SCC, or GIVE input was evaluated.

## Parent and geometry recovery

The published estimation sample contains 56 second-season UIDs: 25 in Sri Lanka and 31 in Vietnam. Exact normalized matching against every pinned author hierarchy node gives:

- 43 unique parent matches: 18 Sri Lanka and 25 Vietnam;
- 10 unmatched UIDs; and
- 3 UIDs with two candidate hierarchy nodes.

Only the 43 unique matches were expanded. They contain 147 terminal descendants—38 in Sri Lanka and 109 in Vietnam. Every descendant has pinned polygon geometry, and no terminal descendant is assigned to more than one selected UID.

## Frozen attrition

Starting from 6,197 strict Rice2 cells per branch:

| Gate | Global | Sri Lanka | Vietnam |
|---|---:|---:|---:|
| Intersects any Sri Lanka/Vietnam terminal polygon | 156 | — | — |
| Intersects any of the 43 mapped second-season UIDs | 79 | — | — |
| Exactly one mapped second-season UID | 27 | 2 | 25 |
| Exact author/GGCMI calendar before the spatial gate | 0 | 0 | 0 |
| Exactly one UID and no competing terminal intersection | 11 | — | — |
| Full-cell ownership at `1 - 1e-6` tolerance | 0 | 0 | 0 |
| Full ownership plus exact calendar; authorized | **0** | **0** | **0** |

Among the 11 one-UID/no-competitor cells, mapped polygon coverage ranges from 0.00160564 to 0.999995653 of the cell, with median 0.305687. The maximum remains below the frozen 0.999999 full-cell threshold.

The calendar gate is independently decisive:

- all 18 uniquely mapped Sri Lankan author UIDs use planting month 5, harvest month 8, and four months total; the two one-UID GGCMI Rice2 cells use 10–2 and five months;
- all 25 uniquely mapped Vietnamese author UIDs use 5–9 and five months; the 25 one-UID GGCMI cells instead use 11–3/5 months, 12–4/5, 12–5/6, 4–7/4, 6–10/5, or 6–9/4.

Thus even the closest spatial case—99.9995653% mapped coverage—cannot pass because its GGCMI calendar is 6–10/5 while the author UID calendar is 5–9/5. Relaxing the frozen spatial tolerance would not create a calendar-concordant row.

## Interpretation

The ordinal name `Rice2` is not source evidence that GGCMI Rice2 represents the prepared panel's `second` reporting series. In the only countries where the estimation panel exposes a second season, the author and GGCMI Rice2 calendars do not agree on any uniquely assigned cell.

The response gate must remain closed. The next defensible action is not coefficient evaluation. It requires an authoritative season-product crosswalk or a new preregistered audit asking which GGCMI rice season, if any, matches each author reporting series. Substituting the nearest calendar, accepting partial cells, or treating `total` as Rice2 would change the application domain.

## Validation and resources

The independent validator rebuilt the 43 parent mappings, 147 descendant ownership assignments, country geometries, all 6,197 cell intersections, spatial fractions, and calendar checks from pinned sources. Every ledger field matched, and maximum absolute overlap-fraction error was zero.

- Builder peak RSS: 366,051,328 bytes
- Validator peak RSS: 291,553,280 bytes
- Ceiling: 536,870,912 bytes

## Hash-bound artifacts

- Contract: `config/hultgren_rice2_second_season_parent_crosswalk_v1.toml` — `1bfab20478ac996a1e05d0de1fe1516b81d92e88d97b46a6d1fca22134d7fae0`
- Builder: `scripts/build_hultgren_rice2_second_season_parent_crosswalk.py` — `e91f8e01a65a0a01111a1f9d83de15218b99d8448aeadda0adeefd88597ada03`
- Cell ledger: `data/interim/hultgren_rice2_second_season_parent_crosswalk_20260928.parquet` — `f6bed0618e66df47f1439bc62edd57b654700520e1b3600d22f0466b45cd29d1`
- Build receipt: `data/provenance/hultgren_rice2_second_season_parent_crosswalk_20260928.json` — `aad1894cdca770257facbb46c8da1fa4519f094918c5a0e09c58f1af5026eff7`
- Validator: `scripts/validate_hultgren_rice2_second_season_parent_crosswalk.py` — `ce31581d60297dd10f1ec54f64b0eb0c307d2176a976332bc4099f5d98984179`
- Validation receipt: `data/provenance/hultgren_rice2_second_season_parent_crosswalk_validation_20260928.json` — `e7f872208e6ae5bd15d01f0e1a96c0d856cb12bd233cbc02d25b1075b7db8425`

All response and downstream claim gates remain closed.
