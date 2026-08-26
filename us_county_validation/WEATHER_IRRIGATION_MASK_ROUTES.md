# U.S. county climate, irrigation, and crop-area routing

## Bounded gridMET smoke

The first acquired weather input is deliberately one gridMET full-CONUS daily
NetCDF file: precipitation short name `pr`, calendar year 2018. The year is
inside the real locked 2018–2022 NASS corn-grain outcome support. The official
Climate Toolbox documentation identifies gridMET as a CONUS daily gridded
meteorological product at approximately 4 km from 1979 onward and identifies
the Northwest Knowledge Network full-NetCDF distribution and THREDDS subset
access route.

The executable fetch is:

    .venv/bin/python us_county_validation/scripts/download_gridmet_smoke.py       --variable pr --year 2018

The downloader refuses variables outside pr/tmmn/tmmx, one year per run, and
files over 100 MiB. It pins HTTP content length/ETag/last-modified when
provided, validates a full 365/366-day NetCDF time axis and latitude/longitude
coordinates, and writes SHA-512 provenance to the gitignored raw-input tree.
It does **not** compute county averages, join a yield, or authorize an SCC
input. The smoke is only a daily-file availability/integrity check.

Sources:

* Climate Toolbox, [gridMET past-weather data](https://climatetoolbox.org/data/past-weather-data).
* Abatzoglou (2013), [gridMET construction](https://doi.org/10.1002/joc.3413).

## Crop-specific irrigation-share gate

The authoritative initial route is USDA NASS Census of Agriculture county
records, retrieved through the documented Quick Stats service only after a
bounded series-discovery/count check. For each crop (beginning with corn for
grain), request two otherwise identical county records:

| Quantity | Required discovery target |
|---|---|
| Irrigated crop harvested area | `source_desc=CENSUS`; crop; `statisticcat_desc=AREA HARVESTED`; `agg_level_desc=COUNTY`; irrigation-status domain/category identifying irrigated acres; `unit_desc=ACRES` |
| Total crop harvested area | Same crop/statistic/geography/unit and census reference period, but total domain/category |

The actual domain/category labels must be obtained from NASS parameter values
and frozen in the manifest; do not assume that a label found for another crop
or release applies. The static share is
`irrigated_acres / total_harvested_acres`; it selects high-rainfed counties
under preregistered thresholds but does not prove every county-year outcome is
non-irrigated. Fail the gate if either series has incompatible year/reference
period, non-county geography, duplicate keys, suppressed denominator, negative
values, or a share outside [0,1] after documented rounding tolerance.

The 2023 Farm and Ranch Irrigation Survey documents crop-specific irrigated
harvested acres as a concept but its published tables should not be assumed to
provide the county panel needed here. It is evidence for the definition and a
cross-check, not a substitute for county-level numerator/denominator records.

Sources:

* USDA NASS [Quick Stats/developer information](https://www.nass.usda.gov/developer/).
* USDA NASS [2023 Farm and Ranch Irrigation Survey](https://data.nass.usda.gov/Publications/AgCensus/2022/Online_Resources/Farm_and_Ranch_Irrigation_Survey/index.php).

## Crop-area weather-weight route

The primary spatial weight is the annual USDA NASS Cropland Data Layer (CDL),
not county centroids. For every NASS outcome year 2018–2022, acquire the
matching annual CDL raster from NASS CroplandCROS/National Download, preserve
the release metadata/checksum, and use the corn class defined by that release.
Intersect selected crop pixels with official county polygons and gridMET cell
polygons. Compute daily county weather as crop-area-weighted gridMET values:

`W[county, day] = sum(cell intersection crop area * W[cell, day]) / sum(cell intersection crop area)`.

Perform the spatial work in an equal-area/geodesic area treatment, record the
county boundary vintage, and fail cells/counties with zero selected crop area.
Only then create crop-stage total, wet-day, dry-spell, heavy-rain, and
temperature features. A plain county-average/centroid series may be a labeled
diagnostic but never the primary exposure.

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
* gridMET: the 2018 `pr` smoke file was acquired from the documented official
  distribution on 2026-08-26 (65,031,749 bytes; 365 verified daily steps;
  SHA-512 and upstream identity are in the ignored raw manifest). No
  crop-area-weighted county exposure exists.
* CDL/county intersections: not acquired or computed.
* Irrigation numerator/denominator: not acquired or series-locked.
* Hence: no high-rainfed sample and no county yield-response estimate.
