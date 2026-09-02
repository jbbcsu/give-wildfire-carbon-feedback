# nClimGrid county-estimator spatial sensitivity

Status: validated outcome-free weather-measurement sensitivity; not estimator
equivalence, route replacement, a yield response, damages, or SCC evidence.

The sample was fixed before its nine-county output in
`nclimgrid_estimator_spatial_sample_v1.toml`. It compares NOAA's official
nClimGrid-Daily county-area averages with the registered 2019 TIGER polygon-
weight proxy for June 2019 in nine geographically dispersed production
counties across Alabama, Arkansas, California, Idaho, Indiana, Iowa, Kansas,
Kentucky, and Nebraska. The comparison reads no yield outcomes and defines no
equivalence threshold.

All four variables retain the exact official 3,107-county support and all 30
days, producing 36 county-variable comparisons. The minimum defined daily
correlation is 0.999812. The largest absolute daily difference is 0.325871 mm
of precipitation in Adams County, Iowa (19003). Polygon-minus-official monthly
precipitation-total differences range from -0.830529 mm in Adams County to
+0.413524 mm in Cuming County, Nebraska (31039). Seven of nine precipitation
totals differ by at least 0.1 mm in absolute value.

The new spatial sample agrees with the earlier temporal synthesis that the two
estimators are close but not interchangeable. The registered polygon route is
retained as a historical county-average proxy; the official product remains a
source-level validation reference. Neither is relabeled as crop-pixel or
average-farm weather.

## Fixed seasonal-anchor expansion

Before evaluating additional cells, the same nine-county sample was frozen for
January, June, and December 2019, using only official county-average files that
had already been acquired. All 108 county-variable-month cells have complete
daily support and nonzero maximum differences. The minimum defined daily
correlation is 0.999758; polygon-minus-official monthly rainfall differences
range from -0.830529 to +0.619192 mm, and the maximum daily absolute difference
remains 0.325871 mm. The expansion reads no yield outcome, defines no
equivalence threshold, and does not replace the registered polygon route or
authorize response, damage, or SCC use.
