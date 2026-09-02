# EPA annual precipitation pattern-scaling benchmark

Status: external benchmark and uncertainty sensitivity; not the primary
climate driver and not an agricultural-damage or SCC input.

## Reviewed source

The public [USEPA pattern-scaled-climate-variables repository](https://github.com/USEPA/pattern-scaled-climate-variables)
was reviewed at commit
`dac5503549d5158e0257894012293acff45c0cb4` on 2 September 2026. The software
is MIT licensed and the repository states that its data and figures are
CC-BY-4.0.

The precipitation workflow reads precomputed PEEPS annual CMIP6 pattern
files. Each file contains a gridded slope and intercept for annual
precipitation against global mean temperature. The EPA scripts use the slope,
convert precipitation flux to mm/day/K or annual mm/K, and aggregate the
pattern to GIVE countries using area, GDP, or population weights. The checked
country output has 184 countries, 26 climate models, and five socioeconomic
scenario labels. In `make_patterns_for_give.R`, all climate slopes are read
from `ssp245_pr` files; the SSP loop changes socioeconomic weights, and SSP4
and SSP5 weights are copied from SSP2 and SSP1. Consistent with that code, the
area-weighted precipitation pattern is identical across the five output SSP
labels for every country-model group. Eleven models are omitted from a
restricted sample because the workflow flags their pattern rasters as
noncontinuous.

The temperature workflow separately ranks FAIR draws by 2100 temperature and
pairs them with ranked GCM temperature patterns. The repository describes
cross-GCM pattern variation as its main nonparametric uncertainty source.

## Relationship to this project

The EPA workflow answers a useful but narrower question: how does a change in
GMST map into a spatial pattern of **annual mean precipitation**, and how does
that pattern aggregate to geopolitical units? It does not construct crop-year
or phenological-stage exposures, daily wet/dry sequences, rainfall timing,
CDD, Rx1day, Rx5day, drought indices, crop yields, irrigation/adaptation
responses, agricultural welfare, or a precipitation SCC.

Our primary estimand therefore remains distinct. We derive daily ISIMIP3b
features within crop- and regime-specific calendars, preserve their joint
dependence, estimate agricultural responses with global yield and U.S. NASS
evidence, replace rather than stack the existing GIVE agriculture sector, and
evaluate matched FAIR baseline/pulse paths. Novelty rests on the validated
combination of daily crop exposure, agricultural response, adaptation, and
marginal welfare accounting—not on claiming that precipitation pattern
scaling itself is new.

## Predeclared uses

1. **Annual-total external benchmark.** Aggregate our daily precipitation to
   annual totals and area-weighted country means, then compare signs,
   magnitudes, and spatial rank patterns against the EPA/PEEPS ensemble. Use
   the three exactly overlapping primary ESMs—MPI-ESM1-2-HR, MRI-ESM2-0, and
   UKESM1-0-LL—for named-model checks; use the broader EPA ensemble only as a
   distributional benchmark.
2. **Sector-appropriate weighting test.** Reproduce the area-weighted country
   comparison, but retain crop harvested-area/value weights for the
   agricultural damage calculation. GDP and population weights are
   sensitivities, not agriculture defaults.
3. **FAIR--GCM dependence sensitivity.** Compare the primary same-realization
   climate construction with a preregistered rank-pairing sensitivity inspired
   by EPA's 2100-GMST pairing. Do not outcome-select the pairing or substitute
   temperature-pattern rankings for precipitation validation.
4. **Model-continuity and ensemble uncertainty.** Carry a formal continuity
   gate and preserve discrete between-ESM variation. Do not treat the EPA
   coefficient-of-variation map rule as sufficient validation near zero-mean
   patterns.

## Non-uses

- Do not adopt annual country precipitation as the primary crop exposure.
- Do not label socioeconomic SSP weights as distinct climate-response
  scenarios when the underlying precipitation slope is SSP2-4.5.
- Do not infer crop damage, causality, drought, extremes, or daily timing from
  the annual pattern coefficient.
- Do not add an EPA-pattern damage term beside the joint agriculture
  replacement; that would double count precipitation effects.

The benchmark is accepted only if its source commit, exact overlapping-model
mapping, baseline units, aggregation weights, and comparison support are
recorded in a machine-readable receipt. It can diagnose or bound the primary
driver but cannot open response, damage, welfare, or SCC gates.
