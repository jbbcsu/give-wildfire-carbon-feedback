# Tuninetti--Davis 2026 global drought benchmark audit

## Decision

Use Tuninetti and Davis (2026) as a published global **process-based spatial
benchmark**, not as the primary empirical yield-response function and not as a
direct SCC parameter.

The paper is unusually relevant: it covers 17 crops, distinguishes rainfed
from irrigated production, resolves results at 5 arc minutes, and publishes
code plus output rasters. But its drought-sensitivity metric is a modeled
percent yield change between median and tenth-percentile historical actual
evapotranspiration (ETa), calculated with prescribed FAO crop response factors.
It is not an estimated causal response of observed yield to SPEI, PDSI, or a
transient climate-change perturbation.

Primary sources:

- Article: <https://doi.org/10.1038/s41467-026-72715-y>
- Official code and outputs: <https://doi.org/10.5281/zenodo.18937255>

## What the paper supplies

The authors run a soil-water-balance model using precipitation, reference
evapotranspiration, soils, crop calendars, rooting depths, and crop
coefficients. They calculate ETa for 1961--2018, then compare the median and
tenth percentile of each pixel's historical ETa distribution. Yield changes
follow the FAO water-production relationship with a crop-specific prescribed
yield-response factor. The paper reports a global median production loss under
the historical tail of 10.1% for rainfed production and 6.8% for irrigated
production; soybean has the largest crop-level rainfed sensitivity reported in
the main text (15.2%). These are historical-tail scenario results, not future
climate-change damages.

The official Zenodo record contains 36 files: 34 crop-by-irrigation output
rasters and two MATLAB programs. Maize and soybean each have separate rainfed
and irrigated output rasters. The four relevant rasters total 333,400,387
bytes. They were deliberately not downloaded at this audit stage because the
published estimand is not yet approved for response parameterization; only the
two small code files and metadata were acquired and hash-checked.

## Reproducibility assessment

The official code is informative but not turnkey. It contains machine-specific
absolute paths, refers to unbundled water-balance inputs, spreadsheets, and a
custom export helper, and the Zenodo metadata does not declare a license. The
published output rasters make spatial comparison feasible even though exact
end-to-end rerunning from the release alone is not.

The code confirms the central methodological details:

- 1961--2018 ETa histories;
- pixelwise median and tenth-percentile ETa;
- prescribed yield-response factors of 1.25 for maize and 0.85 for soybean;
- a proportional ETa-to-yield equation and a floor at a 100% yield loss;
- separate rainfed and irrigated calculations.

The source audit is machine-readable at
`data/interim/tuninetti_2026_source_audit_20260922/result.json`. Raw acquired
files remain ignored under `data/raw/`.

## Compatibility with the GIVE precipitation project

### Defensible uses

1. Compare the spatial ranking and sign of our maize/soy drought exposure with
   the published rainfed/irrigated sensitivity maps.
2. Use the prescribed FAO water-response branch as a process-based sensitivity
   analysis after matching the paper's ETa state variable and time contrast.
3. Use the published rainfed--irrigated gap to check the direction and rough
   scale of our adaptation scenarios.

### Uses that are not defensible

1. Treating the historical tenth-percentile loss as a marginal climate-change
   damage or multiplying it directly by a CO2 pulse.
2. Regressing or translating its sensitivity map into a universal
   SPEI-to-yield coefficient without a separately validated mapping.
3. Adding its water-stress loss to a temperature damage function without an
   explicit attribution rule. ET0 already carries atmospheric-demand effects.
4. Calling its prescribed FAO relationship an empirically estimated global
   drought--yield response.

## Consequence for the project hierarchy

The benchmark materially strengthens validation and offers a credible
process-based alternative, but it does not remove the response-estimation
gate. The primary global SCC branch still requires either:

- a leakage-safe empirical relationship with adequate held-out stability; or
- a transparent process-based replacement whose state variable is driven on
  matched GIVE baseline and pulse paths and whose overlap with existing GIVE
  temperature damages is explicitly removed.

The next safe analysis is a bounded spatial comparison using the four
published maize/soy rasters. It should be preregistered as validation only and
stream the 5-arc-minute text rasters so memory remains below the project cap.
