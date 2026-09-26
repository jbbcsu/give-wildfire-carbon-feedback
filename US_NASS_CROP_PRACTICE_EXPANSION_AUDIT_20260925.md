# U.S. NASS crop/practice expansion and heterogeneity audit

**Audited:** 2026-09-25. This inventory and the new bounded wheat sensitivity
are historical U.S. diagnostics only. They do not identify causal weather or
irrigation effects, national responses, global transfer parameters, damages,
or SCC inputs.

## What is already estimation-ready

The fully validated direct-practice weather analysis remains limited to corn
and soybean. Both reported `IRRIGATED` and `NON-IRRIGATED` outcomes are ready
and already estimated on exact paired support:

- corn: 7,013 paired 1981--2018 county-years, 361 counties, 10 states;
- soybean: 4,844 paired 1981--2018 county-years, 255 counties, 5 states.

With the registered county and state-by-year fixed effects and temperature
controls, an additional 100 mm at median seasonal rainfall is associated with
+7.72% for non-irrigated corn versus -0.41% for irrigated corn, and +4.46% for
non-irrigated soybean versus -0.05% for irrigated soybean. The registered
soybean timing contrast, moving 10 percentage points of rain from late to
middle season, is +4.73% for non-irrigated soybean and -0.21% for irrigated
soybean. Exact coefficients and independently reproduced fields are in
`US_DIRECT_PRACTICE_PRECIPITATION_PRELIMINARY_RESULTS.md` and
`data/provenance/us_direct_practice_precipitation_association_20260826.json`.

Daily-heat sensitivities retain the practice heterogeneity. With 29 C heat
controls, a median-to-10th-percentile rainfall reduction gives fitted changes
of -12.88% versus -0.68% for corn and -10.18% versus -1.01% for soybean
(non-irrigated versus irrigated). Paired-gap fits account for the shared
county/year error: at median rainfall, +100 mm changes the fitted
irrigated/non-irrigated yield ratio by -7.55% for corn and -4.05% for soybean.
See `us_county_validation/US_RAINFALL_CURVE_AND_IRRIGATION_RESULTS_20260907.md`
and `us_county_validation/US_PAIRED_PRACTICE_GAP_ASSOCIATION.md`.

The national all-practice and final 990 m USDM analyses provide separate corn
and soybean heterogeneity by county support class. They are not direct-practice
outcomes and must not be combined with the regional paired-practice estimand.

## Additional crop readiness

All-classes wheat is the only additional crop with a completed direct-practice
outcome panel. The raw paired support has 9,672 county-years in 639 counties
and 14 states during 1981--2007; there are no paired wheat observations after
2007. Geography screening leaves 9,513 paired county-years in 631 counties.
The PDSI join has complete fixed-primary candidate seasons for every official
positive-acre wheat class in each retained state.

Wheat is **not** ready for the existing direct-rainfall analysis: its outcome
combines winter, spring, and durum wheat, while the daily weather pipeline has
not built and validated class-specific bases and county/year class weights.
Treating the candidate calendars as duplicate observations or selecting one
after looking at coefficients remains invalid.

No direct-practice rice, sorghum, cotton, or other additional-crop panel is
present in the locked acquisition. Recent practice-specific expansion also
remains blocked: the state terminal screen returns only one corn row per year
and no soybean rows, and Census production/area queries cannot construct the
required county practice-specific yields. See
`US_STATE_DIRECT_PRACTICE_TERMINAL_SUPPORT_RESULTS_20260921.md` and
`US_CENSUS_DIRECT_PRACTICE_OUTCOME_SUPPORT_RESULTS_20260921.md`.

## New bounded wheat/PDSI sensitivity

The official 2010 NASS calendar table contains independent 2009 harvested-acre
totals for winter, spring, and durum wheat by state. A design was frozen before
fitting that normalizes those acres within state and uses the fixed shares to
combine the already-built fixed-primary full-season PDSI candidates. Shares do
not vary by county, year, practice, or outcome.

The resulting panel contains 9,513 paired county-years, 631 counties, 14
states, and harvest years 1981--2007. Separate log-yield and exact paired-gap
models absorb county and state-by-year fixed effects and cluster by county.

| Prespecified form | Reported irrigated yield, +1 PDSI | Reported non-irrigated yield, +1 PDSI | Irrigated/non-irrigated ratio, +1 PDSI |
|---|---:|---:|---:|
| Linear | +0.31% [0.02, 0.60] | +3.60% [3.11, 4.10] | -3.18% [-3.65, -2.72] |
| Quadratic, evaluated at median PDSI | +0.33% [0.04, 0.62] | +3.70% [3.21, 4.20] | -3.25% [-3.72, -2.79] |

Intervals are county-clustered normal pointwise intervals conditional on the
fixed state-share mapping and specification. The paired-gap coefficients equal
the irrigated-minus-non-irrigated coefficients within `2.08e-17`. The linear
gap coefficient remains negative after every state deletion (14/14; range
-0.03463 to -0.02791 log point per PDSI unit). An independent joint sparse
design reproduces all six fitted PDSI coefficients within `2.83e-12`.

The production run peaks at 404,357,120 bytes RSS and the independent validator
at 408,780,800 bytes, both below the frozen 512 MiB ceiling. The first completed
attempt was retained under `data/interim/` and rejected because NumPy matrix
multiplication emitted numerical warnings; the corrected implementation uses
explicit stable products, treats warnings as errors, and is the only result in
`data/provenance/`.

This sensitivity says that wetter seasonal PDSI is more strongly associated
with reported non-irrigated than irrigated all-classes-wheat yield on the
selected historical support. It does not establish irrigation buffering
causally. The fixed 2009 state acreage mix postdates the 1981--2007 outcomes,
does not observe county/year wheat composition, and is suitable only as a
retrospective measurement sensitivity.

## Completed predictive check and promotion blocker

The preregistered first-difference predictive check is now complete. Each
practice has 8,171 consecutive-year differences across 573 counties and all
14 states. Linear PDSI improves fixed 2001--2007 terminal RMSE by 5.05% for
irrigated wheat and 14.85% for non-irrigated wheat relative to the trend-only
benchmark. However, the primary gate fails for both practices because the
prespecified materiality floor is cleared in only 8/14 irrigated and 11/14
non-irrigated leave-one-state-out development tests. California is the largest
reversal in both strata. The independently reconstructed maximum metric
discrepancy is `6.66e-16`; production and validation peak below 512 MiB. See
`US_WHEAT_PRACTICE_PDSI_PREDICTIVE_RESULTS_20260925.md`.

This check preserves PDSI as a separate alternative moisture family and does
not stack it with direct rainfall. Its failed primary gate prevents promotion
from a regional historical exploratory diagnostic.

Promotion of wheat into the direct-rainfall response remains blocked until an
independent historical county/year winter/spring/durum harvested-area source is
acquired or a prespecified sensitivity demonstrates that conclusions are
stable across defensible fixed class weights. Daily nClimGrid wheat features
must then be constructed class-first and combined only after those weights
pass. The present 2009 state-share result belongs in an exploratory appendix,
not the primary crop-response family.

## Reproducible artifacts

- Protocol: `US_WHEAT_PRACTICE_PDSI_PROTOCOL_20260925.md`
- Estimator: `us_county_validation/scripts/estimate_wheat_practice_pdsi_sensitivity.py`
- Result: `data/provenance/us_wheat_practice_pdsi_sensitivity_20260925.json`
- Independent validator: `us_county_validation/scripts/validate_wheat_practice_pdsi_sensitivity.py`
- Validation receipt:
  `data/provenance/us_wheat_practice_pdsi_sensitivity_validation_20260925.json`
- Predictive protocol:
  `US_WHEAT_PRACTICE_PDSI_PREDICTIVE_PROTOCOL_20260925.md`
- Predictive result:
  `data/provenance/us_wheat_practice_pdsi_predictive_20260925.json`
- Predictive independent validation:
  `data/provenance/us_wheat_practice_pdsi_predictive_validation_20260925.json`
- Ignored resource receipts:
  `data/interim/us_county/us_wheat_practice_pdsi_sensitivity_resource_20260925.json`
  and
  `data/interim/us_county/us_wheat_practice_pdsi_validation_resource_20260925.json`
