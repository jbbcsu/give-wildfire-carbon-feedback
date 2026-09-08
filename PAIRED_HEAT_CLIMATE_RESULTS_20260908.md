# Matched rainfall/heat scenario pilot: actual results

Same-model SSP585 minus SSP126, GFDL-ESM4/r1i1p1f1,2042–2049,39.25/39.75N
only. These are climate-input contrasts, not agricultural losses or SCC.

## Result

Fixed MIRCA2000 irrigation-calendar weights are applied before pairing.
Differences are averaged over eight years within each cell and then equally
over cells. Maize uses29°C heat; soybean30°C. Counts are4,000maize/2,616soy
paired crop-years across500/327cells respectively.

| Climate feature, higher minus lower scenario | Maize | Soybean |
|---|---:|---:|
| Seasonal rainfall (mm) | −9.86 | −19.98 |
| Longest dry spell (days) | +0.85 | +1.05 |
| Largest five-day rainfall total (mm) | −2.03 | −4.00 |
| First-stage threshold degree days (°C·days) | +4.87 | +3.94 |
| Second-stage threshold degree days (°C·days) | +20.50 | +18.60 |
| Third-stage threshold degree days (°C·days) | +8.54 | +0.77 |

Rainfall changes are geographically mixed:247of500maize cells and121of327soy
cells have positive eight-year-mean changes. Their cellwise10th–90th percentile
rainfall differences are[−89.21,+34.03]mm and[−105.74,+22.85]mm. These are
spatial dispersion, not confidence intervals; no area/production/value
weighting across cells is claimed. Internal variability and the short period
matter. The seasonal rainfall and dry-spell contrasts are not annual-global
rainfall statistics or a separation of quantity versus timing's yield effects.

Second-stage degree days increase in416of500maize and261of327soy cells. This
provides the matched heat controls missing from earlier precipitation-only
future comparisons; it does not validate extrapolating historical response
functions. Historical heat-range checks classify1,864of2,336evaluable maize
and899of1,192soy future crop-years outside at least one of six heat ranges
(79.79%/75.42%). The lower-scenario values were64.34%/58.98% using the same
crop-specific thresholds. Missing historical ranges are excluded, not treated
as inside. Marginal ranges neither establish joint support nor distinguish
historical/future climate-source differences from forced change.

## Acquisition, license and verification

The separate SSP585 source contract uses public CC0 ISIMIP3b input data,
version20210512, resource DOI10.48364/ISIMIP.842396.1. Its exact2041–2050 source
file is2,064,887,843bytes; only the12,905,254byte spatial ZIP was downloaded.
Official catalogue identity, source checksum, member, variable, rights and
request geometry were verified before submission. The completed server job
reports one file and no errors. HEAD/GET length and ETag match; safe ZIP
inspection, child hashes,3652daily dates, exact grid and finite K temperatures
pass. No full parent-payload checksum verification is claimed.

[Official source catalogue](https://data.isimip.org/api/v1/datasets/512a7927-2125-494d-b0fe-7229dac66d44/),
[ISIMIP input dataset](https://doi.org/10.48364/ISIMIP.842396.1).
The original SSP126 config, cutout and authorization were not relabeled.
Standing user download authority is recorded separately from the catalogue/
server-request-only contract. All raw/derived row-level climate remains ignored.

Four newly constructed regime products each have5,488seasonal and16,464stage
rows. Calendar, stage and season reconciliation precede exact scenario-matched
rainfall joins. The generalized wrapper refuses an input config with a
different model/member/scenario. Fixed-weight and full paired-key equality
checks pass. Five new synthetic tests cover registered archive identity and
paired contrasts; four preexisting exact-join tests also pass after wrapper
changes. No real job failed or required an evidence-rule amendment.

## Resource accounting and reproduction

New SSP585 archive, NetCDF, four regime products, joint tables and receipts
total28,340,440bytes(27.03MiB), before this small aggregate-provenance export.
Largest sampled group RSS484.09MiB (soybean construction); maize474.56MiB.
Acquisition took5.89s; crop calculations5.38/4.90s; paired comparison0.47s;
historical range jobs0.68/0.69s. All used one numerical thread, <=1GiB sampled
RAM limits and the original64MiB acquisition/processing disk ceiling.

New scripts/commands (use the bounded runner and new output paths):

1. `prepare_heat_subset_pilot.py --config config/isimip3b_ssp585_heat_cutout_20260908.json
   --out data/provenance/ssp585_heat_request_20260908.json --submit`.
2. `acquire_registered_heat_cutout.py` with that config/request receipt and
   `--out-dir data/interim/ssp585_heat_cutout_20260908`.
3. `extend_heat_cutout_two_crops.py --scenario ssp585` once with`--crops mai
   --threshold-c 29` and once with`--crops soy --threshold-c 30`, new output
   directories, and the maize output included in soybean's`--accounted-dir`.
4. `compare_paired_heat_climate.py --out data/interim/ssp585_heat_cutout_20260908/paired_climate_comparison.json`.
5. `compare_future_heat_ranges.py` once for each completed crop receipt.

Do not repeat completed acquisition or calculations. Aggregate provenance,
exact command-resource receipts and hashes are exported in
`data/provenance/paired_heat_climate_20260908.json`.

Next: extend this matched heat comparison to an independent ESM on the same
support before treating a single-model sign/magnitude as robust. Global
geographic expansion requires a cumulative-storage plan. Yield-response
transport, CO2/adaptation accounting, welfare and marginal-emissions links
remain unestimated; none is filled by these scenario contrasts.
