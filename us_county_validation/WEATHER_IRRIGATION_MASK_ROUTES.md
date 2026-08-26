# U.S. county climate, irrigation, and crop-area routing

## Primary NOAA nClimGrid-Daily smoke

The authoritative primary candidate for the 1981--2019 county daily-weather
bridge is NOAA NCEI nClimGrid-Daily v1.0.0. The exact January 1981 object and
six May--October 1981 objects have been acquired and pinned separately by
SHA-512, byte length, ETag, Last-Modified, decoded version, grid, units,
variables, and daily chronology. The latter six objects cover 184 contiguous
days and support the real Cuming County corn/soy construction smoke.
The file contains `prcp`, `tmin`, `tmax`, and `tavg`; each date label applies
to the 24-hour period ending in the early morning of that date. NCEI states
that v1 inputs can be updated without a version bump, so any change to the
reviewed upstream identity fails closed.

The executable smoke is:

    .venv/bin/python us_county_validation/scripts/download_nclimgrid_smoke.py --year 1981 --month 1

The raw objects are gitignored. The bounded Cuming smoke now proves both
source/schema access and the selected spatial/temporal construction order; it
does not complete 1981--2019 acquisition or estimate a weather response. See
[the full daily weather/calendar contract](DAILY_WEATHER_CALENDAR_CONTRACT.md).

Sources:

* NOAA NCEI [official nClimGrid-Daily product](https://www.ncei.noaa.gov/products/land-based-station/nclimgrid-daily).
* NOAA NCEI [nClimGrid-Daily v1.0.0 user guide](https://www.ncei.noaa.gov/data/nclimgrid-daily/doc/nclimgrid-daily_v1-0-0_user-guide.pdf).
* NOAA NCEI [dataset DOI](https://doi.org/10.25921/c4gt-r169).

## Bounded gridMET robustness smoke

The first acquired weather input is deliberately one gridMET full-CONUS daily
NetCDF file: precipitation short name `pr`, calendar year 2018. The year is
inside the real locked 2018–2022 NASS corn-grain outcome support. The gridMET
publisher identifies it as a CONUS daily gridded meteorological product at
approximately 4 km from 1979 onward, and points to the Northwest Knowledge
Network full-NetCDF and THREDDS routes.

The executable fetch is:

    .venv/bin/python us_county_validation/scripts/download_gridmet_smoke.py --variable pr --year 2018

The downloader refuses variables outside pr/tmmn/tmmx, one year per run, and
files over 100 MiB. The currently reviewed acquisition is only `pr`/2018. Its
tracked provenance record pins byte length, SHA-512, ETag, Last-Modified,
content type, decoded grid, units, and daily chronology; reruns fail if either
the upstream HTTP identity or local content differs. New variable-years need a
separately reviewed tracked record rather than silently accepting whatever a
mutable direct URL serves. The raw NetCDF and append-only run manifest remain
gitignored. This does **not** compute county averages, join a yield, or
authorize an SCC input.

The publisher states that, to the extent possible under law, rights to
gridMET have been waived and the work is free of known copyright restrictions.
Because the publisher page does not name a standard license, the provenance
record uses SPDX `NOASSERTION`, not an inferred `CC0`; raw files remain
unredistributed by project policy. The same page cautions against using
gridMET to infer changes in precipitation intensity or frequency because
source changes introduce inhomogeneities. The U.S. response design therefore
uses gridMET as a historical weather-product robustness path, not as sole
evidence of a climate trend. nClimGrid-Daily is the current primary candidate,
and weather-product robustness remains required before interpreting timing or
extreme coefficients.

Sources:

* Climatology Lab, [official gridMET description, terms, and limitations](https://www.climatologylab.org/gridmet.html).
* Northwest Knowledge Network, [official full-NetCDF distribution](https://www.northwestknowledge.net/metdata/data/).
* Abatzoglou (2013), [gridMET construction](https://doi.org/10.1002/joc.3413).

## Crop-specific irrigation-share gate

The authoritative initial route is USDA NASS Census of Agriculture county
records, retrieved through the documented Quick Stats service after a bounded
series-discovery/count check. The exact 2012, 2017, and 2022 series have now
been acquired for corn, soybean, and all-classes wheat. For each crop and
vintage, the two otherwise identical county records are:

| Quantity | Required discovery target |
|---|---|
| Irrigated crop harvested area | `source_desc=CENSUS`; crop; `statisticcat_desc=AREA HARVESTED`; `agg_level_desc=COUNTY`; irrigation-status domain/category identifying irrigated acres; `unit_desc=ACRES` |
| Total crop harvested area | Same crop/statistic/geography/unit and census reference period, but total domain/category |

The discovery returned `domain_desc=TOTAL`, `domaincat_desc=NOT SPECIFIED`,
and production practices `IRRIGATED` and `ALL PRODUCTION PRACTICES`; these
exact labels are frozen in the tracked manifest. The static share is
`irrigated_acres / total_harvested_acres`; it selects high-rainfed counties
under preregistered thresholds but does not prove every county-year outcome is
non-irrigated. Fail the gate if either series has incompatible year/reference
period, non-county geography, duplicate keys, suppressed denominator, negative
values, or a share outside [0,1] after documented rounding tolerance. An
absent or `(D)` irrigated-acre numerator is never interpreted as zero.

The 2017 pre-outcome vintage is the recommended primary selector for the
2018--2022 all-practice outcome panel; 2012 and 2022 are temporal
sensitivities. At candidate 10/20/30 percent thresholds, the 2017 audit retains
428/540/610 corn counties, 393/472/511 soybean counties, and 219/271/304 wheat
counties. See [the exact practice and share screen](NASS_IRRIGATION_PRACTICE_SCREEN.md).

The 2023 Farm and Ranch Irrigation Survey documents crop-specific irrigated
harvested acres as a concept but its published tables should not be assumed to
provide the county panel needed here. It is evidence for the definition and a
cross-check, not a substitute for county-level numerator/denominator records.

Sources:

* USDA NASS [Quick Stats/developer information](https://www.nass.usda.gov/developer/).
* USDA NASS [2023 Farm and Ranch Irrigation Survey](https://data.nass.usda.gov/Publications/AgCensus/2022/Online_Resources/Farm_and_Ranch_Irrigation_Survey/index.php).

## Primary polygon route and crop-pixel sensitivity

The selected full-period primary spatial measure is the Census county-polygon
area-weighted nClimGrid exposure. It is explicitly a **county-average proxy**,
not a crop-pixel or average-farm exposure. For any feature basis already built
separately in each grid cell and crop calendar, compute:

`B[county,k] = sum(cell/county intersection area * B[cell,k]) / sum(intersection area)`.

The separate USDA NASS Cropland Data Layer (CDL) route is a crop-location
sensitivity. The exact 2017 national archive is acquired and validated. It
uses official class codes 1 for corn and 5 for soybeans, excludes distinct
double-crop classes, treats class 0 explicitly as background because nodata is
unset, selects 30 m pixel centers inside each county, and maps those centers
to nClimGrid cells. Its within-crop formula is:

`B[county,crop,k] = sum(selected crop-pixel area * B[cell,crop,k]) / sum(selected crop-pixel area)`.

Both routes construct nonlinear dry-spell, Rx1day/Rx5day, wet-day-intensity,
timing, temperature-threshold, interaction, and response bases at the grid-
cell/calendar-class level **before** spatial weighting. For all-classes wheat,
winter, spring, and durum bases remain separate until independent class shares
exist. Centroid weather is only a labeled diagnostic.

National CDL coverage begins in 2008. A 2017 or 2008--2019 crop mask applied
to 1981--2007 outcomes is therefore a retrospective measurement assumption,
not observed historical crop location. This limits interpretation of the CDL
sensitivity but does not block the county-polygon full-period primary proxy.
It is especially binding for the paired all-classes wheat series, which has no
observations after 2007; pooled all-wheat weather responses remain blocked.

Crop Sequence Boundaries (CSB) are a useful NASS field-boundary/rotation
product for an alternate or computational-support route. They are constructed
from historic CDL stacks and cover matching multiyear windows; they do not
replace annual CDL as the main year-specific crop mask.

Sources:

* USDA NASS [Cropland Data Layer overview and downloads](https://www.nass.usda.gov/Research_and_Science/Cropland/).
* USDA NASS [Crop Sequence Boundaries](https://data.nass.usda.gov/Research_and_Science/Crop-Sequence-Boundaries/).
* U.S. Census Bureau [TIGER/Line county boundaries](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html).

## Current gate status

* NASS corn-grain 2018–2022 outcomes: acquired and temporally audited.
* nClimGrid-Daily: January and May--October 1981 are independently byte-pinned,
  live-identity checked, and decoded. The six growing-season objects contain
  184 contiguous days. Full 1981--2019 acquisition is still pending.
* gridMET: the 2018 `pr` smoke file was acquired from the documented official
  distribution on 2026-08-26 (65,031,749 bytes; 365 verified daily steps;
  SHA-512 `503c9cf6...b5497bae`). Exact object identity, terms, decoded
  validation, and scientific limitations are now tracked in
  `data/provenance/gridmet_pr_2018.toml`; the ignored raw manifest records each
  execution. It remains a robustness input, not the primary trend product.
* Polygon primary: the acquired 2019 TIGER archive passed ZIP/schema/FIPS/CRS
  checks. Cuming County has 120 positive nClimGrid intersections, effectively
  complete polygon coverage, and area weights summing to one. A real 1981
  corn/soy feature panel was built cell-first and joined to four paired NASS
  practice-support rows; no relationship was estimated.
* CDL sensitivity: the exact 1,790,196,900-byte archive passed SHA-512 and all
  five ZIP-member checks. The Cuming window contains 706,394 corn and 582,110
  soybean pixels mapped with 100% nClimGrid coverage into 120 cells per crop.
  A retrospective-2017-mask feature smoke exists and is not historical crop-
  location evidence or a response estimate.
* Crop calendar: the exact NASS 2010 usual-dates PDF is acquired, checksummed,
  and visually audited. A tested parser preserves 130 state/crop source rows
  and expands 10,920 unique 1981--2022 calendar rows across 42 states and five
  crop classes. The selected engineering default uses floor midpoints of most-
  active planting/harvest boundaries; the published begin-to-end envelope is
  the broad sensitivity. Final causal calendar selection remains validation-
  dependent, and wheat classes cannot share one calendar.
* Irrigation numerator/denominator: exact 2012/2017/2022 Census series are
  acquired, checksummed, and audited for corn, soybean, and all-classes wheat.
  The 2017 primary selector has 1,014/706/420 numeric crop-share counties.
* Practice-specific yields: long regional paired panels exist (11,483 corn,
  6,294 soybean, and 18,831 wheat county-years), but coverage is not national.
* Hence: irrigation identification and a bounded real weather-panel
  construction now exist. Full multi-county/multi-year acquisition,
  preregistered model selection, and every yield-response estimate remain
  pending.
