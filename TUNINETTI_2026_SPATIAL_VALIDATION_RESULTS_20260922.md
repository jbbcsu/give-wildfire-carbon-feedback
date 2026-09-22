# Published global water-stress map versus projected drought exposure

## Result

The preregistered comparison is complete and independently validated. It finds
robust global-average crop-season drying in the five-ESM late-century
contrasts, but only weak and mixed spatial concordance with the historical
water-stress sensitivity maps published by Tuninetti and Davis (2026).

This is evidence against treating the published map as a universal future
yield-response coefficient. It remains useful as an independent process-based
benchmark.

Primary sources:

- [Tuninetti and Davis (2026), Nature Communications](https://doi.org/10.1038/s41467-026-72715-y)
- [Official code and output archive](https://doi.org/10.5281/zenodo.18937255)

## Design

Four official 5-arc-minute rasters—maize and soybean, each rainfed and
irrigated—were acquired sequentially and matched exactly to the official byte
counts and MD5 hashes. They were streamed into 0.5-degree means without
creating expanded copies. Published loss severity is the negative of the
paper's historical median-to-tenth-percentile ETa yield change.

The independent climate side uses crop-season SPEI3 for 2092--2099 from five
validated ISIMIP ESMs. SSP3-7.0 and SSP5-8.5 are differenced from the
same-model SSP1-2.6 path and averaged across years and models. More negative
SPEI means greater projected drying. Fixed GGCMI calendars and MIRCA-OS v2
rainfed/irrigated hectares define support and weights.

| Crop / regime | Contrast | Cells | Mean SPEI3 change | Published historical-tail yield change | Unweighted rank correlation | Area-weighted rank correlation (descriptive 95% interval) |
|---|---:|---:|---:|---:|---:|---:|
| Maize rainfed | SSP370−126 | 18,574 | −0.440 | −7.54% | 0.059 | 0.042 [0.014, 0.069] |
| Maize rainfed | SSP585−126 | 18,574 | −0.650 | −7.54% | 0.186 | 0.225 [0.196, 0.255] |
| Maize irrigated | SSP370−126 | 10,533 | −0.503 | −5.26% | −0.067 | −0.267 [−0.317, −0.217] |
| Maize irrigated | SSP585−126 | 10,533 | −0.791 | −5.26% | −0.014 | −0.218 [−0.274, −0.161] |
| Soybean rainfed | SSP370−126 | 11,925 | −0.320 | −17.19% | 0.029 | −0.121 [−0.162, −0.082] |
| Soybean rainfed | SSP585−126 | 11,925 | −0.533 | −17.19% | 0.135 | −0.079 [−0.121, −0.035] |
| Soybean irrigated | SSP370−126 | 3,908 | −0.362 | −9.65% | 0.050 | 0.172 [0.097, 0.243] |
| Soybean irrigated | SSP585−126 | 3,908 | −0.669 | −9.65% | 0.059 | 0.119 [0.032, 0.202] |

Intervals are a fixed-rank, latitude-stratified cell bootstrap with 2,000
draws. They are descriptive and do not correct fully for spatial dependence,
climate-model dependence, response uncertainty, or model-selection
uncertainty.

## Interpretation

The global mean signal strengthens from SSP3-7.0 to SSP5-8.5 for every
crop-regime cell, but local model agreement is much weaker than the aggregate
signal: all five ESMs project drying in only 28%--54% of common cells, while at
least four project drying in 55%--74%. This reconciles a robust global mean
with substantial spatial heterogeneity.

Spatial concordance is not stable across irrigation regimes. It is positive
for rainfed maize and irrigated soybean, negative for irrigated maize, and
negative under area weighting for rainfed soybean. The largest positive
diagnostic is rainfed maize under SSP5-8.5 (0.225); it is still modest. The
mixed signs are unsurprising because the two objects differ:

- the published map describes historical sensitivity to an ETa tail using a
  prescribed FAO water-production function;
- the GIVE project contrast describes a future change in crop-calendar SPEI3;
- ETa sensitivity depends on soils, crop coefficients, water balance, and the
  historical climate distribution, whereas future SPEI change identifies the
  location of projected drying;
- irrigation treatment and water availability differ between the two
  frameworks.

The benchmark therefore validates the relevance of water stress and the need
to preserve rainfed/irrigated structure, but it does not validate a common
spatial response map or an SCC coefficient.

## Validation and resources

An independent implementation recomputed the cell means, model counts,
weighted and unweighted rank correlations, bootstrap intervals, and aggregate
statistics in 450,966 numerical checks. It also re-read twelve selected
6-by-6 blocks directly from the four raw ASCII grids. All checks passed.

The primary job peaked at 584,024,064 bytes sampled process-group RSS under a
640 MiB guard; the independent audit peaked at 189,562,880 bytes. The joined
75,141-row diagnostic table is 7.6 MiB. This stays far below the earlier
machine-memory failure and creates no large derived raster.

Evidence:

- frozen protocol: `TUNINETTI_2026_SPATIAL_VALIDATION_PROTOCOL_20260922.md`
- source audit: `TUNINETTI_2026_GLOBAL_DROUGHT_BENCHMARK_AUDIT_20260922.md`
- result SHA-256: `5311dd64150e05e6c7d674640280302d442a398c14000783490436260d7efa28`
- validation SHA-256: `d6b299c58eadb4ecec1d766caa0d26025f9733939a414c3dc91d5a607b6f34c3`
- joined table SHA-256: `a7f1b3c43fc528ccea1ba1803f1db04698fbf03aa6d922f37b58fdc7b77864f6`

## Gate status

- external spatial process validation: **passed**;
- global drought-to-yield response: **not passed**;
- damage: **not passed**;
- SCC: **not passed**.

No published historical-tail loss is multiplied by a future SPEI change or a
CO2 pulse. A matched state-variable response or separately approved process
replacement remains necessary.
