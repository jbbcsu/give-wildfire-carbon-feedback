# National all-practice PDSI comparison route

This route attaches retrospective NOAA nClimDiv county PDSI windows to the
1981--2019 national NASS corn and soybean **all-practice** yield panel. It is a
data-construction route for later predictive comparison, not a rainfed-yield
panel, causal response estimate, damage function, or SCC input.

The executable route fails closed unless all of the following hold:

- every outcome remains labelled `all_practices` and comes from the locked
  national Quick Stats series;
- irrigation shares use the fixed-2017 vintage, and missing or suppressed
  shares remain missing rather than being set to zero;
- outcome state codes agree with the fixed-2019 TIGER geography gate, counties
  requiring unresolved historical-boundary review remain excluded, and the
  output retains the fixed-2019 county-envelope proxy caveat;
- NOAA county PDSI has exactly the same county support and state identity as
  the eligible outcomes, retains the publisher's 1931--1990 calibration and
  locked provenance, and completely covers every registered crop window; and
- candidate feature keys equal the eligible crop-county-year keys exactly.
  Direct precipitation, temperature, PET/heat, SPEI, and outcome columns are
  rejected, as are upstream response-estimation or SCC authorization flags.

PDSI is therefore a mutually exclusive historical moisture-stress
representation. A later comparison may fit PDSI *instead of* direct weather
or SPEI on identical outcome keys. It must not add their coefficients or
interpret predictive ranking as causal attribution. The fixed-2017
high-rainfed flags are sample definitions and do not change the aggregate NASS
outcome into an observed rainfed yield.

The synthetic invariant test is
`scripts/test_prepare_nass_national_all_practice_pdsi.py`. It includes
adversarial checks for irrigation relabelling or imputation, geography and
PDSI state mismatches, nonlocked share vintage, extra outcome-key support,
stacked moisture/weather predictors, outcome leakage, and authorization-flag
masking. It does not substitute for the hash-bound real-data audit emitted by
the full route.
