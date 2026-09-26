# Additional-crop NASS direct-practice count feasibility results

**Run:** 2026-09-25 under the frozen
`US_ADDITIONAL_CROP_DIRECT_PRACTICE_COUNT_PROTOCOL_20260925.md`.

## Decision

Sorghum grain, upland cotton, barley, and oats pass the deliberately
permissive count-only gate for a later exact-record overlap audit. Rice fails:
county survey rice-yield records exist, but none are labeled `IRRIGATED` or
`NON-IRRIGATED` even after removing class, utilization, domain, and unit
filters.

No yield value was downloaded, no county pair was observed, and no weather or
model was run. A count pass is not a usable panel; it only means that marginal
counts do not rule one out.

## Exact count support

The all-years columns are the stage-one Quick Stats counts. The remaining
columns use separately queried annual counts for 1981--2019. For each year,
the paired-count upper bound is the smaller of the irrigated and
non-irrigated marginal counts; actual same-county overlap can only be smaller.

| Crop series | All-years irrigated | All-years non-irrigated | 1981--2019 paired-count upper bound | Years with positive upper bound | Years with upper bound >=25 | 2001--2019 years with upper bound >=25 | Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| Sorghum, grain | 11,671 | 18,540 | 6,439 | 38 (1981--2018) | 33 | 13 | Pass |
| Cotton, upland | 5,921 | 9,392 | 4,524 | 38 (1981--2018) | 38 | 18 | Pass |
| Rice, all classes | 0 | 0 | Not queried | 0 | 0 | 0 | Blocked |
| Barley, all classes | 13,098 | 17,756 | 5,766 | 28 (1981--2008) | 28 | 8 | Pass, historical only |
| Oats, all classes | 7,086 | 7,413 | 1,978 | 28 (1981--2008) | 26 | 6 | Pass, historical only |

All four passing crops clear every frozen threshold: at least 500 all-years
records in each practice, at least 500 summed annual paired-count upper bound,
at least 10 positive years, at least five years with an upper bound of 25, and
at least five such years during 2001--2019.

The time support matters. Sorghum and upland cotton have positive marginal
counts through 2018, but zero in 2019. Barley and oats stop after 2008. Their
count pass therefore supports only a historical acquisition audit, not a
recent terminal validation. Barley's >=25 USDM-era support is 2001--2008;
oats' is 2001--2006.

## Rice zero-count diagnosis

The separately frozen broad diagnostic made three all-years count requests
with class, utilization, domain, and unit omitted:

- county survey rice yield without a practice filter: 9,725 records;
- with `IRRIGATED`: 0 records; and
- with `NON-IRRIGATED`: 0 records.

Thus the rice failure is not caused by the primary `CWT / ACRE` or
all-classes filter. The county survey yield series is not directly stratified
by production practice, so rice cannot supply the requested direct-practice
yield panel through this route.

## Remaining gates before any modeling

For each passing crop, a separately frozen acquisition must still establish:

1. actual common county/year support between the two practice series after
   preserving disclosure and suppression flags;
2. positive numeric yields, unique five-digit county GEOIDs, and the frozen
   minimum actual-pair thresholds;
3. historically valid county geography and sufficient state breadth;
4. a crop-specific NASS calendar and weather-feature mapping; and
5. prespecified estimation and independent validation.

The current prepared calendar file
`config/us_county_nass_usual_date_definitions_2010.csv` contains only corn,
soybean, and wheat calendars. It therefore does not yet authorize weather
construction for sorghum, cotton, barley, or oats. Cotton must remain the
prespecified upland class; Pima and upland records cannot be pooled without a
new class-weight protocol.

All causal, irrigation-treatment, national-representativeness, damage, and SCC
gates remain closed.

## Validation, resources, and artifacts

The structural validator reconstructed all 322 primary count queries, three
broad rice queries, the staged request matrix, every gate, and the feasible
and blocked crop lists. It found no credential field and confirmed that all
data/model flags remain false.

The network count pass checkpointed every count under ignored `data/interim/`
and peaked at 32,292,864 bytes RSS. A post-query summary indentation bug caused
that first process to exit after all counts were safely checkpointed; the
corrected final aggregation completed at 28,475,392 bytes, the rice diagnostic
at 30,670,848 bytes, and validation at 23,920,640 bytes. All are far below the
512 MiB cap. Earlier failed network/sandbox attempts remain explicitly named
as rejected receipts under ignored `data/interim/`.

- Primary protocol:
  `US_ADDITIONAL_CROP_DIRECT_PRACTICE_COUNT_PROTOCOL_20260925.md`
- Primary implementation:
  `us_county_validation/scripts/audit_nass_additional_crop_direct_practice_support.py`
- Primary count result:
  `data/interim/us_county/nass_additional_crop_direct_practice_count_support_20260925.json`
- Rice diagnostic protocol:
  `US_RICE_DIRECT_PRACTICE_ZERO_COUNT_DIAGNOSTIC_20260925.md`
- Rice diagnostic result:
  `data/interim/us_county/nass_rice_direct_practice_zero_count_diagnostic_20260925.json`
- Structural validator:
  `us_county_validation/scripts/validate_nass_additional_crop_direct_practice_support.py`
- Validation result:
  `data/interim/us_county/nass_additional_crop_direct_practice_count_validation_20260925.json`
