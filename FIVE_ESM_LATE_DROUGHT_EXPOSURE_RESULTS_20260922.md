# Five-ESM crop-calendar drought exposure, 2092--2099

## Result and interpretation boundary

The completed matrix contains five named ISIMIP3b ESMs, SSP1-2.6,
SSP3-7.0, and SSP5-8.5, maize and soybean, harvest years 2092--2099,
five crop-calendar windows, SPEI-1/3/6, and fixed rainfed, irrigated, and
combined MIRCA-OS v2 area bases. All 15 ESM--scenario cases passed the
case-level climate and crop-window validators. The independent matrix
validator reproduced 1,350 case means, 900 named-model contrasts, and 180
cross-model summaries in 7,065 checks with zero saved-precision numerical
disagreement.

The primary diagnostic is rainfed crop-season SPEI-3. Relative to the same
ESM's SSP1-2.6 value, every named ESM is drier under both higher-forcing
scenarios:

| Crop | Contrast | GFDL | IPSL | MPI | MRI | UKESM | Five-model mean | Median | Negative models |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Maize | SSP3-7.0 minus SSP1-2.6 | -0.617 | -0.374 | -0.380 | -0.321 | -0.552 | -0.449 | -0.380 | 5/5 |
| Maize | SSP5-8.5 minus SSP1-2.6 | -0.885 | -0.828 | -0.458 | -0.438 | -0.701 | -0.662 | -0.701 | 5/5 |
| Soybean | SSP3-7.0 minus SSP1-2.6 | -0.536 | -0.276 | -0.306 | -0.138 | -0.374 | -0.326 | -0.306 | 5/5 |
| Soybean | SSP5-8.5 minus SSP1-2.6 | -0.883 | -0.786 | -0.442 | -0.098 | -0.500 | -0.542 | -0.500 | 5/5 |

The broader sign diagnostic contains 45 window--scale--irrigation cells per
crop and contrast. All five ESMs are negative in 45/45 maize cells for both
contrasts, 42/45 soybean SSP3-7.0 cells, and 44/45 soybean SSP5-8.5 cells.
At least four of five ESMs are negative in all 180 crop--contrast feature
cells. These named-model signs are not probabilities, confidence intervals,
or evidence that the five models are independent draws.

This is a validated **scenario-exposure** result, not anthropogenic
attribution, an estimate per kelvin, or a marginal CO2-pulse response. The
SSP contrasts contain multiple forcing differences and internal variability.
They are not yield effects, monetary damages, or an SCC estimate. No drought
coefficient is applied because the registered global country-held-out yield
gate has not promoted a drought response family.

## Construction

Daily precipitation and mean/minimum/maximum temperature for 2091--2100 are
read one day at a time on the frozen 31,208-cell crop-support grid. Daily
Hargreaves--Samani reference evapotranspiration is aggregated to monthly
precipitation-minus-ET0. Frozen observational 1982--2011 generalized-logistic
parameters transform 1-, 3-, and 6-month rolling water balance to SPEI; no
future refit is permitted. Crop-year aggregation uses GGCMI calendars and
harvest years 2092--2099. Maize and soybean are summarized separately over
the season, three crop stages, and the 90-day preplant window using fixed
MIRCA-OS v2 hectares. Rainfed, irrigated, and combined bases are parallel
summaries, not treatment effects.

Each case streams global inputs under a 512 MiB sampled process-group limit,
retains a roughly 40 MiB derived HDF5, validates a separate cell/month sample
and every crop-window aggregate, and only then deletes the two newly acquired
extrema files. Exact byte counts, SHA-512 identities, URLs, and reacquisition
metadata are preserved. Sampled builder peaks across the final MRI and UKESM
cases remained below 399 MB.

## Reproducibility record

- Frozen source registry:
  `data/provenance/isimip3b_five_esm_late_drought_extrema_20260921.json`.
- Case protocol: `FIVE_ESM_LATE_DROUGHT_STREAMING_PROTOCOL_20260921.md`.
- Matrix SHA-256:
  `99f77812774cc5f11db035d48e710b0417e6b5b75f00fc28494146f1853ff1e9`.
- Independent validation SHA-256:
  `c91ee295b4dd391ccf44307483ca36bcc16e993d8798d374db6529bdcfa8998e`.
- Public evidence record:
  `data/provenance/five_esm_late_drought_public_evidence_20260922.json`.
- Primary implementation:
  `scripts/build_isimip3b_late_drought_pair.py`,
  `scripts/summarize_isimip3b_late_drought_crop_windows.py`, and
  `scripts/summarize_five_esm_late_drought_crop_matrix.py`.
- Independent validation:
  `scripts/validate_isimip3b_late_drought_pair.py`,
  `scripts/validate_isimip3b_late_drought_crop_windows.py`, and
  `scripts/validate_five_esm_late_drought_crop_matrix.py`.

The SPEI definition follows Vicente-Serrano, Begueria, and Lopez-Moreno
(2010), [doi:10.1175/2009JCLI2909.1](https://doi.org/10.1175/2009JCLI2909.1).
Future work must keep SPEI as a competing climatic-water-balance response
family rather than add its effect to precipitation and temperature effects.
