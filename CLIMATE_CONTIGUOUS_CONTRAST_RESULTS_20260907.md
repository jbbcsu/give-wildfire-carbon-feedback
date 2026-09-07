# Twenty-eight-year climate contrasts across crop calendars

Completed September 7, 2026. Derived climate-model scenario comparisons only;
not crop-yield projections, causal climate attribution, irrigation effects or SCC.

## Results and coverage

For maize and soybean rainfed calendars, all three common ESMs have lower
band-average growing-season rainfall and longer maximum dry spells in
SSP5-8.5 than SSP1-2.6 over 2032–2059. The median maize changes are -5.79 mm
and +1.45 days; soybean changes are -2.83 mm and +1.29 days. These are not
global changes: the geographic support remains latitude centers 39.25°N and
39.75°N. The sample is calendar support, not area-weighted crop production.

The common ensemble is GFDL-ESM4, IPSL-CM6A-LR and MPI-ESM1-2-HR, one member
each. MRI-ESM2-0 supplies a separate SSP3-7.0 sensitivity but lacks SSP5-8.5
in this retained longer-period matrix. UKESM is absent. No missing scenarios
or models were imputed. The 28 annual records per cell are used once each;
overlapping 21-year moving means are not treated as independent observations.

The table reports median [model minimum, maximum] for the same three ESMs.
These ranges are not confidence intervals. Rainfed here describes the
calendar, not the GDHY irrigation composition or an irrigation experiment.

| Candidate minus SSP1-2.6 | Calendar | Cells | Rainfall (mm) | Maximum dry spell (days) | Rx5day (mm) |
|---|---|---:|---|---|---|
| SSP3-7.0 | Maize | 686 | -11.86 [-22.00, -2.14] | 1.16 [-0.93, 2.66] | -1.43 [-3.66, -0.27] |
| SSP3-7.0 | Soybean | 686 | -9.90 [-21.43, -2.75] | 0.99 [-0.58, 2.31] | -0.84 [-3.59, -0.50] |
| SSP3-7.0 | First rice | 686 | -9.14 [-18.70, -2.35] | 0.43 [-0.49, 2.18] | -0.57 [-3.21, -0.11] |
| SSP3-7.0 | Second rice | 408 | -7.23 [-15.61, 6.33] | -0.06 [-0.30, 0.60] | -0.59 [-1.17, -0.26] |
| SSP3-7.0 | Spring wheat | 686 | -5.07 [-18.04, -3.80] | 0.83 [-0.59, 2.02] | -0.03 [-3.00, 0.03] |
| SSP3-7.0 | Winter wheat | 686 | -11.42 [-22.08, 4.97] | -1.26 [-1.43, -0.22] | -1.02 [-1.33, 1.39] |
| SSP5-8.5 | Maize | 686 | -5.79 [-18.84, -2.02] | 1.45 [0.01, 1.65] | -0.94 [-3.46, 0.66] |
| SSP5-8.5 | Soybean | 686 | -2.83 [-19.78, -2.17] | 1.29 [0.27, 1.77] | -1.16 [-3.66, 1.58] |
| SSP5-8.5 | First rice | 686 | -2.36 [-21.44, -2.29] | 1.16 [0.04, 2.30] | -0.33 [-4.11, 1.32] |
| SSP5-8.5 | Second rice | 408 | 5.25 [-25.06, 12.62] | 0.34 [0.18, 0.93] | 0.05 [-4.19, 0.71] |
| SSP5-8.5 | Spring wheat | 686 | -3.68 [-15.99, -3.63] | 0.93 [0.02, 1.64] | -0.39 [-3.09, 1.12] |
| SSP5-8.5 | Winter wheat | 686 | -6.09 [-18.33, -2.98] | -0.01 [-0.93, 2.65] | -1.13 [-1.68, 1.28] |

MRI's additional SSP3-7.0 differences are -10.28 mm/+1.17 dry-spell days
for maize and -9.80 mm/+0.75 days for soybean. Regional subsets need not
agree with the full band: in the USA-labeled subset, IPSL's SSP5-8.5 maximum
dry-spell changes are -0.385 days for maize and -0.309 for soybean, whereas
GFDL and MPI changes are positive. Do not promote full-band sign agreement
to country-wide agreement or statistical significance.

All 252 comparisons (7 ESM/candidate pairs × 12 crop/calendar definitions ×
3 reporting subsets) completed. The aggregate JSON includes all 11 features,
fully irrigated calendars, country subsets, individual ESM results and spatial
quantiles. Shape comparisons exclude cells with any zero-rain season in
either 28-year path; band exclusions range from zero to 41 depending on
crop/calendar/model. This restriction does not affect quantity/dry-spell means.
The timing field remains a coarse stage-position index, with the definition
and limitation documented in the protocol; it is not exact daily timing.

## Input alignment: what is still missing

All 132 consumed crop/calendar/scenario source sets contain stage mean
temperatures. None of these stage schemas contains the daily Tmax threshold
integrals required by the completed historical heat-controlled regressions.
Separate early-future GFDL maize/rainfed heat products exist for 2016–2019;
they do not supply missing midcentury, other-model or other-crop heat data.
Do not claim the entire project lacks heat data, and do not infer extreme
heat from average temperature.

The historical GDHY regressions also use nonlinear weather bases constructed
within irrigation calendars before fixed-area weighting. Raw rainfed-calendar
scenario means cannot be substituted into those regressors. A future joint
response needs aligned regime bases, heat inputs, support/transport evidence,
CO2 and adaptation treatment. A welfare replacement and matched marginal CO2
path are additional requirements. Longer-period climate contrasts alone do
not satisfy these links or justify multiplication by a historical slope.

## Reproduction and checks

- Protocol: `CLIMATE_CONTIGUOUS_CONTRAST_PROTOCOL_20260907.md`, including the
  transparent temperature-precision amendment and preservation of failed runs.
- Implementation: `scripts/summarize_contiguous_climate_contrasts.py`.
- Aggregate result: `data/provenance/climate_contiguous_contrasts_20260907.json`.
- Four synthetic tests: `scripts/test_contiguous_climate_contrasts.py`.
- Independent source-assembly overlap check:
  `scripts/check_climate_contrast_overlap.py` and
  `data/provenance/climate_contrast_overlap_20260907.json`.

The 28-year calculation took 21.52 seconds with sampled peak process-group RSS
225.08 MiB (2 GiB monitor cap). The maximum stage/season temperature residual
was 1.04403e-5 °C, below the explicitly revised 1e-4 °C threshold. Exact
calendar days and source hashes passed. Across the 11 common ESM/scenario
combinations, all 60,368 maize crop-year records overlap the short-period
assembly exactly: maximum difference zero for each of the 11 features.
This verifies assembly consistency, not independence or external validity.
No source downloads, raw-data rehydration or large output files were needed.

Run scripts in the existing `.venv` through `scripts/run_bounded_job.py`, with
numerical threads one. Both result scripts require a new output filename;
the overlap check intentionally validates the registered result filenames.
Raw/derived climate and country-proxy data remain ignored, not redistributed.
