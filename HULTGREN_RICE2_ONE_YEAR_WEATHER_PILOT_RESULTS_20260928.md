# Hultgren Rice2 one-year weather-basis pilot

Date: 2026-09-28

Status note: this one-year gate was subsequently extended across the complete
resident historical period in
`HULTGREN_RICE2_HISTORICAL_MULTIBLOCK_RESULTS_20260928.md`. Its contract hashes
intentionally identify the builder version used for this frozen pilot.

## Result

The bounded Rice2 gate passes. The scalar rice weather primitive now accepts
the source-observed three- through twelve-month domain and treats absent later
precipitation phases as exact structural zeros. The grid builder accepts
explicit `ri2_noirr` and `ri2_firr` branches and, for Rice2 only, uses strict
support: a finite branch-specific calendar and positive publisher
`fraction_of_harvested_area`. It does not copy Rice1, fill missing calendars,
attach MIRCA area or production weights, or emit support magnitudes.

The 1982 GSWP3-W5E5 pilot produced 6,197 complete unweighted cell rows in each
Rice2 branch. The independent validator passed exact source identity, support,
calendar, finiteness, uniqueness, structural-zero, daily reaggregation,
memory, and claim gates.

## Scoped implementation change

- `src/hultgren_rice_weather.py` now accepts 3--12 months. Its unchanged phase
  slices are months 1--2, months 3--5 when present, and month 6 through
  harvest; empty slices sum to exact zero.
- `scripts/build_hultgren_rice_grid_weather_basis.py` now accepts
  `ri2_noirr`/`ri2_firr`. Rice2 support requires finite planting/maturity and
  positive publisher season fraction. No broad annual MIRCA raster is used.
- Rice1 retains its existing annual broad-rice Boolean mask and six-month
  minimum. Independent comparison to the preserved 1982--1990 Rice1 basis
  confirms the exact same 10,104 cells.

Focused tests cover three-, four-, five-, six-, and twelve-month phase
arithmetic, invalid domains, strict Rice2 support, and legacy Rice1 support.
Both test scripts pass.

## Pilot support

Each branch contains the same 6,197 calendar cells because the resident GGCMI
Rice2 rainfed and irrigated calendar arrays are identical. They remain
separate labeled outputs.

| Whole-month season | Rows per branch |
|---:|---:|
| 3 | 14 |
| 4 | 1,174 |
| 5 | 3,397 |
| 6 | 851 |
| 7 | 445 |
| 8 | 316 |

There are 4,585 three- through five-month rows and 1,616 cross-year rows per
branch. Every short-season `prcp_poly_1_bin3` and `prcp_poly_2_bin3` value is
exactly zero. All weather primitives are finite.

The two branch outputs are exactly equal in key, calendar, and weather fields
after removing the branch label. This reflects identical source calendar
arrays; it is not an aggregation of regimes.

## Independent daily sentinels

The validator independently reopened the raw daily precipitation, Tmin, and
Tmax files and rebuilt four deterministic sentinels in each branch:

| Kind | Cell center | Calendar | Daily records | Maximum absolute error |
|---|---|---|---:|---:|
| 3 months | 29.25 N, 79.25 E | February--April 1982 | 89 | 1.14e-13 |
| 4 months | 30.75 N, 119.75 E | April--July 1982 | 122 | 1.14e-13 |
| 5 months | 34.25 N, 116.75 E | March--July 1982 | 153 | 1.42e-14 |
| Cross-year | 28.75 N, 80.75 E | December 1981--March 1982 | 121 | 0 |

All precipitation-basis errors were exactly zero. The small reported maxima
are floating-point GDD/Tmin summation differences, far below the predeclared
`1e-7` tolerance.

## Resource bounds

- `ri2_noirr` build: 163,987,456 bytes peak RSS; 37.40 seconds.
- `ri2_firr` build: 158,400,512 bytes peak RSS; 37.44 seconds.
- Independent validator: 199,622,656 bytes peak RSS.
- Cap: 536,870,912 bytes.

## Artifacts

- Contract: `config/hultgren_rice2_one_year_pilot_v1.toml`
- Scalar tests: `scripts/test_hultgren_rice_weather.py`
- Builder compatibility tests:
  `scripts/test_build_hultgren_rice2_grid_weather_basis.py`
- Builder: `scripts/build_hultgren_rice_grid_weather_basis.py`
- Rainfed basis and build receipt:
  `data/interim/hultgren_rice2_one_year_pilot_20260928/ri2_noirr_1982.parquet`
  and adjacent `.result.json`
- Irrigated basis and build receipt:
  `data/interim/hultgren_rice2_one_year_pilot_20260928/ri2_firr_1982.parquet`
  and adjacent `.result.json`
- Independent validator: `scripts/validate_hultgren_rice2_one_year_pilot.py`
- Validation receipt:
  `data/provenance/hultgren_rice2_one_year_pilot_validation_20260928.json`

## Gates

Opened only:

- scalar 3--12 month rice weather method validated;
- strict-support, one-year Rice2 weather pilot validated; and
- prior Rice1 support preserved.

Still closed:

- multi-year Rice2 basis;
- MIRCA area or production-weight attachment;
- published response evaluation or new response fitting;
- monetary damage; and
- SCC use.

The safest next gate is a multi-block Rice2 weather build and validation on the
same strict calendar support, still unweighted, before revisiting the separate
failed-reconciliation MIRCA production-weight question.
