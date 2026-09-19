# Frozen same-cell historical/future crop-weather support audit

Registered before reading future weather values for this comparison.
The purpose is to test where future direct-daily crop-weather inputs
would require extrapolating a historical weather–yield response, **not**
to estimate that response, climate-attributable yield, damages or SCC.

Use only the fixed 30,654 positive-MIRCA2000 rainfed-maize crop cells
(108,038,665.258 ha) validated in
`GLOBAL_THREE_ESM_MAIZE_AREA_WEATHER_RESULTS_20260918.md`. The historical
rainfed-maize direct-season feature files cover every harvest year
1982–2016 (35 years), all with the same fixed crop-calendar convention:

| Harvest years | Existing ignored Parquet(s) | SHA-256 |
|---|---|---|
| 1982–1989 | `data/interim/mai_noirr_1982_1989_stage_estimation_panel_v2.parquet` (season and wide stages) | `2a144ce55416be5c7e452fc0e64f505b8e53413a11365b75da3c2f92a3b61bae` |
| 1990–2011 | `data/interim/continuous_global_panel_1982_2016_v1/assembled_middle_1990_2011/direct_season/mai_noirr_1990_2011.parquet` and sibling `direct_stage/mai_noirr_1990_2011.parquet` | `6554bf09890e3d3fc6791d5f650259a7aa28c2c51102091938895204acd64c0e`; `a5f5324f16cd7992b219cb56e6a230c575fc19e2ebdd49b02cc08b1ff0c3b186` |
| 2012–2016 | `data/interim/mai_noirr_2012_2016_features.parquet` and `data/interim/mai_noirr_2012_2016_stage_features.parquet` | `32b127f6a2e8ba14d22cf073ce4ceb2b9f2a9967b18da180591cef8f48552b97`; `43c7208aa8597f29be767ca999d6b3cce0cc66508f0bbf40bdf404611f8c75d4` |

Read **only weather and key columns**; outcomes in the early source must
not be inspected. Require exactly one finite weather vector for each
matched cell/year, no duplicate or missing key, and the same wet-day
threshold (1 mm). Historical weather uses the observational ISIMIP3a
GSWP3-W5E5 pathway; future panels use the bias-adjusted ISIMIP3b ESM
pathway. Even matching feature names and calendars do not make those
climate sources interchangeable or identify a forced change.
The early file holds wide stage fields; the middle and late stage files
hold three rows per cell-year and must be pivoted with exact keys and
stage-sum reconciliation at the existing pipeline's preregistered 0.001 mm
tolerance before building the historical range.

For each matched cell and each of nine direct-weather features—season
rainfall, wet days, longest dry spell, Rx1day, Rx5day, mean temperature,
and early/middle/late stage rainfall—freeze the 35-year historical
minimum/maximum and empirical 5th/95th percentiles without consulting
future values. Use the same source-validated 72 future ESM×SSP×year
panels in the area-weather result. On each future cell-year, flag
`below_min`, `above_max`, and `outside_5_95` per feature, plus whether
**any** feature is outside the historical min/max. Report fixed-area
fractions by ESM, scenario and feature, averaging eight years equally;
also separate below from above and preserve annual support counts.
Do not exclude out-of-support cells, stretch ranges, tune thresholds,
or call 5th/95th exceedance a physical impossibility.

For every future panel, bind source manifest and independent validation
hashes and season/stage tile hashes before reading. Verify exact same
30,654 cell/area support, feature units, stage sums and physicality.
Audit saved source-bound annual exceedance ledgers independently, with
fixed raw-tile checks. Report historical range length and the effect
of using min/max versus 5th/95th, not a spurious confidence interval.
This is a domain-overlap diagnostic only; it does **not** license
coefficient transfer to future crops, adapt irrigation, isolate rain
from temperature, or monetize welfare.

One numerical worker at a time, sampled RSS <=512 MiB, new owned
output <=64 MiB, free disk >=130 GiB, log <=2 MiB. Preserve any
failed attempt and stop if the disk floor or source identities fail.
