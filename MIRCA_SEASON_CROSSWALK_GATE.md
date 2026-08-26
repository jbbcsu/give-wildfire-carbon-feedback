# MIRCA-OS season crosswalk gate

## Current decision

The publisher's 0.5° annual MIRCA-OS maps are admissible fixed irrigation
weights for the one-season maize and soybean outcomes. They are not admissible
for GDHY's two rice seasons or spring/winter wheat outcomes.

| GDHY outcome | Annual MIRCA class | Current status | Next defensible route |
|---|---|---|---|
| `mai` | Maize | Eligible | Use the fixed-vintage annual share. |
| `soy` | Soybeans | Eligible | Use the fixed-vintage annual share. |
| `ri1`, `ri2` | Rice | Blocked | Validate the 5′ monthly `Rice1`, `Rice2`, and `Rice3` products, aggregate season-specific hectares to 0.5°, and reconcile their sum to annual Rice. |
| `swh`, `wwh` | Wheat | Blocked | Obtain an explicit spring/winter harvested-area source or a publisher-supported mapping; do not infer it from `Wheat1`/`Wheat2`. |

This gate is fail-closed in the weight builder and allocator. It is not a
claim that the blocked crops are unimportant.

## Primary-source evidence

The [MIRCA-OS v2 HydroShare record](https://www.hydroshare.org/resource/e4582ca0042148338bb5e0148b749ed6/)
states that annual harvested area for a multiply cropped class is the sum of
the maximum monthly areas of its subcrops. Annual filenames contain crop,
year, and irrigation system, but no subcrop. The same README documents the
5′ monthly growing-area filename convention with a numeric crop-season label
and gives `Rice1` as the first rice season. The
[Scientific Data paper](https://doi.org/10.1038/s41597-024-04313-w) defines
one broad Wheat class covering multiple wheat types; numeric MIRCA subcrops
represent multiple cropping, not a documented spring/winter cultivar split.

The checksum-pinned 2000 irrigated and rainfed calendar CSVs were inspected
without using yield outcomes. They contain `Rice1`, `Rice2`, and `Rice3`, and
`Wheat1` and `Wheat2`. Their administrative-unit growing-area totals are:

| System | Rice1 | Rice2 | Rice3 | Wheat1 | Wheat2 |
|---|---:|---:|---:|---:|---:|
| Irrigated | 60,620,956 | 35,484,341 | 6,697,983 | 66,205,226 | 474,936 |
| Rainfed | 39,758,693 | 23,713,101 | 748,788 | 119,105,965 | 19,600,481 |

These are source-table hectares, not new agricultural-effect estimates.
`Rice3` is material enough that it cannot be silently folded into either GDHY
rice outcome. The wheat labels alone do not establish spring/winter identity,
even when planting months appear suggestive.

The ignored discovery files are pinned here so the totals are reproducible:

| File | Bytes | Data rows | SHA-512 |
|---|---:|---:|---|
| `MIRCA-OS_2000_ir_v2.csv` | 9,264,277 | 129,661 | `76af4b0c55012e693ce2926c249c65cb7d1efe7e1484fb298751ceb3d0bfd284e196a36a63038febe248faf3c05a60e3b90e5b21649bc396dd3567914765c836` |
| `MIRCA-OS_2000_rf_v2.csv` | 9,295,446 | 129,530 | `9d0beb530f39f751918dfa2193625b0361e6aa4a3a0940bf551379e0fbc401031b366453a3952bde831a8c8b920e64f9876b5901e330f66db5358ea81181a558` |

They require Latin-1 decoding. They support the outcome-blind label and total
audit only; they are not gridded irrigation weights. A 1,537,240,142-byte
local transfer named `Monthly_Growing_Area_Grids_v2.rar` also exists in ignored
storage (local SHA-512
`b01ca694d47967024bc8544037a381a6f267503dfeb12ea0b89dcc1ed23b35bdb8b8ce1cd5af014169f5616c12a2facc960ae8f8b0209bdc4adf6d768cb56a7c`).
Its official object identity, inventory, extraction, and grid contents have
not passed the protocol below, so it is not yet a validated rice input.

## Rice validation protocol

1. Pin the official monthly archive byte length, source object identity,
   locally computed SHA-512, license, and exact inventory. Keep it ignored.
2. Require explicit `Rice1`, `Rice2`, and `Rice3` files for both irrigation
   systems and every selected fixed vintage; reject missing or duplicate files.
3. Validate WGS84 grid coordinates, 5′ resolution, nonnegative finite hectares,
   month order, units, and zero/nodata semantics.
4. For each subcrop/system/grid cell, recover annual harvested area using the
   publisher's documented maximum-over-month rule. Sum 5′ hectares into exact
   0.5° cells; never average area.
5. Require the aggregated sum of Rice1--Rice3 to reconcile to the released
   annual 0.5° Rice map within a predeclared numerical tolerance.
6. Compare Rice1/Rice2 calendar timing and spatial support with the locked
   GGCMI/GDHY `ri1`/`ri2` crosswalk. Disclose Rice3 and all ambiguous cells;
   do not renormalize them into the two observed outcomes.
7. Only after these checks may separate fixed Rice1/Rice2 irrigation shares be
   marked production-eligible. Each vintage remains a sensitivity held fixed
   across outcome years, not a time-varying adaptation series.

No analogous MIRCA-only route is currently defensible for spring versus
winter wheat. That input gap remains open rather than being filled from timing
heuristics.
