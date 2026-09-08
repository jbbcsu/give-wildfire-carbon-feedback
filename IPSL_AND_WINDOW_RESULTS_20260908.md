# Independent model and time-window sensitivity

The IPSL-CM6A-LR/r1i1p1f1 SSP585-minus-SSP126 comparison is complete on the
same39.25/39.75N grid, fixed MIRCA2000 weights and2042–2049crop years as GFDL.
Maize uses29°C heat; soybean30°C. Both scenarios contain4,000maize/2,616soy
joint crop-years across500/327cells. These are climate inputs, not crop losses.

## Model disagreement is material

| Equal-cell mean scenario difference | GFDL maize | IPSL maize | GFDL soybean | IPSL soybean |
|---|---:|---:|---:|---:|
| Seasonal rainfall (mm) | −9.86 | +22.63 | −19.98 | +26.23 |
| Longest dry spell (days) | +0.85 | −1.33 | +1.05 | −0.38 |
| Rx5day rainfall (mm) | −2.03 | +3.53 | −4.00 | +3.75 |
| Second-stage threshold heat (°C·days) | +20.50 | +12.16 | +18.60 | +12.67 |

IPSL has positive eight-year-mean rainfall changes in391/500maize and236/327
soy cells, unlike GFDL's more negative regional aggregate. Mid-season heat
increases in both models, but even heat is not uniformly positive: IPSL's
first-stage soybean threshold degree days average−2.36°C·days. No preferred
model, positive-damage interpretation or confidence interval is selected.

## The short-window sign is not stable

Motivated by this disagreement, an explicitly exploratory sensitivity uses
three eight-year windows from the already resident28year rainfall inputs.
The windows were specified before this additional calculation, not before
observing the initial model disagreement. The last column below is the prior
completed28year result, reused rather than recalculated.

| Crop/model | 2032–2039 rain Δmm | 2042–2049 rain Δmm | 2052–2059 rain Δmm | 2032–2059 rain Δmm |
|---|---:|---:|---:|---:|
| Maize/GFDL | −28.13 | −9.86 | −23.87 | −24.00 |
| Maize/IPSL | −14.68 | +22.63 | −9.49 | −3.50 |
| Maize/MPI | −18.96 | +22.90 | −12.72 | −6.95 |
| Soybean/GFDL | −36.28 | −19.98 | −25.08 | −31.74 |
| Soybean/IPSL | −16.97 | +26.23 | −13.99 | −4.15 |
| Soybean/MPI | −17.07 | +28.48 | −6.82 | −1.81 |

Dry-spell signs also reverse for IPSL/MPI in the middle window. GFDL remains
negative-rain/positive-dry-spell in all three tested windows. All three models
have negative seasonal-rainfall differences in the retained full28year mean,
but this does not establish the sign of global agricultural damages. The
window comparison mixes internal variability with evolving forcing and cannot
identify their separate contributions. MPI has rainfall inputs but not yet
the newly constructed matched daily-heat controls; none were inferred from
its stage mean temperatures. Four overlapping GFDL/IPSL crop/model midperiod
summaries match the completed joint-climate results exactly for all four
shared rainfall metrics (maximum absolute discrepancy0).

## Data, resources and validation

Two newly verified public CC0 IPSL inputs use the same ISIMIP3b version20210512
and DOI10.48364/ISIMIP.842396.1. Small ZIPs are12,958,146and12,960,376bytes.
Each acquisition verifies catalogue/file/member/scenario/rights, safe archive
identity and extraction, exact3652daily dates, two latitude rows,720longitude
centers, K units and finite values. Child checksums are recorded; the full
global parent payloads were not downloaded or cryptographically verified.
The dataset IDs are22791b2f-5d4a-405d-8be9-d33f7782c083(SSP126) and
1dc615ca-83b8-4d8b-9f5b-25752056eca5(SSP585).

[IPSL SSP126 catalogue](https://data.isimip.org/api/v1/datasets/22791b2f-5d4a-405d-8be9-d33f7782c083/),
[IPSL SSP585 catalogue](https://data.isimip.org/api/v1/datasets/1dc615ca-83b8-4d8b-9f5b-25752056eca5/).

Explicit model/member/scenario/variable/bias-adjustment/frequency identity
tests now prevent relabeling another model's source. Both paired calendars
and fixed weight hashes must agree. Five wrapper tests, three comparison
tests and two new window tests pass; every real acquisition/build/comparison
passed on its first run. Eight new regime products are validated before
weighting. Existing GFDL jobs were not rerun.

Largest sampled process-group RAM is486.83MiB; numeric threads are fixed at
one. Scenario acquisition plus crop products occupy28,437,507bytes for SSP126
and28,500,204bytes for SSP585 (27.12/27.18MiB), including small local receipts,
before aggregate-provenance export. Each is below its64MiB batch ceiling;
both files are retained and system free space remains above130GiB. The
18window comparisons took0.68seconds and116.25MiB sampled RAM. No additional
weather data were acquired for that sensitivity calculation.

Protocols:`IPSL_PAIRED_HEAT_PROTOCOL_20260908.md` and
`PRECIPITATION_WINDOW_SENSITIVITY_PROTOCOL_20260908.md`.
Reproduction: register source configs, request/acquire each cutout, then run
the existing heat wrapper with`--esm IPSL-CM6A-LR`, explicit scenario/crop/
threshold, and new output directories. Pair using
`compare_paired_heat_climate.py --pairs-config config/ipsl_paired_heat_comparison_20260908.json`.
Window calculation:`evaluate_precipitation_window_sensitivity.py --out NEW.json`.
Use the bounded runner; do not repeat finished calculations to export notes.
Full hashes, receipts and resource accounting:
`data/provenance/ipsl_and_window_20260908.json`.

The next priority is full2032–2059matched daily-heat coverage, starting with
the missing GFDL decades, rather than promoting this short window's rainfall
sign. This requires additional *small* source-bound cutouts and multi-file
chronology validation, not global bulk files or relaxed evidence gates.
