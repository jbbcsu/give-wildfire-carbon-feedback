# nClimGrid county-average estimator comparison

## Bounded comparison

The official NOAA county-area-average route and the registered 2019 TIGER
polygon-weight route were compared without outcomes for April 1990. The fixed
counties were Cuming County, Nebraska (GEOID 31039), and Fresno County,
California (GEOID 06019). All four official files contain the same 3,107
counties and 30 finite daily values for precipitation, mean temperature,
minimum temperature, and maximum temperature.

The polygon calculation uses the exact already-registered nClimGrid grid file
and the existing county weight partitions. It does not infer or alter either
spatial estimator.

## Results

Daily agreement is close in this bounded month but not exact. Across the eight
county-variable comparisons, daily correlations are at least 0.99983. The
largest absolute daily difference is 0.1345 mm for precipitation and 0.0717 C
for temperature. Polygon-minus-source monthly precipitation totals are +0.1805
mm in Cuming and +0.0265 mm in Fresno. Mean absolute temperature differences
range from 0.0110 to 0.0142 C in Cuming and 0.0412 to 0.0550 C in Fresno.

These results support continuing a preregistered equivalence audit across
months, boundary vintages, and counties. They do not establish general
equivalence and do not authorize replacing the registered polygon route.

## Reproduction and evidence boundary

The executable is
`scripts/compare_nclimgrid_county_average_estimators.py`; synthetic failures
are covered by
`scripts/test_compare_nclimgrid_county_average_estimators.py`. Exact NOAA
URLs and hashes, the local grid and polygon-weight hashes, and all metrics are
recorded in
`../data/provenance/us_nclimgrid_county_average_estimator_comparison_199004_20260830.json`.

This is a weather-measurement comparison only. It does not use yield outcomes,
select an estimator, estimate a response, calculate damages, or authorize an
SCC input.
