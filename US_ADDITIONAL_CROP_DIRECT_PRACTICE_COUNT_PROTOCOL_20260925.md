# Additional-crop NASS direct-practice count feasibility protocol

**Frozen:** 2026-09-25 before querying any count in this crop screen.

## Purpose and boundary

Determine whether official USDA NASS Quick Stats contains enough county-level,
annual, directly reported irrigated and non-irrigated yield records to justify
a later exact-record acquisition for additional crops. This screen retrieves
counts only. It does not download yield values, infer paired counties, join
weather, estimate a response, compare irrigation treatments, calculate
damages, or calculate an SCC.

The API credential is read only from the ignored local
`.secrets/nass.env`. It may not be printed, embedded in saved query parameters,
written to a URL in an artifact, or included in an exception. Saved artifacts
contain only the official count endpoint, key-free parameters, counts,
timestamps, hashes, and derived feasibility summaries.

## Frozen exact series

Every query fixes source `SURVEY`, sector `CROPS`, aggregation `COUNTY`,
statistic `YIELD`, annual frequency, reference period `YEAR`, domain `TOTAL`,
one of the production practices `IRRIGATED` or `NON-IRRIGATED`, and JSON
format. The crop-specific fields are:

| Screen crop | Commodity | Class | Utilization | Unit |
|---|---|---|---|---|
| Sorghum grain | `SORGHUM` | `ALL CLASSES` | `GRAIN` | `BU / ACRE` |
| Upland cotton | `COTTON` | `UPLAND` | `ALL UTILIZATION PRACTICES` | `LB / ACRE` |
| Rice | `RICE` | `ALL CLASSES` | `ALL UTILIZATION PRACTICES` | `CWT / ACRE` |
| Barley | `BARLEY` | `ALL CLASSES` | `ALL UTILIZATION PRACTICES` | `BU / ACRE` |
| Oats | `OATS` | `ALL CLASSES` | `ALL UTILIZATION PRACTICES` | `BU / ACRE` |

Upland cotton is the prespecified cotton target because it is a named standard
yield series. Pima cotton is not pooled with it. Sorghum is limited to grain.
Barley and oats are included because their standard all-class annual bushel per
acre series require no adaptive descriptor discovery.

## Frozen staged count requests

1. Query one all-years count for each crop/practice series.
2. Only when both practice totals are at least 500 and below the API's 50,000
   record cap, query separate annual counts for every year 1981--2019.
3. Never call the data endpoint in this run, including when a crop passes.

For year `t`, define the *paired-count upper bound* as the smaller of the
irrigated and non-irrigated counts. Counts cannot show whether the records are
the same counties, so this is only an upper bound.

## Frozen count-feasibility gate

A crop passes the count-only gate only if all of the following hold:

- both all-years practice totals are at least 500 and below 50,000;
- the sum of annual paired-count upper bounds over 1981--2019 is at least 500;
- at least 10 years have a positive upper bound;
- at least five years have an upper bound of at least 25 county records; and
- at least five 2001--2019 years have an upper bound of at least 25, preserving
  potential overlap with the U.S. Drought Monitor era.

These deliberately permissive thresholds authorize only a later acquisition
and exact overlap audit. After acquisition, a separate frozen gate must verify
numeric positive yields, disclosure flags, unique five-digit county GEOIDs,
at least 500 actual paired county-years, at least 10 supported years, at least
25 actual paired counties in five years, calendar availability, geography
harmonization, and weather overlap. Suppressed or absent observations remain
missing and are never zero-filled.

## Interpretation

A passing count screen means only that the marginal series counts do not rule
out a usable direct-practice panel. A failure is sufficient to block exact
record acquisition under this protocol. A pass cannot establish common-county
support, geographic breadth, longitudinal continuity, causal identification,
an irrigation treatment effect, national representativeness, future or global
transfer, damages, or SCC relevance.
