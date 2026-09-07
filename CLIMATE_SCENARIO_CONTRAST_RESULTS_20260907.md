# Direct climate-feature contrasts: limited geographic pilot

Completed September 7, 2026. These are derived ISIMIP3b scenario comparisons,
not observed trends, climate attribution, agricultural damages or SCC estimates.
The five-model maize/rainfed-calendar table covers only latitude centers
39.25°N and 39.75°N: 686 cells, including 154 USA-proxy and 102 CHN-proxy cells.
Those subsets are not national samples or projections. Calendar support is
not an observed rainfed crop-outcome sample.

## Main finding

In 2092–2099, SSP5-8.5 minus SSP1-2.6 lengthens the band-average maximum
growing-season dry spell in every model: median +2.18 days, model range
+0.93 to +6.11. Models disagree on growing-season rainfall totals: median
-13.20 mm, range -39.72 to +29.61 mm. Thus these simulations permit changes
in temporal distribution that cannot be summarized by a common sign of total
rainfall change. This does not establish their incremental effect on yields.
The agreement on dry spells does not extend to every period, scenario or
regional subset. It is not a significance test.

## Full comparison matrix

Entries are median [minimum, maximum] across model-specific equal-cell mean
differences. Brackets are model ranges, **not confidence intervals**. Reference
is always SSP1-2.6. Rx5day is maximum consecutive five-day rainfall within the
growing season; it is not a flood-loss measure.

| Years | Candidate | Subset within band | Rainfall total (mm) | Longest dry spell (days) | Rx5day (mm) |
|---|---|---|---|---|---|
| 2042–49 | SSP3-7.0 | Full | -6.76 [-18.33, 13.22] | 2.53 [-1.36, 3.20] | 0.71 [-4.07, 3.84] |
| 2042–49 | SSP3-7.0 | USA proxy | -14.61 [-49.25, 16.40] | 0.97 [-1.18, 2.72] | -0.76 [-6.33, 6.16] |
| 2042–49 | SSP3-7.0 | CHN proxy | 7.71 [-16.53, 39.59] | 1.31 [-1.88, 2.53] | 4.40 [1.17, 19.57] |
| 2042–49 | SSP5-8.5 | Full | 5.16 [-8.81, 19.88] | -0.77 [-2.83, 0.55] | 3.13 [-2.68, 6.75] |
| 2042–49 | SSP5-8.5 | USA proxy | -13.93 [-53.15, 11.55] | -0.27 [-1.70, 0.84] | 1.31 [-12.49, 5.66] |
| 2042–49 | SSP5-8.5 | CHN proxy | 33.09 [-5.97, 74.51] | -0.01 [-2.26, 1.45] | 11.09 [-2.04, 30.87] |
| 2092–99 | SSP3-7.0 | Full | 2.24 [-29.06, 25.70] | 2.41 [-2.26, 3.16] | 1.15 [-3.59, 4.47] |
| 2092–99 | SSP3-7.0 | USA proxy | 18.58 [-71.12, 37.15] | -0.61 [-1.92, 2.74] | 2.76 [-2.28, 10.10] |
| 2092–99 | SSP3-7.0 | CHN proxy | 28.15 [-15.67, 64.09] | 0.57 [-6.50, 1.47] | 4.97 [1.36, 14.67] |
| 2092–99 | SSP5-8.5 | Full | -13.20 [-39.72, 29.61] | 2.18 [0.93, 6.11] | 0.56 [-2.18, 4.68] |
| 2092–99 | SSP5-8.5 | USA proxy | -35.88 [-94.35, 70.84] | 2.37 [-1.54, 6.62] | -3.55 [-6.46, 12.06] |
| 2092–99 | SSP5-8.5 | CHN proxy | 43.82 [-27.25, 81.39] | -0.95 [-5.58, 1.80] | 7.24 [4.60, 21.56] |

All 11 feature comparisons, individual ESMs, spatial quantiles, paired cell
counts, mean temperatures, GMST differences, and zero-rain exclusions are
in `data/provenance/climate_scenario_contrasts_20260907.json` (60 comparisons).
Rainfall shares describe three calendar windows with boundaries at season
fractions 0, 0.3, 0.7 and 1, not measured phenological stages. The field named
`precipitation_timing_centroid` is a legacy share-weighted **stage-position
index** with weights (1/6, 1/2, 5/6). Those weights are not the actual window
midpoints; do not interpret this index as exact timing in days. HHI is the
sum of squared **three-stage shares**,
not daily rainfall concentration. Shares, timing and HHI exclude cells with
any zero-rain season in either paired eight-year path; excluded counts range
from zero to ten. Total-rainfall and dry-spell summaries retain these cells.

## Limitations and next step

Eight-year averages contain internal variability; ESMs are not independent
draws and scenarios do not isolate CO2. The comparison is not a no-warming
counterfactual or marginal emissions response. Results are equally weighted
by calendar cell, not crop production. Do not multiply these changes by the
historical yield contrasts: the latter use different transformed and
irrigation-weighted bases, and require additional heat controls.

Retained contiguous 2032–2059 crop-year features offer a longer-period,
multi-crop/calendar follow-up without new daily-data downloads. Its ESM × SSP
matrix is incomplete and must be reported as such. Inspect that support and
the temperature-feature alignment before extending the comparison.

Follow-up completed: `CLIMATE_CONTIGUOUS_CONTRAST_RESULTS_20260907.md` reports
the 28-year multi-crop comparison, incomplete ESM matrix, and missing aligned
Tmax controls. The two assemblies agree exactly on all overlapping records.

## Reproduction and validation

Protocol: `CLIMATE_SCENARIO_CONTRAST_PROTOCOL_20260907.md`.
Source table hash and upstream assembly/country-proxy receipts are pinned in
the result. Run in the documented existing `.venv`, with numerical threads
set to one and the bounded-job monitor:

```sh
.venv/bin/python scripts/test_climate_scenario_contrasts.py
.venv/bin/python scripts/summarize_climate_scenario_contrasts.py --out /tmp/climate_scenario_reproduction.json
```

Four synthetic tests passed (pairing, exact-year/duplicate rejection,
zero-rain shape exclusion, composition validation). The real calculation
completed in 3.60 seconds; sampled peak process-group RSS was 325.58 MiB
against a 1,024 MiB monitor limit. No raw downloads or large outputs occurred.
Resource receipts and logs remain in ignored `outputs/`.
