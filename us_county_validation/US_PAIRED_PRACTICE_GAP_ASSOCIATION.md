# U.S. paired-practice yield-gap association

Status: historical county validation diagnostic only; not causal, nationally
representative, a global transfer parameter, a damage function, or an SCC
input.

The direct-practice NASS panel contains exact irrigated/non-irrigated yield
pairs under a shared county-level nClimGrid exposure proxy. The paired-gap
diagnostic collapses each county-crop-year pair to
`log(irrigated yield) - log(non-irrigated yield)` and fits the same registered
quantity and quantity-plus-timing forms with county and state-by-year fixed
effects and county-clustered uncertainty.

This asks whether the historical irrigated/non-irrigated yield ratio varies
systematically with the shared weather exposure among the selected reporting
counties. It does not identify an irrigation treatment effect: practice
selection, crop management, soil, technology, reporting support, and other
time-varying differences may remain. The shared county exposure is not a
practice-specific crop-pixel weather measure.

The executable requires the exact hash-bound 1981--2018 panel, complete pairs,
identical weather features within every pair, positive yields, finite designs,
and the closed causal/damage/SCC gates. It emits aggregate coefficients and
predeclared contrasts but no row predictions. The machine-readable result is
`data/provenance/us_paired_practice_gap_association_20260827.json`.

The real hash-bound sample contains 11,857 paired county-crop-years: 7,013
corn pairs across 361 counties and 4,844 soybean pairs across 255 counties.
At the crop-specific median seasonal rainfall, the fitted change in the
irrigated-to-non-irrigated yield ratio for 100 mm more precipitation is
-7.55% in the corn quantity form and -7.63% in the quantity-plus-timing form;
the corresponding soybean values are -4.05% and -4.32%. In the timing forms,
moving ten percentage points of rain from stage 3 to stage 2 while holding
registered controls fixed is associated with ratio changes of -4.12% for corn
and -4.72% for soybeans. These conditional historical associations may reflect
differential water buffering, but they are not causal irrigation effects and
must not be transferred to global crop damages.

An independent algebraic audit requires every paired-gap coefficient to equal
the irrigated coefficient minus the non-irrigated coefficient from the prior
separate-practice fits on the identical paired support. It does not subtract
the separate standard errors, because that would omit their cross-practice
covariance; uncertainty is taken from the county-clustered paired-gap fit.
All 36 coefficient identities pass, with maximum absolute disagreement
`3.33e-16`.

Reproduce with:

```bash
./.venv/bin/python \
  us_county_validation/scripts/test_us_paired_practice_gap_association.py

./.venv/bin/python \
  us_county_validation/scripts/estimate_us_paired_practice_gap_association.py

./.venv/bin/python \
  us_county_validation/scripts/validate_us_paired_practice_gap_association_independent.py
```
