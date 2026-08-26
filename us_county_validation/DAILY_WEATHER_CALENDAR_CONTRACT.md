# U.S. county daily weather and calendar contract

## Purpose and present boundary

This contract defines the reproducible bridge from selected NASS county
outcome support to daily precipitation and temperature features. The complete
corn/soy bridge now exists, but it is not an estimated causal climate-yield
relationship. No coefficient, damage, or SCC result is implied.

The primary historical weather candidate is now NOAA NCEI nClimGrid-Daily,
not gridMET alone. The reason is methodological: gridMET remains useful for
historical-exposure robustness, but its publisher cautions against using that
product by itself to infer changes in precipitation intensity or frequency
across input-source inhomogeneities. The U.S. county response still needs at
least one weather-product robustness comparison.

## Audited source state

| Input | Audited state | Permitted use |
|---|---|---|
| NOAA nClimGrid-Daily v1.0.0 | All 468 monthly 1981--2019 objects are acquired and independently content-pinned; each passes HTTP identity, local SHA-512, schema, units, day-label, and exact-calendar checks | Primary daily weather source; 419 county weights, 39 year partitions, and the exact 23,722-row corn/soy assembly pass downstream receipts |
| gridMET | 2018 precipitation object pinned and decoded | Historical weather-product robustness; not sole trend evidence |
| Daymet V4 | Official dataset/DOI identified; no exact local object acquired | Candidate 1 km robustness after license/object/size review |
| USDA NASS 2010 usual dates | Exact 51-page PDF acquired/checksummed and relevant tables visually inspected; tested parser preserves 130 state/crop definitions and emits 10,920 validated 1981--2022 primary/broad rows | Fixed state-level calendar construction, not realized annual phenology |
| USDA NASS CDL | Exact 2017 national archive acquired (1,790,196,900 bytes), SHA-512 and all five ZIP members validated; raster/class metadata inspected; bounded Cuming corn/soy weights built | Fixed crop-location sensitivity; before-2017 use is explicitly retrospective, never observed historical location |
| Census 2019 county TIGER/Line | Exact 79.2 MB archive acquired and validated; 3,233 unique GEOIDs; bounded Cuming polygon/nClimGrid overlay reconciles area and coverage | Full-period primary county-polygon overlay proxy after every historical NASS FIPS code passes a county-change audit |

Tracked source records are
`data/provenance/nclimgrid_daily_198101.toml`,
`data/provenance/nclimgrid_daily_1981_cuming_smoke.toml`,
`data/provenance/nass_field_crop_calendar_2010.toml`, and
`data/provenance/us_county_spatial_input_plan.toml`.

Authoritative sources:

* NOAA NCEI [nClimGrid-Daily product](https://www.ncei.noaa.gov/products/land-based-station/nclimgrid-daily), [user guide](https://www.ncei.noaa.gov/data/nclimgrid-daily/doc/nclimgrid-daily_v1-0-0_user-guide.pdf), and [dataset DOI](https://doi.org/10.25921/c4gt-r169).
* USDA NASS [Field Crops Usual Planting and Harvesting Dates](https://www.nass.usda.gov/Publications/Todays_Reports/reports/fcdate10.pdf).
* USDA NASS [CDL FAQ, metadata, coverage, and terms](https://data.nass.usda.gov/Research_and_Science/Cropland/sarsfaqs2.php).
* Census Bureau [2019 TIGER/Line counties](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.2019.html), [technical documentation](https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2019/TGRSHP2019_TechDoc.pdf), and [county-change reference](https://www.census.gov/programs-surveys/geography/technical-documentation/county-changes.1990.html).
* ORNL DAAC [Daymet V4 daily surface weather](https://doi.org/10.3334/ORNLDAAC/1840).

## Required construction order

For a nonlinear precipitation feature, averaging daily weather over a county
first is generally not equivalent to averaging farm/grid-cell features. The
pipeline therefore uses this order:

1. Select a declared crop calendar class and align each weather-grid cell's
   daily observations to the season and stages.
2. At the grid-cell/calendar-class level, construct seasonal and stage totals,
   normalized stage shares, timing centroid/concentration, wet-day occurrence,
   conditional wet-day intensity, consecutive dry days, Rx1day, Rx5day,
   temperature/heat bases, and registered interactions.
3. For the full-period primary route, apply county/nClimGrid polygon-
   intersection area weights and label the result a county-average proxy. For
   the separate CDL route, apply fixed crop-pixel weights to the same cell-
   first bases.
4. For an all-classes wheat outcome, retain winter-, spring-, and durum-wheat
   bases separately until independent fixed class-area shares exist.
5. Join one feature row to each county-outcome-crop-year support key.

The primary spatial formula for any already-constructed grid-cell basis
`B[g,k]` is:

`B[county,k] = sum_g(intersection_area[county,g] * B[g,k]) / sum_g(intersection_area[county,g])`.

The CDL sensitivity replaces intersection area with selected crop-pixel area
within each crop/calendar class:

`B[county,class,k] = sum_g(area[county,class,g] * B[g,k]) / sum_g(area[county,class,g])`.

Seasonal precipitation total is linear, but it follows the same ordering for
one auditable pipeline. CDD, Rx5day, wet-day intensity, timing concentration,
heat thresholds, and nonlinear response transforms must not be reconstructed
from county-mean daily weather and described as average farm exposure.

## Calendar design

The acquired NASS report is authoritative about its own date ranges. It says
that begin/end dates represent roughly 5/95 percent completion and that the
most-active range represents roughly 15/85 percent completion, based on 20
years of crop-progress information plus specialist knowledge.

The selected engineering default is a representative season from the floor
midpoint of the most-active planting range to the floor midpoint of the most-
active harvest range. A planting-begin through harvest-end envelope is the
wider-window sensitivity. Final causal-model calendar selection remains
validation-dependent. Annual Crop Progress timing is a separate realized-
timing/adaptation sensitivity; using it as the primary exposure could condition
on timing that responds to weather.

Equal-duration thirds can continue as an engineering diagnostic. A production
claim about vegetative, reproductive, or grain-fill stages requires a
crop-specific phenology source or an explicit and justified model choice.

There is no defensible single calendar for the current NASS all-classes wheat
outcome. The NASS source publishes winter, spring, and durum calendars
separately. The contract therefore requires class-specific feature bases and
independent class-area shares before aggregation to all-classes wheat.

## Spatial-route and time-support constraint

National CDL coverage begins in 2008. That supports an outcome-preceding 2017
crop mask for the 2018-2022 aggregate high-rainfed panel. It does not directly
observe crop locations throughout the 1981-2019 direct-practice panel.

This is a constraint on the crop-pixel sensitivity, not a blocker for the
selected full-period county-polygon primary proxy. That primary includes all
land and water in the legal county geometry and must therefore remain labeled
as a county-average measurement rather than average farm weather.

For the direct-practice panel, the defensible options are:

1. Restrict corn/soy crop-area-weighted estimation to the national-CDL era and
   report the lost county-year support.
2. Use a fixed 2008-2019 or 2017 crop mask retrospectively, label this as a
   measurement assumption, and test mask-vintage and crop-location stability.
3. Use a coarser independent circa-2000 crop map for earlier years as a
   sensitivity.

The all-classes wheat paired-practice support has no observations after 2007,
so option 1 cannot retain wheat. This is a real data-design decision, not a
missing value that code may silently fill. County-centroid weather can be
reported only as a diagnostic measurement-error comparison.

## County/FIPS gate

The five-digit NASS state-plus-county GEOID is preserved exactly. A fixed 2019
Census county geometry is only an overlay reference. Every outcome GEOID must
either be stable over its outcome years or have an explicit authoritative
county-change/crosswalk record. Unresolved county changes fail feature
eligibility; no obsolete or missing code is guessed.

## Executable schema gate

`validate_county_crop_weather_contract.py` is the four-table gate for the CDL
sensitivity: selected outcome support, county inventory/crosswalk, sparse
crop-pixel-to-weather-grid weights, and state/class/year calendars. It verifies five-digit GEOIDs,
county-state reconciliation, grid indices, unique cells, area denominators,
within-class weights, wheat-class shares, exact calendar coverage, paired
practice support, and false SCC-authorization flags. The county-polygon primary
builders apply their own source/profile, exact-area, coverage, operation-order,
and false-authorization gates. Every JSON output is an audit only.

Run the synthetic failure suite with:

```bash
.venv/bin/python us_county_validation/scripts/test_validate_county_crop_weather_contract.py
```

The test covers tampered weights, duplicate cells, out-of-grid indices,
invalid all-wheat calendar use, unresolved county changes, incomplete
irrigated/non-irrigated pairs, missing class calendars, and malformed FIPS.

Run the spatial/feature construction tests with:

```bash
.venv/bin/python us_county_validation/scripts/test_build_county_polygon_nclimgrid_weights.py
.venv/bin/python us_county_validation/scripts/test_build_county_nclimgrid_feature_smoke.py
.venv/bin/python us_county_validation/scripts/test_build_cdl_nclimgrid_crop_weights.py
.venv/bin/python us_county_validation/scripts/test_build_crop_weighted_nclimgrid_feature_smoke.py
.venv/bin/python us_county_validation/scripts/test_build_nass_usual_date_calendars.py
```

Acquire or revalidate the bounded NOAA smoke with:

```bash
.venv/bin/python us_county_validation/scripts/download_nclimgrid_smoke.py \
  --year 1981 --month 1
```

The full configuration and non-authorization boundary are frozen only as a
candidate schema in `config/us_county_daily_weather_contract.toml`.

The bounded real Cuming outputs remain under ignored `data/interim/us_county/`.
`compare_spatial_feature_smokes.py` verifies common crop-year, weather,
calendar, false-authorization, and practice-invariant feature support before
reporting polygon-versus-CDL feature differences. Its output is a spatial-
measurement audit, never a response estimate.
