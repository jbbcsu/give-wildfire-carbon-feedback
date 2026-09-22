# U.S. county drought-yield replication and validation protocol

**Frozen:** 2026-09-22, before acquisition of the national 2001--2013 USDM panel or inspection of any resulting response estimates.

**Post-freeze correction:** A primary-source audit later established that the
paper's annual exposure runs from October of the preceding year through
September of the harvest year. The calendar-year specification frozen below is
retained as an auditable sensitivity. The corrected design was separately
frozen before rerunning in `US_USDM_OCTSEP_CORRECTION_PROTOCOL_20260922.md`.

## Purpose and claim boundary

This analysis asks whether the project's U.S. NASS county outcomes reproduce the
published qualitative finding that observed drought has larger adverse yield
associations on dryland support than on irrigated support.  It is an external
historical validation of the precipitation/drought response design.  It is not a
global coefficient, a future USDM projection, a causal irrigation effect, a
monetary damage estimate, or an SCC input.

The benchmark is Kuwayama et al. (2019), *American Journal of Agricultural
Economics*, DOI 10.1093/ajae/aay037.  Their study uses county and year fixed
effects, state-specific linear trends, mutually exclusive U.S. Drought Monitor
(USDM) severity exposures, direct weather controls, and dryland/irrigated sample
separation over 2001--2013.  This project will match that structure where the
archived public inputs permit and label all deviations.

## Frozen sample and inputs

- Years: 2001--2013, inclusive.
- Outcomes: positive county-year NASS corn-for-grain and soybean yield from the
  existing all-production-practices panel.  The all-practice outcome is never
  relabeled as directly observed rainfed or irrigated yield.
- Geography: counties and states with an eligible NASS outcome.  USDM downloads
  may cover the lower 48 for reproducibility, but estimation uses the outcome
  intersection and reports one-sided coverage.
- Drought: official USDM county-week mutually exclusive area percentages for
  None, D0, D1, D2, D3, and D4.  Files are retrieved one state-year at a time,
  schema-checked, hashed, and retained only in the ignored raw-data tree.
- Primary drought exposure period: the full calendar year, matching the
  benchmark's annual D0--D4 weeks (which can sum to approximately 52 weeks).
- Drought-timing sensitivity: April 1--September 30 and the already documented
  crop/state usual-date calendar. These are extensions, not the replicated
  primary exposure period.
- Weather controls: April--September precipitation and temperature terms from the
  project's independently prepared daily weather panel, restricted to identical
  outcome keys.  If exact April--September controls are not yet available, the
  drought-only fit may run but the weather-controlled fit remains blocked and is
  not interpreted as the preferred specification.

## Irrigation classification

The preferred benchmark classifier follows the published design: a county is
classified as irrigated when the maximum **all-cropland** irrigated harvested-
cropland share across the 1997, 2002, 2007, and 2012 Censuses of Agriculture
exceeds 15%. Missing or suppressed irrigated acreage is never set to zero. The
numerator and denominator must both be numeric and refer to the same county,
Census year, and harvested-cropland concept. Crop-specific corn/soybean shares
already used elsewhere in this project are scientifically useful selectors but
are not the published classifier and cannot substitute for it in a claimed
replication.

Until all four vintages are acquired and validated, a 2012-only 15% classifier
may be reported solely as an explicitly approximate sensitivity.  Existing
fixed-2017 10%, 20%, and 30% selectors remain separate modern-composition
diagnostics and cannot be described as a Kuwayama replication.

## Exposure construction

The currently obtainable REST inputs yield season sums of **county-area**-
equivalent weeks in the mutually exclusive D0--D4 categories. Day-weighted
category-area shares are integrated over the season, divided by seven, and
retained separately. The published benchmark instead intersects weekly USDM
maps with agricultural land, so the REST implementation is a transparent
county-area approximation, not an exact exposure replication. An exact
agricultural-area sensitivity requires archived USDM geometries and a pinned
agricultural mask before fitting; results from the approximation must say so.
D0 is
"abnormally dry," not drought.  D1+ threshold days and a severity-weighted index
are secondary summaries only; they do not replace the primary category model
after results are inspected.

USDM intervals must cover every season day exactly once.  Duplicate, missing,
gapped, overlapping, non-rectangular, out-of-state, or checksum-changing source
records fail closed.

## Model hierarchy

For each crop and irrigation-support class, estimate log yield using:

1. drought-only: mutually exclusive D0--D4 exposure weeks;
2. weather-only: the pre-existing direct precipitation and temperature controls;
3. drought plus weather: both sets together.

Every family uses county fixed effects, harvest-year fixed effects, and
state-specific linear trends.  The preferred inference clusters by county;
state-cluster and spatial-correlation-robust inference are sensitivities if the
software and support permit.  No drought or weather term is selected by its
coefficient sign, significance, or implied damages.

The all-practice outcome means irrigation classes identify differences across
county support, not a within-county irrigation treatment effect.  Direct-practice
NASS yield estimates remain a separate corroborating analysis.

## Pre-specified checks and interpretation

- Publish counts by crop, year, state, support class, and missing-data reason.
- Reconcile category exposure arithmetic against direct raw-file spot checks.
- Report coefficient covariance and joint tests, not only individual stars.
- Refit with the crop calendar, with alternative irrigation thresholds, and
  excluding one state at a time.
- Use blocked temporal and leave-state-out predictive checks for model
  comparison.  In-sample fit alone is not validation.
- Treat attenuation of USDM coefficients after direct weather controls as
  expected evidence about overlapping moisture information, not as failure.
- Never add damages from USDM, PDSI/scPDSI, SPEI, and direct precipitation
  specifications.  They are competing moisture representations unless a later,
  separately frozen attribution design partitions them.

## Advancement gate

This benchmark can support the global precipitation-SCC paper only as evidence
that response signs, irrigation heterogeneity, and the hierarchy of moisture
representations are externally credible.  It cannot supply the global response
coefficient or an SCC contribution.  Advancement requires complete provenance,
an independently reproducible numerical audit, and honest reporting of null,
unstable, or contradictory results.
