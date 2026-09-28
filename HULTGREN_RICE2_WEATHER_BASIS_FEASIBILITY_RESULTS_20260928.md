# Hultgren Rice2 weather-basis feasibility audit

Date: 2026-09-28

Status note: this is the frozen pre-implementation audit. Its recommended gate
was subsequently implemented and validated in
`HULTGREN_RICE2_ONE_YEAR_WEATHER_PILOT_RESULTS_20260928.md`; the hashes in this
audit's contract intentionally identify the pre-patch implementation.

## Finding

A separate Rice2 weather basis is technically reconstructable on a strict,
non-imputed subset of the resident data, without copying Rice1. It is **not yet
executable source-faithfully with the current builder**. The blocking issue is
not missing Rice2 calendars or historical daily weather; it is a current code
guard that excludes the short seasons actually present in the published rice
estimation panel and dominant in the Rice2 calendar.

No rice weather basis, response, fitted model, damage, or SCC was produced in
this audit. Exact reproduction of the authors' historical GMFD/SAGE weather
inputs also remains unavailable; the resident daily weather is an alternative
GSWP3-W5E5 transport product.

## Preserved Hultgren evidence

The recovered prepared panel
`data/raw/hultgren_response/historical_git/dae5fe8d0d4a260328e4baa45b547368bd6790b3/rice_gmfd_v1_ready.dta`
contains 178,157 rows. Reapplying the published complete-case and iterative
singleton rules gives 166,174 estimation rows, including:

- 1,560 rows labeled `first`;
- 1,189 rows labeled `second` (708 Sri Lanka and 481 Vietnam);
- 791 rows labeled `third`; and
- 162,634 rows labeled `total`.

All 1,189 second-season estimation rows have four- or five-month calendars:
708 are four months and 481 are five months. Across all 124,588 complete
three- through five-month estimation rows, both third-phase rainfall terms are
exactly zero. This is direct prepared-panel evidence that the published
2/3/remainder precipitation construction permits an empty third phase. It is
not calendar imputation.

The 12 preserved Hultgren `.do` files contain no explicit `ri2` or `Rice2`
branch. They configure one pooled rice response, while the prepared panel
retains the within-year season label. Thus a Rice2 weather basis may use the
published pooled weather transformation, but this audit does not authorize a
new season-specific coefficient fit or a global response evaluation.

## Separate Rice2 calendar evidence

The pinned GGCMI Phase 3 manifest contains independent `ri2_noirr` and
`ri2_firr` files. Each has 31,005 finite Rice2 calendar cells; 6,197 have both
a finite calendar and a positive publisher `fraction_of_harvested_area`. Every
finite Rice2 cell declares source index 4, documented in-file as RICEATLAS.
The two Rice2 irrigation-regime arrays happen to be identical, but they are not
copies of Rice1: among the 31,005 cells with both Rice1 and Rice2 calendars,
30,887 have different whole-month planting/harvest calendars and only 118 are
the same.

The Rice2 whole-month distribution is 72 three-month, 6,076 four-month,
12,591 five-month, 2,886 six-month, 3,391 seven-month, and 5,989 eight-month
finite cells. Therefore, retaining the current six-month minimum would remove
18,739 of 31,005 finite Rice2 calendar cells before any weather calculation.

The MIRCA administrative calendar files independently contain 4,849 `Rice2`
records per irrigation system. All 144 positive rainfed and 614 positive
irrigated records have complete unit, planting-month, and maturity-month
fields. Those CSVs do not, by themselves, provide an executable
administrative-unit-to-grid join, so they are corroborating metadata rather
than a substitute for the gridded GGCMI Rice2 calendars.

## Strict no-fill overlap with current MIRCA Rice2 layers

Using unrepaired Rice2 positive-area masks reconstructed from the preserved
candidate and requiring an exact half-degree match to a finite GGCMI Rice2
calendar with positive publisher season fraction gives:

| System | Positive MIRCA Rice2 cells | Direct no-fill cells | Direct no-fill area | Share of unrepaired Rice2 area | Area retained by current 6--12 month guard |
|---|---:|---:|---:|---:|---:|
| Rainfed | 7,143 | 2,751 | 20.389 million ha | 85.9804% | 1.191 million ha (5.8435% of direct support) |
| Irrigated | 4,561 | 2,796 | 26.666 million ha | 78.2237% | 5.383 million ha (20.1869% of direct support) |

All 2,751 direct rainfed cells and 2,788 of 2,796 direct irrigated cells have
whole-month Rice2 calendars distinct from Rice1. Cells outside this strict
overlap remain missing; they are not nearest-neighbor filled, assigned a Rice1
calendar, or renormalized away. The MIRCA table remains a failed-reconciliation
sensitivity and is not promoted to production weights.

## Exact implementation blocker

`scripts/build_hultgren_rice_grid_weather_basis.py` currently:

1. limits `--calendar-branch` to `ri1_noirr` and `ri1_firr`; and
2. filters support to six through twelve months.

`src/hultgren_rice_weather.py` independently rejects seasons shorter than six
months. The builder's phase slices already compute the source-consistent
structural zero for an empty third phase, so no invented weather values are
needed. Enabling `ri2` without correcting both guards would retain only 5.84%
of direct rainfed Rice2 area and 20.19% of direct irrigated Rice2 area and is
therefore rejected.

The local alternative-weather inventory is complete for precipitation, daily
minimum temperature, and daily maximum temperature in four blocks spanning
1981--2019. The 1981--2010 blocks were already exercised in the validated
Rice1 preflight. Availability does not make this an exact GMFD/SAGE historical
reproduction.

## Decision and next gate

The feasibility gate passes; the build gate stays closed. The single safest
next calculation is to patch only the rice primitive and builder guards to
accept explicitly declared `ri2_noirr`/`ri2_firr` and source-observed 3--12
month seasons, with absent later phase months fixed at exact zeros. Then run a
one-harvest-year pilot on the strict finite, positive-publisher-fraction Rice2
support and independently reaggregate distributed three-, four-, five-, and
cross-year calendar sentinels directly from daily weather. Do not attach
production weights or evaluate the response at that gate.

## Audit artifacts

- Contract: `config/hultgren_rice2_weather_basis_feasibility_v1.toml`
- Audit: `scripts/audit_hultgren_rice2_weather_basis_feasibility.py`
- Tests: `scripts/test_audit_hultgren_rice2_weather_basis_feasibility.py`
- Independent validator: `scripts/validate_hultgren_rice2_weather_basis_feasibility.py`
- Receipt: `data/provenance/hultgren_rice2_weather_basis_feasibility_20260928.json`
- Validation: `data/provenance/hultgren_rice2_weather_basis_feasibility_validation_20260928.json`

The audit used 365,838,336 bytes peak RSS and the validator used 318,128,128
bytes, both below the 536,870,912-byte cap. All response, fit, damage, and SCC
gates remain closed.
