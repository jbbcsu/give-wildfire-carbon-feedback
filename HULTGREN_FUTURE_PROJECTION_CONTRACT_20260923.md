# Source-matched global maize projection contract

## Purpose and status

This contract defines the next use of the reproduced Hultgren et al. maize
response as a global empirical benchmark. It prevents a historically valid
coefficient vector from being applied to mismatched future features. Historical
response, phase arithmetic, and one published local-response checkpoint now
pass; future response, agricultural damage, and SCC gates remain closed.

## Required weather basis

Every historical and future crop-unit-year must use the same construction:

1. Align daily precipitation and daily maximum temperature to the local
   planting-month through harvest-month window. Recovered source seasons span
   four through ten months; ten is a maximum, not a universal duration.
2. Sum daily precipitation to calendar-month totals before transformation.
3. Form phase 1 from month 1, phase 2 from months 2--4, and phase 3 from month 5
   through local harvest.
4. For each phase retain both the sum of monthly rainfall totals and the sum of
   squared monthly rainfall totals. Do not square phase-total rainfall.
5. Compute growing-degree days from daily maximum temperature between 8 C and
   31 C, and killing-degree days above 31 C.

`src/hultgren_maize_weather.py` implements step 3--5 after calendar alignment.
The calendar join and spatial crop weighting remain separate so their source
identities and coverage can be audited.
Its validated `with_moderators` boundary attaches a declared income,
irrigation, and long-run-climate state to the published 49-term evaluator; it
does not select those moderator values.

## Spatial and temporal alignment gates

The historical response was fitted to crop-weighted administrative-unit weather
and local crop calendars, not directly to the project's GGCMI grid cells.
Therefore the benchmark projection must either reconstruct source-compatible
administrative-unit features or demonstrate numerical equivalence of a
grid-cell-first aggregation. The choice is made on historical overlap before
future outcomes are examined.

Promotion requires all of the following:

- identical historical unit, calendar, and crop-weight support for baseline and
  future transformations;
- exact monthly precipitation conservation from daily input;
- exact phase-to-season linear and quadratic accounting within storage
  tolerance;
- historical GDD/KDD agreement against a source-derived checkpoint;
- explicit handling of cross-year seasons and missing daily observations;
- a joint-support report for every projected weather basis term and moderator;
- rejection or labeled extrapolation for cells outside historical support.

The project's existing five-ESM daily pipeline is an input candidate, not an
automatic match. Its proportional crop stages cannot substitute for the
published calendar-month phases without a historical equivalence result.

## Moderator and adaptation scenarios

The response varies with log income per capita, irrigated share, long-run
growing-season maximum temperature, and long-run growing-season precipitation.
Those moderators cannot be omitted or silently held at arbitrary values. The
already approved scenarios are:

- **Fixed adaptation:** hold income and irrigation at the registered baseline;
  update weather exposures while keeping the declared baseline long-run climate
  moderators fixed.
- **Trend adaptation:** advance income and irrigation along documented trend or
  scenario paths; update long-run climate moderators using a trailing-climate
  rule frozen before results.
- **Upper adaptation:** use the preregistered upper adaptation trajectory for
  income/irrigation and any allowed response adjustment, without selecting the
  path from resulting damages.

Each scenario must state baseline year, interpolation, caps, missing-country
rule, and whether long-run climate moderators evolve. These scenarios are
reported separately rather than averaged.

## Uncertainty and attribution

Coefficient uncertainty uses draws from the validated 49-by-49 published
covariance matrix. Climate uncertainty uses named ESM/scenario members without
treating model spread as a probability distribution. Moderator/adaptation
uncertainty remains a discrete scenario dimension. The output ledger retains
all three dimensions so none is collapsed prematurely.

The benchmark estimates joint temperature--precipitation yield response. A
precipitation-attributable component requires paired evaluation holding
temperature and all nonprecipitation moderators fixed between the factual and
counterfactual weather states. The joint response is also retained. Adding a
separate drought, rainfall, or temperature damage term to the same crop output
is prohibited unless an explicit orthogonal attribution design demonstrates no
double counting.

## Remaining implementation sequence

1. Reproduce source-compatible historical monthly precipitation, GDD, and KDD
   checkpoints from primitive daily climate. The author-selected Iroquois local
   response already matches across Stata and Python; it validates the response
   evaluator, not primitive climate transformation.
2. Freeze the administrative-unit/grid aggregation choice on historical data.
3. Generate matched historical and future basis files from the same code path.
4. Apply fixed, trend, and upper-adaptation moderator ledgers.
5. Produce coefficient-draw by ESM by adaptation response panels and support
   diagnostics.
6. Validate crop-output aggregation before monetary valuation.
7. Use the isolated agricultural welfare adapter and GIVE pulse machinery only
   after response, support, attribution, and no-double-counting gates pass.

No new modeling choice is needed from the user at this stage. The next blocker
is empirical: a source-compatible primitive historical-weather checkpoint must
be produced before future projections can be called validated.
