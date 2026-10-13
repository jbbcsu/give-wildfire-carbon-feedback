# U.S. precipitation--agriculture two-stage design memo

## Decision and claim boundary

The U.S. evidence should be organized as a Qiu-et-al.-style linked chain, but
the two empirical stages must remain separately estimated and separately
gated:

1. **Stage 1: climate forcing -> crop-season precipitation or drought.**
2. **Stage 2: precipitation or drought -> county yield.**

The current artifacts support historical associations, predictive diagnostics,
and descriptive pattern transports. They do not identify a causal yield
response to climate change. No current result is authorized as a national
yield effect, damage function, welfare effect, or SCC input.

The strongest fully gated stage-2 cell is the direct-practice,
non-irrigated-corn seasonal-PDSI contrast at the median reference value: a
one-unit PDSI decrease is associated with a 4.30% yield decrease, with a
500-km spatial interval of 3.57% to 5.02% lower yield. It passes the frozen
spatial, leave-state, terminal-period, and preidentified-influence gates. It
still is not causal, nationally representative, or composable with future
climate because no validated climate-to-future-PDSI stage exists.

The direct-rainfall linked-chain route is not promotable either. Its existing
historical quantity response does not pass the full geographic and temporal
stability battery, while the three available climate patterns are not a
homogeneous validated ensemble and disagree in sign across most counties.

## Formal estimands

### Stage 1: climate to moisture

For county or weather cell (c), crop calendar (k), climate model (m),
member (r), scenario (s), and forcing increment or future window (h),
estimate or construct

\[
\Delta W_{ckmrs}(h) = g(\text{daily climate}_{ckmrs,h})
                      - g(\text{historical climate}_{ckmr}),
\]

where (g(\cdot)) yields one prespecified moisture family:

- seasonal rainfall quantity;
- rainfall distribution, dry-spell, and extreme features; or
- a physically constructed drought index such as PDSI or SPEI.

Direct precipitation and PDSI/SPEI are competing families. A drought index is
not added to a direct-rainfall regression as another precipitation channel.
Temperature covariates and the temperature component of a water-balance index
must be disclosed to avoid calling PDSI a precipitation-only exposure.

Stage 1 retains model, member, scenario, spatial support, calendar, and
historical-reference identities. Equal-GCM summaries may follow
model-specific results but may not conceal disagreement. Required gates are:

- historical comparison with an independently constructed NOAA product on
  frozen counties and calendar windows;
- multiple counties spanning the eventual outcome support;
- model/member holdouts or a genuinely external published pattern;
- temporal-window and boundary/calendar sensitivities;
- finite area-weighted features and exact rainfall-component reconciliation;
- no climate-model weighting using crop outcomes.

Free-running historical GCM years are compared as distributions, not scored
as paired-year forecasts. A future PDSI stage additionally requires a frozen
water-balance construction, not a direct substitution of rainfall change for
PDSI change.

### Stage 2: moisture to yield

For county (c), harvest year (t), crop (j), and irrigation practice
(p\), the historical response family is

\[
\log Y_{ctjp} = \alpha_c + \gamma_{s(c),t}
              + f_W(W_{ctj}) + f_T(T_{ctj}) + \varepsilon_{ctjp}.
\]

The primary direct-practice design fits irrigated and non-irrigated outcomes
separately on identical exposure support. County fixed effects and
state-by-year fixed effects remain common. The candidate moisture families are
mutually exclusive:

- quadratic total seasonal precipitation;
- an outcome-blind, leverage-qualified distribution extension; or
- quadratic seasonal PDSI/SPEI.

The existing corn distribution extension remains ineligible because its
outcome-blind leverage gate failed. It cannot be repaired by deleting the
preidentified 2011 Texas observation.

Every reported contrast requires county CR1 inference plus the frozen 250-km
and 500-km spatial covariance sensitivities. Promotion also requires:

- leave-one-state-out DFBETA and sign gates;
- a separate 2012--2018 terminal-period fit versus 1981--2011 development;
- preidentified row/county influence checks;
- held-out predictive improvement for model-family selection;
- adequate county, state, and practice support without outcome-based deletion.

Passing these gates establishes a stable historical association or predictive
representation, not causality. A causal label requires a separately defended
identification design and cannot be inferred from fixed effects and spatial
standard errors alone.

## Linked-chain composition rule

A stage-1 draw may enter a stage-2 response only when its moisture definition,
units, crop calendar, spatial aggregation, and support match the historical
response. The chain must propagate climate-model identity and stage-2
coefficient covariance. It must not combine:

- direct rainfall changes with a PDSI response;
- monthly-mean rainfall patterns with daily-extreme coefficients;
- all-practice low-irrigation proxies with directly reported non-irrigated
  yields without a labeled sensitivity;
- selected-sample results with national acreage, production, or welfare
  weights without a separate coverage and weighting design.

The chain is reportable only if both stage gates pass. A strong stage-2 PDSI
association with no stage-1 PDSI projection remains unlinked; a stage-1
rainfall pattern paired with an unstable quantity response remains a
structural sensitivity.

## Existing evidence inventory

| Evidence | Exact support/result | Permitted use |
|---|---|---|
| Direct-practice corn quantity/PDSI response | 14,026 rows, 7,013 paired exposures, 361 counties, 10 states, 1981--2018; practice strata fit separately | Historical selected-sample association only |
| Non-irrigated corn, median PDSI contrast | -4.30% for a one-unit PDSI decrease; 500-km interval [-5.02%, -3.57%]; spatial, leave-state, terminal, and influence gates pass | Strongest stage-2 cell; noncausal and unlinked |
| Non-irrigated corn, median +100-mm quantity contrast | +7.72%; 500-km interval [5.96%, 9.51%], but leave-state DFBETA is 2.10 and terminal standardized difference is 3.15 | Unstable historical association; do not transport |
| Irrigated corn, median quantity contrast | -0.41%; 500-km interval [-1.01%, 0.19%] | Not spatially robust |
| National all-practice low-irrigation PDSI proxy | 15,660 corn rows, 424 counties, 28 states; PDSI -2 versus 0 is -8.32% and spatially robust; temporal gate passes but leave-state DFBETA is 1.40 | Broad proxy sensitivity; not direct rainfed yield and not promoted |
| Corn/soy first-difference predictive audit | 20,228 changes; non-irrigated-corn seasonal PDSI beats quantity in all five eligible development states and in terminal/extreme tests | Model-family predictive evidence, not a causal coefficient |
| Sorghum/cotton geographic predictive audit | 168 state-fold records; among 15 common non-irrigated cross-crop comparisons, seven have opposite improvement signs | Descriptive regional instability; no welfare winner/loser interpretation |
| Published PEEPS MPI SSP5-8.5 rainfall pattern | Mean crop-season slope -25.20 mm/K across the 361 selected counties; 349 negative, 12 positive | One-model published stage-1 structural pattern |
| Published plus GFDL/IPSL project patterns | Equal-county means are -25.20, +3.68, and -5.66 mm/K; only 84 of 361 counties share a nonzero sign across all three | Structural sensitivity, not a validated probability-weighted ensemble |

Machine sources are the hash-bound corn spatial receipt, independently audited
competing-moisture diagnostic, national PDSI validation, and independently
validated additional-crop heterogeneity audit under `data/provenance/`.

## Reproducible state-support diagnostics

The new outputs summarize existing fitted artifacts; they perform no new
outcome regression.

- `US_STAGE2_CORN_STABILITY_GATES_20261013.csv` contains all 12 frozen
  practice/family/reference-quantile cells and the separate spatial,
  leave-state, terminal, and influence gates. Three cells pass all historical
  association gates; every causal, damage, and SCC gate remains false.
- `US_TWO_STAGE_STATE_DIAGNOSTICS_20261013.csv` contains 20 state-practice
  summaries across the three existing rainfall patterns. These are
  state-support pattern transports, not state-specific fitted effects.

Only 4 of 20 state-practice rows have the same nonzero climate-slope sign
across all three patterns; only 3 of 20 have the same nonzero transported-yield
sign. Zero rows are promoted because the stage-1 multi-model gate and the
stage-2 all-contrast quantity-stability gate are both closed. Several state
rows also have very small county support (one county for Oklahoma and three
for Delaware), reinforcing the diagnostic-only interpretation.

The hash-bound receipt is
`../data/provenance/us_two_stage_regional_heterogeneity_20261013.json`; the
independent validation receipt is
`../data/provenance/us_two_stage_regional_heterogeneity_validation_20261013.json`.

## Next defensible analysis

1. Freeze a multi-county, multi-model LOCA2 stage-1 panel on outcome-blind
   county support and report each GCM before any ensemble mean.
2. Construct direct-rainfall and PDSI/SPEI future exposures as separate
   families. Do not infer future PDSI from rainfall alone.
3. Predeclare geographic regions using an external production-region mapping,
   minimum county/state support, and complete-region holdouts before fitting
   regional response differences.
4. Refit or redesign the rainfall quantity response only with outcome-blind
   rules, then require spatial inference, leave-region validation, and terminal
   stability. The current unstable quantity result cannot be rescued by
   selecting favorable states or reference points.
5. Open damage or SCC work only after an identified causal response, validated
   climate exposure, national coverage/weighting, adaptation, price, and
   overlap gates pass.

## Reproduction

```bash
./.venv/bin/python -m unittest \
  us_county_validation.scripts.test_us_two_stage_regional_heterogeneity -v

./.venv/bin/python \
  us_county_validation/scripts/build_us_two_stage_regional_heterogeneity.py \
  --pattern-receipt data/provenance/us_corn_three_pattern_sensitivity_20261012.json \
  --response-receipt data/provenance/us_corn_quantity_pdsi_spatial_real_v1_20261012.json \
  --stage2-output us_county_validation/US_STAGE2_CORN_STABILITY_GATES_20261013.csv \
  --state-output us_county_validation/US_TWO_STAGE_STATE_DIAGNOSTICS_20261013.csv \
  --receipt data/provenance/us_two_stage_regional_heterogeneity_20261013.json

./.venv/bin/python \
  us_county_validation/scripts/validate_us_two_stage_regional_heterogeneity.py \
  --receipt data/provenance/us_two_stage_regional_heterogeneity_20261013.json \
  --memo us_county_validation/US_TWO_STAGE_PRECIPITATION_YIELD_DESIGN_MEMO_20261013.md \
  --output data/provenance/us_two_stage_regional_heterogeneity_validation_20261013.json
```
