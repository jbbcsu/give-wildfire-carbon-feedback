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

## July 2000 seasonal stress test

The identical county/variable comparison was repeated for July 2000 to test a
hot summer month without changing counties after observing results. All four
official files again share exact 3,107-county support and 31 finite daily
values. Daily correlations are at least 0.99994 where variation permits a
correlation. Cuming's polygon-minus-source monthly precipitation difference is
+0.993 mm; Fresno reports zero precipitation under both estimators. Mean
absolute temperature differences are 0.0086--0.0123 C in Cuming and
0.0278--0.0416 C in Fresno. The maximum daily precipitation difference is
0.6564 mm in Cuming.

The summer check supports close bounded agreement while showing that absolute
rainfall differences can be larger than in the April smoke. It still does not
establish nationwide, seasonal, or boundary-vintage equivalence.

## July 2012 drought-month stress test

The same two counties and four variables were retained for July 2012, a dry
summer month selected without reference to yield outcomes. All four official
files again have exact common support for 3,107 counties and 31 finite daily
values. Cuming County reports 0.0900 mm of official monthly precipitation
versus 0.0977 mm from the polygon estimator; Fresno reports 0.0600 versus
0.0706 mm. Temperature correlations exceed 0.99999. Fresno's precipitation
correlation is lower (0.9853) because both estimators are near zero, while its
maximum absolute daily precipitation difference is only 0.0056 mm.

This drought-month check strengthens the evidence that the routes are closely
aligned in the two fixed counties, but the nonzero monthly differences and
bounded support still reject a declaration of estimator equivalence. It does
not select a weather route or authorize a response, damage, or SCC input.

## February 2000 leap-month stress test

An outcome-blind February 2000 check retains the same two counties and four
variables and adds the 29-day leap-year calendar edge. All official and polygon
series contain exactly 29 finite days. Correlations are at least 0.999988.
Polygon-minus-official monthly precipitation is +0.2838 mm in Cuming and
+0.6589 mm in Fresno; the largest daily difference across variables is
0.1342 in the variable's native unit. This closes a leap-day decoding check
but again rejects exact estimator equivalence and authorizes no response,
damage, or SCC input.

## January 2019 recent-boundary check

An outcome-blind January 2019 check retains the same counties and variables
near the end of the acquired historical panel. All official files again have
exact 3,107-county support and both estimators retain 31 finite days. Polygon-
minus-official monthly precipitation is +0.0441 mm in Cuming and +0.4057 mm
in Fresno. Precipitation correlations are 0.99976 and 0.999997, respectively;
the small Cuming total makes its correlation more sensitive to tiny daily
differences. The nonzero differences again reject estimator equivalence and
authorize no response, damage, or SCC input.

## Reproduction and evidence boundary

The executable is
`scripts/compare_nclimgrid_county_average_estimators.py`; synthetic failures
are covered by
`scripts/test_compare_nclimgrid_county_average_estimators.py`. Exact NOAA
URLs and hashes, the local grid and polygon-weight hashes, and all metrics are
recorded in
`../data/provenance/us_nclimgrid_county_average_estimator_comparison_199004_20260830.json`
and
`../data/provenance/us_nclimgrid_county_average_estimator_comparison_200007_20260830.json`,
with the drought-month extension in
`../data/provenance/us_nclimgrid_county_average_estimator_comparison_201207_20260831.json`
and the leap-month extension in
`../data/provenance/us_nclimgrid_county_average_estimator_comparison_200002_20260901.json`,
with the recent-boundary extension in
`../data/provenance/us_nclimgrid_county_average_estimator_comparison_201901_20260901.json`.

This is a weather-measurement comparison only. It does not use yield outcomes,
select an estimator, estimate a response, calculate damages, or authorize an
SCC input.
