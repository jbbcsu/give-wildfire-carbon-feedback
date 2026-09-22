# Preregistered Tuninetti--Davis spatial-validation protocol

Date frozen: 2026-09-22, before acquisition or inspection of the four maize
and soybean output rasters.

## Question and role

Do locations that the published Tuninetti--Davis (2026) water-balance model
classifies as more sensitive to historical ETa shortfalls also experience
larger projected crop-season drying in the independent five-ESM ISIMIP/SPEI
pipeline?

This is an external spatial validation diagnostic. It cannot estimate a yield
response, damages, or SCC and cannot promote the published sensitivity values
to causal coefficients.

## Frozen inputs

- Tuninetti--Davis Zenodo record 18937255: rainfed and irrigated maize and
  soybean 5-arc-minute ASCII grids. Each file must match the official byte
  count and MD5 in the frozen Zenodo metadata.
- Validated five-ESM late-century SPEI cubes already frozen for GFDL-ESM4,
  IPSL-CM6A-LR, MPI-ESM1-2-HR, MRI-ESM2-0, and UKESM1-0-LL under SSP126,
  SSP370, and SSP585.
- Existing frozen GGCMI crop calendars and rainfed/irrigated harvested-area
  weights. No outcome-dependent support changes are permitted.

## Alignment

The published 5-arc-minute output will be read six rows at a time and reduced
to the native 0.5-degree ISIMIP grid by the unweighted mean of finite values
within each 6-by-6 block. A block with no finite published value is missing.
The ASCII-grid header must be exactly 4320 columns, 2160 rows, lower-left
corner (-180, -90), cell size 1/12 degree, and no-data value -9999.

For each ESM, crop, irrigation regime, and harvest year 2092--2099, calculate
crop-season SPEI3 using the existing frozen calendar-window implementation.
For SSP370 and SSP585 separately, subtract the same-ESM SSP126 value, then
average over years and ESMs. More negative contrasts mean greater projected
drying. No climate model is dropped.

## Primary diagnostics

Run four prespecified cells: maize-rainfed, maize-irrigated,
soybean-rainfed, and soybean-irrigated, separately for SSP370--SSP126 and
SSP585--SSP126.

For each cell report:

1. common-support crop cells and harvested area;
2. area-weighted mean projected SPEI3 contrast;
3. area-weighted mean published historical-tail yield sensitivity;
4. unweighted and harvested-area-weighted Spearman rank correlation between
   published loss severity (`-published percent yield change`) and projected
   drying severity (`-SPEI3 contrast`);
5. a five-model sign-agreement count for projected drying and rank-correlation
   sensitivity after excluding cells with fewer than four finite model
   contrasts.

Bootstrap uncertainty will resample 0.5-degree cells within broad latitude
bands, with a fixed seed and 2,000 replicates. Because spatial dependence is
not fully removed, intervals are descriptive, not inferential causal
confidence intervals.

## Interpretation gates

- A positive spatial correlation is supportive external concordance only.
- A zero or negative correlation must be reported plainly and does not justify
  tuning either model.
- No result can be converted to yield, dollars, or SCC without a separate,
  approved state-variable and response mapping.
- ET0-mediated temperature effects in the published model prohibit adding its
  losses to GIVE temperature damages without an explicit overlap adjustment.

## Resource constraints

The four source rasters total 333,400,387 bytes. Acquisition is sequential and
hash-validated. Raster reduction is streaming and holds at most six source
rows in memory. Analysis output is limited to one compact 0.5-degree joined
table and JSON summaries; no expanded 5-arc-minute copies are created.
