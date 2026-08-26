# Preliminary U.S. direct-practice precipitation associations

## Purpose and status

This diagnostic asks whether historical precipitation quantity and a simple
within-season timing contrast are associated with county corn and soybean
yields after absorbing county fixed effects, state-by-harvest-year fixed
effects, and stage-mean temperature controls. It uses the direct NASS
irrigated/non-irrigated outcome screen and the validated nClimGrid-Daily
exposures. The registered result is a **historical association diagnostic**,
not a causal response, nationally representative estimate, damage function,
or SCC input.

The sample ends in 2018 because direct-practice reporting collapses to only
three corn and one soybean county levels in 2019. Results are fit separately
by crop and practice. Standard errors are clustered by county. The corn
primary form is seasonal precipitation quantity; the soybean primary form
adds early- and middle-season precipitation shares, with the late-season
share omitted. This choice was frozen from the earlier outer-holdout
predictive screen before coefficients were estimated.

## Registered preliminary results

For non-irrigated corn (7,013 county-years in 361 counties), the quantity-only
model associates an additional 100 mm of seasonal precipitation with fitted
yield differences of +11.07%, +7.72%, and +3.59% at the 25th, 50th, and 75th
percentiles of observed seasonal precipitation (323, 401, and 500 mm). Their
county-clustered normal 95% intervals are [9.74%, 12.41%], [6.78%, 8.67%], and
[2.86%, 4.32%]. The corresponding irrigated-corn associations are +0.04%,
-0.41%, and -0.98%, with intervals [-0.50%, 0.59%], [-0.81%, -0.01%], and
[-1.39%, -0.58%].
The contrast between non-irrigated and irrigated results is qualitatively
consistent with irrigation buffering rainfall exposure, but it is not an
identified irrigation treatment effect.

For non-irrigated soybean (4,844 county-years in 255 counties), the registered
quantity-plus-timing model associates an additional 100 mm with +7.44%,
+4.46%, and +1.11% fitted yield differences at 325, 397, and 481 mm. A partial
model contrast that moves 10 percentage points of seasonal rainfall from the
late to the middle crop-calendar window, holding total rainfall, early share,
stage temperature, fixed effects, and other registered regressors constant,
is +4.73% [3.63%, 5.84%]. The quantity intervals are [6.09%, 8.81%], [3.44%,
5.50%], and [0.26%, 1.98%]. The same point contrasts for irrigated soybean are
+0.32%, -0.05%, -0.49%, and -0.21%; all four intervals include zero.

The secondary corn timing model produces a positive middle-versus-late timing
contrast, but timing failed the pre-existing geographic stability gate for
corn. It is therefore not promoted over the parsimonious quantity model.
This distinction prevents a statistically large in-sample timing coefficient
from overriding adverse outer-holdout evidence.

## Interpretation limits and next gates

- County and state-by-year fixed effects remove important time-invariant local
  differences and common state-year shocks, but do not eliminate all
  time-varying confounding or measurement error.
- The timing contrast is partial: it does not mechanically update dry-spell,
  wet-day-intensity, Rx1day, or Rx5day measures that would co-move in a fully
  specified rainfall sequence.
- Fixed historical crop-calendar windows are exposure summaries, not observed
  annual management or phenology. CO2 fertilization, endogenous adaptation,
  irrigation quantities, and input changes are not separately identified.
- Direct-practice NASS reporting is regional and selected. Missing county
  outcomes are never imputed, and the results must not be extrapolated to the
  United States or the globe without an explicit transport design.
- Climate-change attribution is a separate step. These estimates do not yet
  say how greenhouse-gas emissions change rainfall quantity, timing, or
  drought, and they cannot yet be multiplied into an SCC calculation.

A clean-room implementation independently reconstructs the sample and fixed-
effect projection, solves the within model by QR, and reforms the clustered
sandwich. It agrees across 324 reported numeric fields within `1.04e-13`.
The next empirical gates are alternative heat controls, balanced-support and
drought-family comparisons, and a pre-specified design for translating
climate-model exposure changes through a defensible causal response rather
than these descriptive associations.

## Reproduction

The locked contract is
`us_county_validation/us_direct_practice_precipitation_association_v1.toml`.
The estimator and unit test are
`us_county_validation/scripts/estimate_us_direct_practice_precipitation_association.py`
and
`us_county_validation/scripts/test_us_direct_practice_precipitation_association.py`.
The aggregate result is
`data/provenance/us_direct_practice_precipitation_association_20260826.json`
(SHA-256 `4f39079e88103c9fbe14026b33d2741a942e24388a9dfe863845fea3b4100e6e`).
The independent validation receipt is
`data/provenance/us_direct_practice_precipitation_association_independent_validation_20260826.json`
(SHA-256 `e7b259d840f95803e10d8037e3eb75a91c520952247f1a92b89aee943e7d0166`).
No row predictions are emitted.
