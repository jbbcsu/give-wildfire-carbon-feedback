# Rice2 historical multi-block weather basis — 2026-09-28

## Result

The unweighted, branch-separated Rice2 weather basis is complete and independently validated for every full harvest year supported by the resident daily weather: **1982–2019 (38 years)**. This is a weather-basis result only. No MIRCA area or production weights, response coefficients, yield effects, damages, or SCC calculations were attached or evaluated.

Each of `ri2_noirr` and `ri2_firr` contains **235,486 rows**: 6,197 strict-support native cells in each of 38 harvest years. The two branches remain separate even though the resident publisher calendar arrays, and therefore their weather rows apart from the branch label, are exactly equal.

Strict support remains: finite Rice2 planting and maturity calendar values plus positive publisher `fraction_of_harvested_area`, with no calendar fill, Rice1 substitution, or use of publisher fractions as weights.

## Coverage and boundaries

- Resident daily inputs form a continuous **1981-01-01 through 2019-12-31** record: 14,244 daily steps in four source blocks.
- Internal source-block boundary harvest years **1991, 2001, and 2011 are included**. Their cross-year seasons use the preceding block's prior-year months rather than being truncated.
- **1981 is excluded as a whole harvest year.** A complete common-support 1981 panel cannot be formed because 1,616 cross-year cells require unavailable 1980 daily weather. No partial-year or changing-support 1981 panel was emitted.
- Per branch, 61,408 rows are cross-year seasons (1,616 per harvest year).
- Per branch, 174,230 rows have 3–5-month seasons. Both third-phase precipitation terms are exact structural zeros for every one of these rows.
- Per-year calendar-length counts are 14 three-month, 1,174 four-month, 3,397 five-month, 851 six-month, 445 seven-month, and 316 eight-month cells.

## Independent validation

The validator checked exact hashes, complete/unique/finite output rows, all 38 per-year support panels, prohibited economic/output columns, four-block daily continuity, branch equality apart from labels, structural zeros, and unchanged legacy Rice1 support.

Sixteen raw-daily sentinels were independently reaggregated: both branches for cross-year harvests 1982, 1991, 2001, 2011, and 2019, plus representative same-year 3-, 4-, and 5-month 2019 seasons. The maximum absolute difference across all weather primitives was **2.2737367544323206e-13**, versus the prespecified **1e-7** tolerance. Cross-year sentinels explicitly contained harvest-year-minus-one source dates.

The preserved legacy Rice1 support remains exactly **10,104 native cells** under its prior broad annual-MIRCA Boolean-mask rule and 6–12-month season rule.

Memory remained below the 512 MiB ceiling:

- `ri2_noirr` build peak RSS: **256,786,432 bytes** (244.89 MiB)
- `ri2_firr` build peak RSS: **261,079,040 bytes** (248.98 MiB)
- independent validator peak RSS: **485,179,392 bytes** (462.70 MiB)

Focused tests passed:

- scalar 3–12-month Rice2 weather behavior and legacy Rice1 behavior
- explicit Rice2 branch support and structural-zero behavior
- inclusion of prior-block December for a 1991 cross-year season
- fail-closed behavior for a 1981 cross-year season when 1980 weather is absent

## Hash-bound artifacts

- Contract: `config/hultgren_rice2_historical_multiblock_v1.toml` — SHA-256 `27fb4d9f25ea0c6b5b8944b02d04ec84c9bcd98c934f33c94f07ce0c16662dd1`
- `ri2_noirr` basis — SHA-256 `b2d46d4e745ef7e000240c2c50ef2a7413d8a88a440df98d57f5f128ba21eb2f`
- `ri2_noirr` build receipt — SHA-256 `261a932bb8d8b6aec3c6bd501aec02efc58fa44da20b5d9301a7476c11b8f8df`
- `ri2_firr` basis — SHA-256 `95de0e92f2e0ed498d488e5a34ae5aee8daee1ce98685f92017dd1e05ed332b3`
- `ri2_firr` build receipt — SHA-256 `c91339c559566b5c00da9b369b159b78f191e6eb298b93ac6d8a85c6eb0c05d2`
- Independent validator — SHA-256 `71a689d39b74ad5a4dded25b1505f5f2530962eb2302abcdb858f829c1c9238b`
- Validation receipt: `data/provenance/hultgren_rice2_historical_multiblock_validation_20260928.json` — SHA-256 `83b99a658b6e855887260e9dfcbfd56e2e7f4469ef4eb7fe2a39968786667369`

The contract pins the weather-source SHA-512 digests, calendars, branch outputs and build receipts, scalar primitive, builder, and all three focused regression tests. The validation receipt pins the contract and validator hashes.

## Claim gates

Open only:

- scalar 3–12-month weather construction validated
- strict-support historical Rice2 weather basis validated
- legacy Rice1 support preserved

Closed:

- MIRCA weight attachment
- published-response evaluation
- response fitting
- yield or damage calculation
- SCC calculation or GIVE integration

The next scientific gate is therefore not more weather aggregation. It is a separately authorized, source-faithful mapping from these branch-separated weather rows to an appropriate rice response/application domain, with any MIRCA weighting decision audited independently.
