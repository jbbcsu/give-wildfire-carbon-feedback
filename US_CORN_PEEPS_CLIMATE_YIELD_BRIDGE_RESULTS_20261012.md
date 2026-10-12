# Published climate-response bridge to U.S. corn yield

## Question

What does the frozen U.S. non-irrigated corn response imply when it is driven
by a published warming-linked precipitation pattern rather than an arbitrary
100 mm rainfall contrast?

This calculation links two separately validated pieces:

1. author-published PEEPS monthly precipitation slopes for MPI-ESM1-2-HR
   SSP5-8.5, in precipitation per degree of global warming; and
2. the frozen NASS/nClimGrid historical seasonal-rainfall response, conditional
   on crop-stage temperatures.

It isolates the precipitation-mediated channel by holding temperature fixed
inside the historical response. It is the first one-model climate-to-rainfall-
to-yield bridge for the U.S. track, not a damage or SCC estimate.

## Construction

Each of the 361 supported county internal points is mapped to the nearest
native PEEPS grid cell with circular-longitude distance. Monthly slopes are
integrated over the exact NASS usual-date corn season for each of 7,013 paired
county-years, including partial months. The resulting crop-season rainfall
slope is evaluated through the fitted linear/quadratic rainfall response at
each observed county-year exposure. County-year contrast vectors are averaged
within county and then equally across counties. Irrigated and non-irrigated
response models remain separate.

## Result

Across the selected support, the published one-model pattern implies mean
crop-season rainfall change of `-25.20 mm/K` (median `-25.96`, range `-46.71`
to `+22.01`). Of 361 counties, 349 have negative and 12 positive slopes.

Evaluated through the historical response:

| Practice | Equal-county fitted yield response per K | 500 km spatial interval |
|---|---:|---:|
| Non-irrigated | -2.32% | -2.82% to -1.82% |
| Irrigated | +0.03% | -0.14% to +0.21% |

Equal-row results are similar: -2.45% for non-irrigated and +0.06% for
irrigated corn. These intervals propagate historical coefficient sampling
uncertainty only; they do not include climate-model, pattern-scaling, model-
selection, measurement, or transport uncertainty.

The non-irrigated point responses are strongly heterogeneous across the ten
selected states: approximately -3.90%/K in North Dakota, -3.82% in South
Dakota, -3.22% in Wyoming, -2.63% in Colorado, -2.39% in Nebraska, -2.09% in
New Mexico, -1.59% in Kansas, and -0.97% in Texas. Delaware is near zero and
the one supported Oklahoma county is positive because the fitted quadratic
rainfall curve changes local marginal sign. These are transports through a
common fitted response, not independent state estimates.

## Interpretation boundary

This bridge helps reconcile the small global average with the stronger U.S.
historical evidence: the one PEEPS pattern used in the global calculation
implies widespread crop-season drying on the selected U.S. support, and the
non-irrigated historical response converts it into a material yield penalty.
The effect is nearly absent for reported irrigated corn.

The result must not be promoted to a national yield effect or SCC because:

- it uses one ESM and one SSP5-8.5 linear pattern;
- the ten-state reported-practice sample omits several major Corn Belt states;
- the historical quantity response fails strict geographic and temporal
  stability gates;
- PEEPS monthly means omit daily dry spells, extremes, and PDSI;
- county internal points approximate spatial exposure on a coarse grid; and
- the summary has no harvested-area, production, price, welfare, or adaptation
  weighting.

The next gate is a multi-model U.S. climate-response ensemble, with LOCA2 or
another defensible downscaled source used for spatial validation and daily
drought/extreme sensitivities. Only after that should production and welfare
weights be added.

## Reproduction

- Implementation:
  `us_county_validation/scripts/build_us_corn_peeps_climate_yield_bridge.py`
- Aggregate receipt:
  `data/provenance/us_corn_peeps_climate_yield_bridge_20261012.json`
- State table (gitignored):
  `data/interim/us_corn_peeps_climate_yield_state_20261012.csv`

The bounded run peaked at 166.2 MB sampled process-group RSS under the 512 MiB
ceiling and exactly reproduces the frozen U.S. median rainfall-response
contrast before applying the climate slopes.
