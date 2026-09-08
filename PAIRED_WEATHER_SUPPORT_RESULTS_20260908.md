# Historical counterclimate: empirical weather-support results

The quantity-only diagnostic flags relatively few observations, but adding
temperature reveals substantially more marginal extrapolation. Neither result
establishes a valid crop-damage estimate. The two diagnostics below disagree
because they ask different questions; their discrepancy is itself important.

| Crop / feature set | Cells / crop-years | Outside any factual marginal range | Beyond joint-distance threshold |
|---|---:|---:|---:|
| Maize / quantity | 292 / 8,465 | 484 (5.72%) | 368 (4.35%) |
| Maize / quantity + heat | 292 / 8,465 | 4,254 (50.25%) | 548 (6.47%) |
| Maize / quantity + heat + distribution | 285 / 8,262 | 4,904 (59.36%) | 354 (4.28%) |
| Soy / quantity | 149 / 4,321 | 269 (6.23%) | 213 (4.93%) |
| Soy / quantity + heat | 149 / 4,321 | 2,013 (46.59%) | 40 (0.93%) |
| Soy / quantity + heat + distribution | 149 / 4,321 | 2,449 (56.68%) | 33 (0.76%) |

Fractions are pooled crop-years, not independent draws or global agricultural
weights. The durable receipt also gives equal-cell fractions. Distribution
excludes seven maize cells with a zero-rain irrigation regime somewhere in
either full climate path; it therefore has a different cohort.

## What was measured

Within each cell, counterclim weather is compared with the factual weather
years that have positive observed crop yields in 1982–2010. Quantity is
log(1 + precipitation); joint heat adds three stage Tmeans and three stage
Tmax degree-day integrals. Distribution adds dry spells, Rx5day, two stage
shares and across-stage HHI. These are 1-, 7- and 12-dimensional diagnostics.

The marginal check tests min/max ranges. The distance check uses the nearest
factual year in factual-standard-deviation-scaled coordinates, with a threshold
at the 95th percentile of factual leave-one-year-out neighbor distances. A small
departure in one feature can exceed a marginal range without producing a
large RMS distance. Conversely, a gap between factual observations can produce
a distance flag inside every marginal range. The latter occurs in 31 maize
and 3 soy crop-years for quantity + heat. Sparse multivariate observations and
correlated coordinates make the distance threshold a limited descriptive
screen, not a test of causal overlap. Increasing dimension does not provide
an improvement in support just because its flagged fraction falls.

Factual leave-one-out exceedance fractions are 6.36–6.79% for maize and
6.46–6.85% for soy, reflecting finite empirical quantiles and ties, not a
calibrated nominal 5% test. No all-constant cells, zero thresholds, or departures
in constant dimensions occurred. Nothing was trimmed or imputed to obtain
these results, apart from the prospectively specified distribution cohort.

## Implications

Use the existing historical crop associations as historical evidence only.
Do not multiply a barred diagnostic coefficient by these climate differences.
A new joint response needs nonlinear temperature/precipitation control,
explicit source-construction and support treatment, independent outcome
validation, and a transport assumption. Do not select a quantity-only impact
model merely because it flags fewer observations: omission of heat is not a
solution to extrapolation. The quantity-first rule concerns the moisture
family, with appropriate temperature controls retained.

This pilot has only two latitude rows. ATTRICI removes historical climate
trends conditional on its construction; it is not an anthropogenic-forcing
experiment or a GIVE emissions pulse. These results provide no yield change,
agricultural welfare loss or SCC estimate.

## Reproduction and resource accounting

Protocol: `PAIRED_WEATHER_SUPPORT_PROTOCOL_20260908.md` (registered before run).
Run `scripts/test_paired_weather_support.py` first, then
`scripts/diagnose_paired_weather_support.py --out NEW_IGNORED_PATH.json`, then
`scripts/export_paired_weather_support.py --out NEW_IGNORED_SUMMARY.json`, each
using the bounded launcher's owned-output mode described in
`OWNED_DISK_ACCOUNTING_20260908.md`. A rerun of the exporter intentionally
reads the original registered diagnostic and resources to reproduce its
publication summary; use a new exporter contract to publish a new analysis.

Six synthetic tests passed. The real diagnostic passed on its first execution:
258.59 MiB sampled peak process-group RSS, 703,865 sampled new disk bytes
(result plus log), about 2.26 seconds in the child job. These timings exclude
tool/approval orchestration and are not total project elapsed time. The tests
and export also completed. No download or raw-file hydration was needed.
The monitor enforced the existing 1,024 MiB sampled ceiling, 64 MiB owned disk
budget and 130 GiB free-space floor; it is not a kernel allocation quota.

Compact aggregate, sources, code/protocol and original output/log hashes:
`data/provenance/paired_weather_support_20260908.json`. Full cell diagnostics
remain ignored at `data/interim/paired_weather_support_20260908/result.json`.

The next stage is defined in `JOINT_RESPONSE_RESEARCH_DESIGN_20260908.md`.
