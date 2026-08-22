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

The supplied [Blumberg (2026) appendix](BLUMBERG_2026_APPENDIX_NOTE.md)
adds a complementary agricultural-functional-form benchmark.  It locks a
comparison of seasonal-total, distribution, extremes, binned, and constrained
nonlinear specifications; it also makes clear that the 100th meridian is only
an irrigation-related robustness split, never a rainfed label.

## Locked initial inputs

| Input | Planned use | Authority |
|---|---|---|
| USDA NASS Quick Stats | County yield, production, and harvested area for maize, soybean, winter/spring wheat, rice | https://www.nass.usda.gov/quick_stats/ |
| gridMET | Primary daily county crop-area weather features, CONUS, 1979-present, about 4 km | https://climatetoolbox.org/data/past-weather-data |
| Daymet | 1 km daily weather robustness comparison | https://daymet.ornl.gov/getdata |
| NASS planting/harvest reports and Crop Progress | Calendar priors and timing sensitivity | https://www.nass.usda.gov/Publications/Todays_Reports/reports/fcdate10.pdf |
| Cropland Data Layer / Crop Sequence Boundaries | Crop-area masks/weights where the historical period permits | https://www.nass.usda.gov/developer/ |
| U.S. Drought Monitor county statistics | Observed county-week composite-drought validation benchmark | https://droughtmonitor.unl.edu/DmData/DataDownload/WebServiceInfo.aspx |

Raw US inputs stay under `data/raw/us_county/` and are gitignored. Record
license, query/download URL, retrieval date, checksum, filters, units, and
suppression handling before an estimation panel is accepted.

The primary NASS outcome source is a dated Quick Stats bulk crops snapshot,
not an unversioned API response. Run
`python us_county_validation/scripts/download_nass_bulk_crops.py` repeatedly
to acquire verified ranges. The downloader pins content length, ETag, and last
modified time; it refuses to continue if the upstream object changes and
writes a SHA-512 manifest only after the full archive is present. The initial
snapshot is `qs.crops_20260821.txt.gz` (1,128,988,003 bytes). No crop, geography,
unit, or suppression filters are accepted until the downloaded header and
field definitions have been inspected.

USDM area-share files are acquired only with the explicit, state/year-bounded
downloader in `scripts/`; its manifest preserves the official query URLs and
checksums. A USDM category is never projected directly into a global SCC draw.
`prepare_usdm_county_weeks.py` standardizes the exclusive county-week area
shares and preserves `D0` separately from the `D1+` drought-exposure measure;
it refuses duplicate county-week inputs or shares that do not sum to 100.

## Primary design

1. Begin with a **high-rainfed-share county sample** for maize, soybean, and
   wheat. NASS county yield is not inherently irrigation-specific, so do not
   call it rainfed without a separate crop-specific irrigated-area measure.
   Pre-specify a primary rainfed-share threshold and test nearby thresholds;
   exclude or separately model materially mixed counties.
2. Build crop--county--year outcomes, retain reported NASS values and flags,
   and use harvested area only as an aggregation weight.
3. Aggregate daily weather to crop-area-weighted county exposures; do not use
   county centroid weather as the main measure where crop masks are available.
4. Include joint temperature, seasonal precipitation total, normalized
   within-season precipitation shares, wet days, CDD, and heavy-rain metrics.
5. Estimate county and year fixed-effect primary specifications, with
   crop/agro-climatic pooling. Compare regularized and constrained nonlinear
   alternatives without allowing them to select features using test outcomes.
6. Use nested blocked year, state/region, and dry/wet-extreme validation.
   Treat the US fit as a validation/heterogeneity input to the global model.

## Irrigation identification gate

The initial county sample will use crop-specific irrigated versus non-irrigated
harvested-area data where available from USDA Census/irrigation products. A
fixed cross-sectional irrigation share is an imperfect proxy for annual
practice; it is therefore a selection device, not a claim that every included
observation is un-irrigated. The analysis will report results under multiple
thresholds and a mixed-county sensitivity specification. No US estimate enters
the global model unless this gate and its coverage diagnostics pass.

The supplied US water manuscripts motivate a later irrigated-water constraint
extension: irrigation is an adaptation/input whose feasibility can respond to
snowpack, runoff, water rights, and seasonal scarcity. It is deliberately
outside the initial high-rainfed-share estimand; see
[the evidence and non-overlap note](../IRRIGATED_WATER_EVIDENCE_NOTE.md).

## Explicit exclusions

- No direct extrapolation of a US coefficient to unsupported global regions.
- No adding a US damage estimate beside the global agricultural component.
- No separate CO2 fertilization term after a response that already embeds it.
- No silently treating NASS suppression or missingness as zero yield.
