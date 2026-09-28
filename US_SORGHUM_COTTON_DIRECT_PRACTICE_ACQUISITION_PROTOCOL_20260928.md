# U.S. sorghum and upland-cotton direct-practice acquisition protocol

**Frozen 2026-09-28 before downloading yield values.**

## Objective

Acquire the exact USDA NASS Quick Stats county SURVEY yield records needed to
determine whether sorghum grain and upland cotton can extend the U.S.
irrigated/non-irrigated validation beyond corn, soybean, and wheat.

## Exact series

- Sorghum grain: `SORGHUM`, `ALL CLASSES`, `GRAIN`, `BU / ACRE`.
- Upland cotton: `COTTON`, `UPLAND`, `ALL UTILIZATION PRACTICES`, `LB / ACRE`.
- Both: `YIELD`, `COUNTY`, `ANNUAL`, `YEAR`, `TOTAL`, `SURVEY`, separately
  for `IRRIGATED` and `NON-IRRIGATED`.
- Years: 1981--2018. The count screen found zero support in 2019.

One crop/practice/year is requested at a time. The official count endpoint is
called first; requests above 50,000 records fail closed. Raw JSON and
credential-free hashes/manifests remain ignored. The API key is read only from
`.secrets/nass.env` and must never appear in a URL receipt, log, output, or Git.

## Eligibility and pairing

Preserve NASS `Value`, `CV (%)`, location metadata, and any disclosure or
suppression notation. A record is numerically eligible only when `Value`, after
removing commas, parses to a finite strictly positive number and both state and
county ANSI codes are present with lengths two and three. Do not convert `(D)`,
`(Z)`, missing, or nonnumeric values. Pair only exact crop--county--year keys
with one eligible record in each practice. Duplicate keys fail closed.

## Gates

Report raw, coded-geography, numeric, and paired support by crop/year/state.
This acquisition does not supply crop calendars or weather. It authorizes no
causal irrigation comparison, national representativeness, climate response,
damage, or SCC calculation. Sorghum/cotton modeling remains closed until
calendar, geography, weather, and independent validation gates are frozen.
