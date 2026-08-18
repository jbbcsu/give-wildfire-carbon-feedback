# US county precipitation--crop validation module

This is a high-resolution empirical and validation track for the global
precipitation-SCC agriculture replacement. It is not a US-only SCC module and
does not transfer US coefficients mechanically to the world.

## Role

The module follows the structural logic of Qiu et al. (2025): compare a
transparent primary response with regularized and nonlinear alternatives;
evaluate nested time and spatial holdouts and climate extremes; retain a
pre-specified near-best model set; propagate model uncertainty. The adapted
chain is daily climate -> precipitation-pattern exposure -> county yield ->
agricultural damage validation. National/global welfare translation remains
in the global track.

## Locked initial inputs

| Input | Planned use | Authority |
|---|---|---|
| USDA NASS Quick Stats | County yield, production, and harvested area for maize, soybean, winter/spring wheat, rice | https://www.nass.usda.gov/quick_stats/ |
| gridMET | Primary daily county crop-area weather features, CONUS, 1979-present, about 4 km | https://climatetoolbox.org/data/past-weather-data |
| Daymet | 1 km daily weather robustness comparison | https://daymet.ornl.gov/getdata |
| NASS planting/harvest reports and Crop Progress | Calendar priors and timing sensitivity | https://www.nass.usda.gov/Publications/Todays_Reports/reports/fcdate10.pdf |
| Cropland Data Layer / Crop Sequence Boundaries | Crop-area masks/weights where the historical period permits | https://www.nass.usda.gov/developer/ |

Raw US inputs stay under `data/raw/us_county/` and are gitignored. Record
license, query/download URL, retrieval date, checksum, filters, units, and
suppression handling before an estimation panel is accepted.

## Primary design

1. Build crop--county--year outcomes, retain reported NASS values and flags,
   and use harvested area only as an aggregation weight.
2. Aggregate daily weather to crop-area-weighted county exposures; do not use
   county centroid weather as the main measure where crop masks are available.
3. Include joint temperature, seasonal precipitation total, normalized
   within-season precipitation shares, wet days, CDD, and heavy-rain metrics.
4. Estimate county and year fixed-effect primary specifications, with
   crop/agro-climatic pooling. Compare regularized and constrained nonlinear
   alternatives without allowing them to select features using test outcomes.
5. Use nested blocked year, state/region, and dry/wet-extreme validation.
   Treat the US fit as a validation/heterogeneity input to the global model.

## Explicit exclusions

- No direct extrapolation of a US coefficient to unsupported global regions.
- No adding a US damage estimate beside the global agricultural component.
- No separate CO2 fertilization term after a response that already embeds it.
- No silently treating NASS suppression or missingness as zero yield.
