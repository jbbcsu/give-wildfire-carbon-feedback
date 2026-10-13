# Compact LOCA2 county-strata expansion preregistration

## Purpose and frozen selection

This outcome-blind design expands the historical direct-rainfall diagnostic
beyond the three Nebraska sentinels without selecting on any LOCA2 result,
nClimGrid climate value, or yield magnitude. Candidate counties require:

- complete 2001--2012 all-practice corn support using only eligibility flags;
- finite NASS irrigation-share metadata;
- the fixed primary USDA NASS planting/harvest calendar;
- the accepted TIGER-2019 geography status; and
- a resident, hash-bound nClimGrid county-weight receipt with at least 0.999
  coverage, at least 0.95 valid area relative to declared land, and positive
  weather cells.

Three nonoverlapping state-group/calendar/irrigation strata were frozen before
selection. Within each stratum in fixed order, the chosen county maximizes its
minimum TIGER internal-point distance to Cuming, Box Butte, Furnas, and any
earlier expansion selection; exact ties use ascending GEOID.

## Selected compact design

| Stratum | County | Irrigation share | Primary season | Minimum distance to prior design |
|---|---|---:|---|---:|
| Western irrigated | Solano, California (`06095`) | 0.997 | May 16--Oct 16, 154 days | 1,655.76 km |
| Southeastern early, mostly rainfed | Grady, Georgia (`13131`) | 0.189 | Apr 6--Sep 3, 151 days | 1,659.93 km |
| Humid Midwest later, rainfed | Shelby, Indiana (`18145`) | 0.034 | May 16--Oct 21, 159 days | 963.34 km |

The strata contain 6, 5, and 101 eligible counties, respectively. The broader
fail-closed candidate pool has 188 counties in 11 states after all support,
calendar, geography, and resident nClimGrid-weight gates. These labels are
design proxies for broad climate/agronomic diversity, not observed climate
classifications and not claims about realized LOCA2 performance.

## Deferred bounded execution plan

No download or climate computation was launched. The selected design implies
12 strictly sequential LOCA2 jobs: three counties, two prespecified
model-members, and two nonoverlapping six-year partitions (2001--2006 and
2007--2012). Every worker retains the 512 MiB cap, 3 GiB free-space gate, and
the direct variable-serial native-chunk accumulator.

Execution remains blocked in this order:

1. build and validate one LOCA2 TIGER-2019 weight table per county;
2. construct outcome-free 2001--2012 nClimGrid features for only these three
   counties using their resident validated nClimGrid weights and frozen primary
   calendars;
3. run all 12 metadata-only LOCA2 preflights; and
4. only after the separate 11-cell SPEI bridge is idle or complete, run the 12
   climate jobs sequentially and independently validate/merge them.

Step 2 is the current scientific execution prerequisite: the selected counties
have validated nClimGrid weights, but their 2001--2012 seasonal feature tables
are not resident. Creating those features must remain outcome-free. Additional
LOCA2 downloads before that prerequisite would not produce a comparable
historical diagnostic and could compete with the SPEI bridge.

The metadata/geometry selector completed at a sampled 166.59 MiB process-group
peak. All 35 LOCA2 tests passed under the same monitor at 201.44 MiB; the six
focused tests independently rebuild the candidate set, reproduce the three
selections, verify selected nClimGrid weight hashes, and enforce the deferred
12-job matrix and closed claim gates.

## Claim boundary

Only the compact design-selection gate is open. County LOCA2 weights, observed
features, historical sentinels, representative multi-county validation, model
skill, outcome response, causal damage, and SCC gates remain closed.

Reproduction inputs and the 12-job plan are hash-bound in
`data/provenance/loca2_compact_strata_expansion_preregistration_20261013.json`;
the frozen criteria are in
`config/loca2_us_compact_strata_expansion_v1.toml`.
