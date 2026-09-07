# Future rainfall inputs and historical-range limits

September7,2026. Two successive real-data calculations completed using only
retained derived inputs. No daily climate was downloaded, no historical
response was refit, and no projected yield, welfare or SCC was calculated.

## Calculation and coverage

The unchanged historical nonlinear-basis builder and fixed-share allocator
were applied to each future crop/calendar regime before weighting. All future
outcome fields supplied to that utility were explicitly missing, with
`yield_observed=false`; outputs contain climate features only. Source hashes,
stage/season reconciliation, crop/member/scenario identities, exact keys and
fixed MIRCA2000 weight hashes were checked. No weight was inferred or
renormalized. The existing historical implementation was not edited.

There are18new climate tables: maize/soybean × GFDL/IPSL/MPI × SSP126/370/585,
2032–2059, latitudes39.25/39.75N. From686calendar cells per crop, missing
MIRCA weight support excludes186maize and359soybean cells, leaving500 and327.
The resulting208,404crop-year rows occupy19,422,308bytes (18.52MiB). These are
two narrow latitude rows, not national or global crop coverage. Irrigation
weights combine calendar exposures within cell; geographic summaries then
weight cells equally, not by area, crop value or welfare.

## Scenario contrasts in response-compatible rainfall inputs

Candidate minus SSP1-2.6, annual differences averaged within cell and then
equally across the same supported cells; all28harvest years used once:

| Crop | Climate model | Candidate | Seasonal rain (mm) | Weighted log1p rain index | Maximum dry spell (days) |
|---|---|---|---:|---:|---:|
| Maize | GFDL | SSP3-7.0 | -26.943 | -0.13995 | +2.523 |
| Maize | IPSL | SSP3-7.0 | -3.279 | +0.01437 | -0.518 |
| Maize | MPI | SSP3-7.0 | -15.063 | -0.06021 | +1.128 |
| Maize | GFDL | SSP5-8.5 | -23.997 | -0.09858 | +1.716 |
| Maize | IPSL | SSP5-8.5 | -3.497 | -0.01022 | +0.223 |
| Maize | MPI | SSP5-8.5 | -6.950 | -0.04216 | +1.340 |
| Soybean | GFDL | SSP3-7.0 | -30.977 | -0.09103 | +1.347 |
| Soybean | IPSL | SSP3-7.0 | -6.565 | -0.00399 | -0.271 |
| Soybean | MPI | SSP3-7.0 | -16.313 | -0.05758 | +1.079 |
| Soybean | GFDL | SSP5-8.5 | -31.743 | -0.10768 | +1.196 |
| Soybean | IPSL | SSP5-8.5 | -4.149 | -0.01137 | +0.327 |
| Soybean | MPI | SSP5-8.5 | -1.808 | +0.00788 | +0.919 |

The sign of an averaged nonlinear rainfall index need not equal that of
averaged rainfall: see MPI soybean/SSP5-8.5 and IPSL maize/SSP3-7.0. The index
is a weighted log1p basis, not log of average rain or a percentage rainfall
change. Nor are these entries projected log-yield effects. No climate model
is selected on these results, and three-model ranges are not confidence
intervals. Differences from the earlier686-cell separate-calendar summaries
reflect changed geographic support and fixed regime weighting; they are not
revisions to the raw weather. SSP1-2.6 is not a no-climate-change baseline.

All11features and zero-rain diagnostics are in
`data/provenance/future_weighted_precipitation_20260907.json`. For shape
contrasts only, positive-weight zero-rain seasons exclude5–6maize cells in
SSP5-8.5 comparisons; no soybean cells are excluded. The full receipt records
each comparison. Share HHI describes three stage fractions, not daily rainfall
concentration. It does not regain primary-predictor status through this step.

## How far outside historically observed ranges?

The next calculation streamed the historical direct basis, retaining only
positive observed-yield rows in1982–2010 on these latitudes. It produced
cell-specific marginal ranges from8,465maize exposures in292cells and4,321soybean
exposures in149cells. Maize cells have28–29observed years; soybean cells29.
This is direct-table exposure support, not necessarily the exact common
heat/drought regression sample. It excludes terminal2012–2016 outcomes.

Only292/500 (58.4%) future maize cells and149/327 (45.6%) soybean cells have
these observed historical ranges. Missing ranges are not treated as supported.
Among evaluable future crop-years under SSP5-8.5:

| Crop | Model | Rain total outside cell range | Stage2 mean temperature outside cell range | Any of11features outside, common evaluable rows |
|---|---|---:|---:|---:|
| Maize | GFDL | 9.82% | 67.45% | 92.51% |
| Maize | IPSL | 6.98% | 73.03% | 93.90% |
| Maize | MPI | 11.03% | 57.30% | 88.05% |
| Soybean | GFDL | 8.87% | 57.91% | 88.11% |
| Soybean | IPSL | 5.27% | 66.13% | 89.67% |
| Soybean | MPI | 7.17% | 45.97% | 83.08% |

Rain and stage2 temperature denominators are8,176maize and4,172soybean
crop-years per scenario/model. Common all-feature maize denominators are
8,173(GFDL) or8,174(IPSL/MPI), after excluding undefined future shapes;
soybean remains4,172. Almost all stage2 temperature violations are above the
historical maximum (one MPI maize row is below its minimum). The any-feature
column reflects multiple marginal checks, not a calibrated joint probability
or damage rate. Full scenarios, feature denominators, above/below counts and
missing-range counts are retained in
`data/provenance/future_precipitation_ranges_20260907.json`.

An inside-range value is not proof of joint or causal transportability.
Sparse interior support, correlated weather, climate-product differences,
unmodeled management and adaptation still matter. These results quantify
why mechanically projecting the historical joint response is not defensible
without explicit extrapolation and validation work. No rows were trimmed
to obtain a preferred response, and no response is promoted.

## Reproduction, resources and next step

Run `scripts/test_future_weighted_precipitation.py` (four synthetic tests),
then `scripts/build_future_weighted_precipitation.py --out-dir NEW_ABSOLUTE_DIR
--receipt NEW_JSON`. Run `scripts/test_future_precipitation_ranges.py` (two
synthetic tests), then `scripts/compare_future_precipitation_ranges.py
--out-dir NEW_ABSOLUTE_DIR --receipt NEW_JSON`. The second calculation requires
the registered first receipt/path. Both protocols predate their calculations;
all six synthetic tests passed without amendments or failed empirical runs.

Use `scripts/run_bounded_job.py` around each command, one numerical thread,
at most1GiB sampled group RSS and a fresh free-disk reserve. The18-table build
took23.57seconds, peaking at509.20MiB sampled group RSS. The range comparison
took1.13seconds, peaking at259.89MiB, and wrote127,515bytes of range tables.
The monitor is sampled, not a kernel cap. Resource logs/receipts use prefixes
`outputs/future_weighted_precipitation_20260907` and
`outputs/future_precipitation_ranges_20260907`. Raw/interim files remain ignored;
only code, documentation and aggregate provenance belong in Git.

These steps complete the missing nonlinear future precipitation-basis
construction for the retained balanced pilot. Aligned future Tmax threshold
integrals are still absent. The pending small-cutout download decision
controls the next acquisition/heat-construction step. Complete joint heat
controls, transport/extrapolation assessment, CO2/adaptation treatment,
economic calibration and matched marginal-emissions climate paths remain
necessary before climate-attributable agricultural damages or SCC.
