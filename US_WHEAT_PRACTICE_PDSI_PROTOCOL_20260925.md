# U.S. all-classes-wheat paired-practice PDSI sensitivity protocol

**Frozen:** 2026-09-25 before fitting any state-share-weighted wheat/PDSI
coefficient. The NASS outcome panel and candidate calendar features were
already constructed and inspected in earlier work.

## Question and claim boundary

Can the existing regional NASS all-classes-wheat irrigated/non-irrigated pairs
support a bounded historical drought-association sensitivity once winter,
spring, and durum calendar candidates are combined with an independent fixed
weight rather than pooled as interchangeable observations?

This is an exploratory retrospective measurement sensitivity. It is not a
causal drought or irrigation effect, a nationally representative U.S.
estimate, a future drought projection, a global transfer parameter, a damage
function, or an SCC input.

## Frozen inputs and mapping

- Use the hash-recorded 1981--2019 direct-practice NASS panel joined to NOAA
  nClimDiv county PDSI and the fixed-primary NASS crop-calendar seasons.
- Retain positive paired all-classes-wheat yields on the geography-eligible
  support. The observed paired wheat series ends in 2007; do not impute later
  years.
- For each state, construct fixed wheat-class weights from the official
  `published_harvested_acres_2009_thousand` values in
  `config/us_county_nass_usual_date_definitions_2010.csv`. Normalize across
  winter, spring, and durum wheat rows available in that state. These weights
  are fixed across county, year, and reported irrigation practice.
- Combine only the fixed-primary, full-season, day-weighted mean PDSI feature.
  Every positive-weight class must have exactly one candidate feature per
  county--year--practice; absent or duplicate candidates fail.
- The 2009 state acreage mix is a retrospective exposure-weight sensitivity,
  not observed county/year varietal composition. Report its weights and do not
  call it a primary wheat exposure.

## Frozen estimation

Fit separately for reported irrigated yield, reported non-irrigated yield, and
their exact within-county/year log ratio:

`log(yield) = county FE + state-by-harvest-year FE + f(weighted seasonal PDSI)`

The paired-gap outcome is
`log(irrigated yield) - log(non-irrigated yield)`. Report two prespecified
forms together: linear PDSI and linear-plus-squared PDSI. Use county-clustered
CR1 uncertainty with a normal reference. Do not select a form, class weight,
sample, or coefficient after inspection. Require at least 500 paired
county-years, 50 counties, and five states.

Because the practice outcomes share identical county/year exposures and fixed
effects, the paired-gap coefficient must equal the irrigated coefficient minus
the non-irrigated coefficient within numerical tolerance. Refit the linear
paired-gap model after deleting each represented state and report its sign
range. These are numerical and support-stability checks, not causal validation.

## Resource and output rules

Read only the required Parquet columns, use one numerical thread, and keep peak
RSS below 512 MiB. Emit aggregate counts, state weights, coefficients,
covariances, contrasts, and validation identities only; emit no row-level
outcomes or predictions. All causal, national-representativeness, future,
global-transfer, damage, and SCC authorization flags remain false.
