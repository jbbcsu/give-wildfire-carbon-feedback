# Aggregate-yield irrigation estimand

## Scope and boundary

GDHY supplies one crop-season-grid-year yield, not separate rainfed and
irrigated yields. MIRCA-OS supplies fixed baseline harvested areas, not yields,
production, revenue, or irrigation effectiveness. The production observation
equation must therefore retain one GDHY outcome and must not represent its
coefficients as directly observed rainfed or irrigated yield responses.

This note defines the estimand and feature-allocation order. It does not fit a
response, establish causal identification, or authorize a damage or SCC input.

## Indices and fixed weights

Let (i) index a 0.5-degree grid cell, (c) a crop season, (t) a harvest
year, and (r\in\{rf,ir\}) a rainfed or fully irrigated calendar regime. Let
(Y_{ict}) be the single positive GDHY yield in tonnes per hectare and
(W_{ictr}) the regime-specific, crop-calendar-aligned weather history. Define

\[
s^0_{icr}=\frac{A^0_{icr}}{A^0_{ic,rf}+A^0_{ic,ir}},\qquad
\sum_r s^0_{icr}=1,
\]

where (A^0) is the independently sourced, modeled MIRCA harvested-area
inventory from one declared vintage. Each sensitivity run fixes one vintage
across all outcome years.
Missing crop-grid support excludes the complete outcome; shares are never
filled from the outcome or renormalized across missing regimes.

## Proposed aggregate reduced-form equation

The primary estimand is the crop-specific response of the observed aggregate
log yield to an area-weighted vector of regime-specific response bases:

\[
\log Y_{ict}=\alpha_{ic}+\lambda_{ct}
 +\beta_c'Z_{ict}+\varepsilon_{ict},\qquad
Z_{ict}=\sum_r s^0_{icr}B_c(W_{ictr}).
\]

(alpha_{ic}) absorbs time-invariant grid/crop productivity and
(lambda_{ct}) absorbs flexible crop-year shocks. (B_c(\cdot)) contains
pre-registered crop-stage functions of temperature, precipitation amount,
within-season timing, dry spells, wet extremes, and their interactions. The
common `beta_c` across the two regime contributions is the recommended primary
identifying
restriction, not evidence that rainfed and irrigated crops have identical
structural responses. The equation is an aggregate reduced form on log yield;
it is not an exact decomposition of unobserved regime yields.

For first-difference diagnostics, the corresponding equation is

\[
\Delta\log Y_{ict}=\Delta\lambda_{ct}
 +\beta_c'\sum_r s^0_{icr}\Delta B_c(W_{ictr})
 +\Delta\varepsilon_{ict}.
\]

The fixed shares commute with differencing. A time-varying share would mix
weather response with adaptation and is prohibited in the historical primary
estimand.

## Nonlinear operations occur before weighting

Every nonlinear daily statistic, transform, spline, threshold, and interaction
must be evaluated within a regime and crop-stage window before area weighting:

\[
Z^{(k)}_{ict}=\sum_r s^0_{icr} B^{(k)}_c(W_{ictr}).
\]

It is invalid to average primitive weather first and then transform it. For
example,

\[
\sum_r s_r\log(1+P_r)\ne
\log\!\left(1+\sum_r s_rP_r\right),
\]

and

\[
\sum_r s_r[T_r\log(1+P_r)]\ne
\left(\sum_r s_rT_r\right)
\left(\sum_r s_r\log(1+P_r)\right).
\]

The right-hand interaction introduces cross-regime terms such as rainfed
temperature multiplied by irrigated precipitation. Consecutive dry days,
Rx1day, Rx5day, threshold degree days, drought indices, and spline columns are
also nonlinear objects and must be constructed separately within each regime.
Only genuinely linear basis columns commute with weighting.

`scripts/allocate_irrigation_response_basis.py` implements the required
season/stage basis-before-weighting order for the minimal predictive
diagnostic. Its basis is not the complete or frozen production feature set.
The output omits primitive precipitation and is accepted only by the
evaluator's explicit contract-aware prebuilt-basis mode, which consumes the
supplied columns without overwriting them. Primitive-weather mode rejects the
same panel. Adding timing, wet-day, spline, threshold, Rx5day, heat, or drought
terms requires a new versioned contract and a synthetic order-of-operations
test.

## What is and is not identified

One aggregate outcome cannot nonparametrically identify two latent regime
yields. In particular, fixed MIRCA shares plus GDHY alone do not identify
rainfed and irrigated yield intercepts, their baseline yield ratio, irrigation
water supply or reliability, or unrestricted regime-specific response
functions. Cell fixed effects also absorb any time-invariant weighted regime
intercepts.

The primary common-slope equation is identified only from within-cell changes
in the weighted basis, conditional on the fixed-effects and climate controls.
It requires pre-estimation rank, condition-number, overlap, influence, spatial
dependence, and blocked-holdout checks. Those checks diagnose support; they do
not make historical weather variation exogenous or establish causality.

A secondary irrigated-deviation design may add

\[
\gamma_c'[s^0_{ic,ir}B_c(W_{ict,ir})]
\]

to the common component. It is admissible only if pre-registered water-related
terms have independent within-sample variation and the augmented design passes
rank, conditioning, interior-share support, spatial holdout, temporal holdout,
and coefficient-stability gates. Even then, (gamma_c) is an aggregate
contrast parameter, not a directly observed irrigated-yield effect. If these
gates fail, irrigation attenuation must be imported transparently from an
independent empirical or process-model source or treated as a bounded modeling
choice; it cannot be recovered by duplicating GDHY outcomes.

## Area, production, and revenue weights

Harvested-area shares are the appropriate physical weights for an aggregate
yield in tonnes per hectare when the aggregate represents total production
divided by total harvested area. On a log-change scale, however, the exact
first-order weights on latent regime-specific proportional yield changes are
baseline production shares,

\[
\pi^0_{icr}=\frac{A^0_{icr}y^0_{icr}}
 {\sum_q A^0_{icq}y^0_{icq}},
\]

not area shares unless baseline regime yields are equal. GDHY and MIRCA do not
supply (y^0_{icr}), so production shares must not be fabricated. The primary
log-yield equation therefore treats area shares as observable exposure weights
in an aggregate reduced form and reports the equal-baseline-yield implication
explicitly.

Revenue or crop-value weights do not belong in the yield observation equation.
They combine prices with production and are reserved for the later,
fixed-baseline welfare aggregation. Using them during response estimation and
again during welfare aggregation would change the physical estimand and risk
double weighting.

## Pre-registered sensitivity benchmarks

1. **Primary:** fixed-2000 MIRCA harvested-area shares, basis before weighting,
   one outcome, crop-specific common regime slope.
2. **Vintage:** repeat the complete model separately with 2005, 2010, 2015,
   and 2020 shares, each fixed over all outcome years.
3. **Outcome scale:** estimate a level-yield specification with the same
   area-weighted bases. Under additive common-slope regime yield functions,
   area aggregation is exact; compare implied proportional impacts with the
   primary log specification.
4. **Rainfed-calendar benchmark:** retain one aggregate outcome and use only
   rainfed-calendar features. Label this a benchmark, not a rainfed yield
   estimate or the all-area primary result.
5. **Irrigation heterogeneity:** use either the gated irrigated-deviation design
   or externally calibrated attenuation values. Report weak-identification and
   support diagnostics; do not select attenuation from SCC magnitude.
6. **Production weights:** run only if an independent, crop-grid, regime-specific
   baseline-yield source passes provenance and compatibility checks. Otherwise
   record the benchmark as unavailable.
7. **Order-of-operations diagnostic:** quantify the difference between
   basis-before-weighting and weather-before-transforming, but never promote
   the latter to a production response.

All variants preserve one row per GDHY crop-grid-year outcome. None becomes a
causal damage function or SCC input until the response, validation, projection,
and accounting gates elsewhere in the project are complete.
