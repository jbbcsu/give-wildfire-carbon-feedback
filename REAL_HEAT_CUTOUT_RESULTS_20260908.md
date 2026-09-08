# Real low-storage heat inputs and historical-range results

September 8, 2026 UTC. The one-file download approved in this task succeeded.
The small-file workaround is now demonstrated on real data, not only synthetic
tests. No crop-yield losses, economic damages or SCC were estimated here.

## Acquisition and matching

The registered GFDL-ESM4/r1i1p1f1 W5E5-adjusted SSP126 cutout has 3,652 daily
Tmax observations per grid cell for 2041–2050, latitudes 39.75/39.25N and 720
longitude centers. Units are K; all values are finite. Archive length and ETag
match the saved server receipt. Child SHA256 hashes are recorded; these do not
verify the entire parent payload. Public source license/DOI/version and calendar
lineage are documented in `LOW_STORAGE_HEAT_SUBSET_PILOT_20260907.md`.

Four crop/calendar combinations each produce 5,488 seasonal and 16,464 stage
rows for harvest 2042–2049. The first maize/noirr outputs were reused, not
reconstructed. Threshold is 29°C and stage fractions are 0/0.3/0.7/1. Seasonal
and stage metrics reconcile, including exact exceedance-day and degree-day
sums; the initial pilot's maximum mean-Tmax reconciliation residual is
7.11e-15°C. Calendar identities and stage lengths match retained rainfall
inputs before weighting. Fixed MIRCA2000 weights give 4,000 maize rows across
500 cells and 2,616 soybean rows across 327 cells. Weighted stage mean
temperatures match the prior rainfall basis exactly. Six heat fields were
appended; no future outcomes or fitted response coefficients were generated.

## Historical heat ranges

The new range calculation uses observed-yield historical heat inputs in
1982–2010, not terminal evaluation years. It compares each of six stage heat
metrics with its own cell-specific historical range, without clipping.

| Crop | Historical cells / future cells | Evaluable crop-years | Outside at least one of six ranges |
|---|---:|---:|---:|
| Maize | 292 / 500 | 2,336 | 1,503 (64.34%) |
| Soybean | 149 / 327 | 1,192 | 691 (57.97%) |

For second-stage degree days above 29°C, outside-range shares are 33.39% for
maize and 21.73% for soybean. All but one maize departure for this metric are
above the historical maximum. Missing-range crop-years (1,664 maize; 1,424
soybean) are not counted as inside or outside. Historical cells contain 28–29
usable years for maize and 29 for soybean.

These results flag extrapolation, not damages or a probability of model
failure. Six marginal ranges do not establish joint support even when all
are satisfied. Historical/future climate source differences can also affect
these comparisons. This is one low-forcing scenario and a narrow latitude
band, not global geographic coverage or a no-climate-change counterfactual.
The soybean 29°C diagnostic does not replace its locked 30°C response control;
the latter remains to be built from the same resident cutout.

## Resources and reproduction

All jobs used one numeric thread and a 1 GiB sampled process-group RAM cap:

| Job | Wall seconds | Peak sampled MiB |
|---|---:|---:|
| Real acquisition and maize/noirr validation | 13.82 | 332.19 |
| Three missing calendars and two-crop join | 7.68 | 512.03 |
| Historical heat-range calculation | 0.90 | 162.22 |

Six new synthetic tests passed (three exact-join, three range tests); all real
jobs passed on the first execution. Sampling is not a kernel-enforced cap.
Combined archive, extracted NetCDF, heat products, joint tables and local
receipts total 28,306,311 bytes (27.00 MiB), before this small documentation and
provenance export, below the approved 64 MiB additional-storage ceiling.

Reproduction order under `scripts/run_bounded_job.py`:

1. `run_authorized_heat_subset_pilot.py` with actual ignored approval record,
   as described in `AUTHORIZED_HEAT_SUBSET_WORKFLOW_20260907.md`.
2. `test_extend_heat_cutout_two_crops.py`, then
   `extend_heat_cutout_two_crops.py --pilot data/interim/authorized_heat_subset_real_20260908
   --out-dir data/interim/two_crop_heat_real_20260908` (new output path required).
3. `test_compare_future_heat_ranges.py`, then
   `compare_future_heat_ranges.py --parent data/interim/two_crop_heat_real_20260908/receipt.json
   --out data/interim/two_crop_heat_real_20260908/historical_heat_ranges.json`.

Do not rerun completed acquisition to reproduce documentation. Original local
receipts and logs are retained; aggregate provenance is exported to
`data/provenance/real_heat_cutout_20260908.json`. Raw/intermediate climate and
the actual user approval record remain ignored and are not pushed to GitHub.

Next: construct the missing soybean 30°C control from this resident file,
then evaluate requirements for a matched second-scenario cutout. No additional
download is approved by this one-file exception. Multi-model attribution,
validated future response transport, CO2/adaptation, welfare and the marginal
CO2 path still prevent an empirical precipitation-agriculture SCC estimate.
