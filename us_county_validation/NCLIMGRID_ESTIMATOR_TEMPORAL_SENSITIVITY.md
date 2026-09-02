# nClimGrid county-estimator temporal sensitivity

Status: fixed-month measurement sensitivity; not estimator equivalence, a
climate-yield response, damages, or SCC evidence.

This audit binds the seven existing official-county-average versus registered
polygon-weight comparisons into one fail-closed series: April 1990; February
and July 2000; July 2012; and January, June, and December 2019. Each receipt
must retain the same two predeclared counties (Cuming County, Nebraska, and
Fresno County, California), four daily variables, 3,107-county official source
support, exact month identity, and explicit non-replacement status.

The executable reports the minimum daily correlation and maximum daily
difference/RMSE for every county-variable pair, plus monthly-total rainfall
differences and the stability of mean-difference signs. Nonzero differences in
any month continue to reject a general equivalence claim. The two-county,
seven-month selection is a measurement check only and cannot validate national
or crop-area-weighted weather exposure.

Run `us_county_validation/scripts/audit_nclimgrid_estimator_comparison_series.py`
over the seven checksum-bound receipts. The result is stored in
`data/provenance/us_nclimgrid_county_average_estimator_comparison_series_20260901.json`.

## Result

All 56 fixed county-variable-month cells pass the receipt and support gates.
Fifty-five contain nonzero maximum differences. The one zero-difference cell
is Fresno precipitation in July 2000, where both daily series are constant
zero and correlation is therefore undefined. The minimum defined correlation
is 0.985332, for near-zero Fresno rainfall in July 2012. Maximum absolute
monthly rainfall-total differences are 0.6589 mm in Fresno and 0.9926 mm in
Cuming. Cuming temperature mean-difference signs are stable and negative over
all seven months, while Fresno temperature signs and both rainfall signs vary.
This supports close bounded agreement but rejects interchangeability.

## Fixed nine-county 2019 expansion

A separate preregistered expansion holds the previously selected nine-state
county sample fixed and adds April and September to the January, June, and
December anchors before acquiring the official comparison series. All 180
county-variable-month cells have complete daily support. The minimum defined
daily correlation is 0.999425 and the largest absolute daily difference is
0.8486 in source units. Polygon-minus-official monthly precipitation totals
range from -2.7068 to +1.2868 mm; 179 of 180 cells have a nonzero maximum
difference.

The larger bounded sample reinforces close agreement while continuing to
reject exact interchangeability. It reads no outcomes, does not replace the
registered polygon route, and supplies no relationship, damage, or SCC
estimate. The checksum-bound audit is
`data/provenance/us_nclimgrid_estimator_spatiotemporal_expansion_2019_20260902.json`.
