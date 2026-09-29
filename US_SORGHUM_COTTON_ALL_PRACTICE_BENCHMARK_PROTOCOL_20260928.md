# Frozen sorghum/cotton all-practice outcome benchmark protocol

**Frozen:** 2026-09-28 after the direct-practice PDSI and direct-weather
predictive gates were found null, and before querying or inspecting any
all-production-practice sorghum or cotton value.

## Question and role

Do the selected county/year records with both reported irrigated and
non-irrigated yields align with the same-source USDA NASS
`ALL PRODUCTION PRACTICES` county yield universe? This is an outcome-support,
sample-selection, and internal-coherence audit. It does not fit another
weather model.

The audit has two goals:

1. quantify how selected the paired direct-practice samples are relative to
   all positive county survey yields for the same crop/year series; and
2. test whether the all-practice yield is numerically consistent with the two
   reported practice yields on common crop/county/year keys.

It cannot identify causal irrigation effects. All-practice yield is not added
to either the direct-weather or PDSI/SPEI model family, and those moisture
families remain mutually exclusive.

## Frozen acquisition

For every year 1981--2018, query exactly one county annual survey-yield series
for each crop:

- sorghum: commodity `SORGHUM`, class `ALL CLASSES`, utilization `GRAIN`,
  unit `BU / ACRE`;
- cotton: commodity `COTTON`, class `UPLAND`, utilization
  `ALL UTILIZATION PRACTICES`, unit `LB / ACRE`.

Every query additionally fixes source `SURVEY`, sector `CROPS`, statistic
`YIELD`, aggregation `COUNTY`, frequency `ANNUAL`, reference period `YEAR`,
domain `TOTAL`, and production practice `ALL PRODUCTION PRACTICES`.

Use the official Quick Stats count endpoint before each data request. Refuse a
negative count, a count over 50,000, or a response whose rows differ from the
key-free query. Read the credential only from ignored `.secrets/nass.env` and
never print or store it. Raw responses remain under ignored `data/raw/`.

## Frozen row and match rules

- Retain a row only if two-digit state ANSI and three-digit county ANSI codes
  form a five-digit GEOID and `Value` parses to a finite positive number.
- Never impute disclosure-suppressed, missing, zero, aggregate-geography, or
  duplicate rows.
- Use the validated geography-eligible paired-practice panel
  `data/interim/us_county/nass_sorghum_cotton_geography_eligible_panel_20260928.parquet`.
- Collapse its two practices only by exact crop, county GEOID, and harvest
  year; require exactly one positive irrigated and one positive non-irrigated
  yield with the expected shared unit.
- Match the all-practice benchmark on that exact key. Do not broaden crop,
  class, utilization, year, or geography.

## Frozen support and coherence metrics

For each crop report:

- positive coded all-practice county-years, unique counties, states, and
  annual support;
- direct-practice paired keys, exact benchmark matches, and match fraction;
- paired-key coverage of the all-practice county-year universe overall, by
  state, and by year;
- states present in the all-practice universe but absent from the paired
  sample;
- whether the all-practice yield is below, exactly equal to, strictly between,
  exactly equal to, or above the two practice yields; and
- maximum and quantiles of any distance outside the practice-yield interval.

The primary interval check is exact. A prespecified rounding sensitivity
expands the interval by `max(0.5 outcome unit, 0.001 * all-practice yield)` on
each side.

The source-coherence support gate requires at least 90% of paired keys to have
an all-practice benchmark. The numeric-bracket gate requires at least 95% of
matched keys to fall within the rounding-tolerant practice interval. These
thresholds diagnose source/sample coherence only; neither gate authorizes a
weather-response fit or causal interpretation.

Classify paired-key coverage of the all-practice universe descriptively as
`broad` at >=50%, `selected` at 20--<50%, and `highly_selected` below 20%.
National representativeness remains unauthorized regardless of classification.

## Validation and claims

Require an independent implementation to reparse every hash-bound raw response
and the paired panel, reconstruct all reported aggregates, and verify that no
credential appears in tracked receipts. Production and validation must each
remain below 512 MiB RSS.

No row-level benchmark panel, coefficient, prediction, causal effect,
irrigation treatment effect, future transfer, global response, damage, or SCC
value is released. All corresponding gates remain false.
