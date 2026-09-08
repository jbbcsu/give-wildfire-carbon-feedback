# U.S. county climate bridge: completed preliminary benchmark

The climate inputs can now be compared on actual NASS county boundaries and
the same NASS crop-season calendars used in the completed U.S. analysis.
This is a source-matched exposure benchmark, not a new yield-response estimate.

## Coverage and validation status

Of the retained 1982–2010 reporting sample (346 corn and252 soybean counties),
only16 corn and15 soybean counties are wholly inside the original climate
strip. Their346 and227 county-years produce573 climate rows per path. The
corn subset has15 Kansas counties and Kit Carson County, Colorado; soy has
the same15 Kansas counties. Partial counties were excluded, not assigned
centroid weather or rescaled as though wholly observed. The broader419-county
1981–2019 weather inventory remains unchanged.

None of the weather years in the retained1981–2019 dataset is a new untouched
evaluation period. The2012–2019 terminal set has already been used in reported
predictive sensitivities. NASS has some later outcome records in the source
manifest, but corresponding weather is not supplied by this dataset and an
untouched outcome/selection history has not been established. County reporting
is more direct than reconstructed grid yields, but shared upstream national
inputs mean independence from GDHY should not simply be assumed.

## Paired climate and measurement-source differences

Numbers below average within county, then equally across counties. They are
neither national means nor crop-area/production weights. Both paths use the
same NASS calendar and county weights. Tmax integrals use29C for corn and30C
for soybean in this table; both thresholds remain in the full result.

| Crop / contrast | Seasonal precipitation, mm | Longest dry spell, days | Rx5day, mm | Stage2 mean temperature, C | Stage2 heat, C-days |
|---|---:|---:|---:|---:|---:|
| Corn: factual minus counterclim | +26.10 | -2.28 | -0.78 | +0.67 | +22.61 |
| Soy: factual minus counterclim | +24.48 | -2.61 | -0.85 | +0.41 | +6.10 |
| Corn: GSWP factual minus nClimGrid | +31.87 | -1.29 | +4.81 | +0.42 | +34.51 |
| Soy: GSWP factual minus nClimGrid | +32.25 | -1.05 | +7.81 | +0.42 | +26.42 |

The measurement-source differences are comparable to or larger than several
factual/counterclim differences. This warns against inserting coefficients
estimated on one weather source directly into another source's scenarios.
It does not identify the separate contributions of spatial resolution,
measurement method, daily observation window or source construction. The
paired source labels do not eliminate those differences.

The detrended-climate comparison suggests more seasonal precipitation and
shorter dry spells in this selected factual sample, but not larger five-day
precipitation maxima. More water can coincide with increased heat. Do not
interpret this as a net crop benefit or anthropogenic damage estimate.
Across-stage shares and HHI are also calculated; no zero-rain cell required
shape exclusion on this sample. The full ignored comparison retains annual
means and county dispersion; those are not uncertainty intervals.

## Implementation and resources

New weights intersect TIGER2019 polygons with the half-degree climate cells,
project clipped areas to EPSG:5070 and normalize only after proving complete
geographic coverage. They are whole-county proxies including water/noncrop
land, not irrigation-specific fields. All nonlinear rainfall and heat metrics
are constructed within cells before weighting. The new builder explicitly
uses pr/tas/tasmax only; it does not invent Tmin to satisfy an older interface.
Only36 daily climate cells are materialized, one scenario/decade block at a
time. Exact dates, source hashes, county/practice calendars and stage sums
validate. No new climate download was needed for this completed benchmark.

Nine targeted synthetic tests passed (3overlap,4features/weights,2comparison).
The inventory, real construction and comparison all passed first execution.
Peak sampled process-group memory was301.84MiB. The original analysis files
before publication exports totaled649,211bytes; the first full and then compact
publication exports were retained separately. This footprint excludes the
already retained daily cutouts and TIGER files. All jobs used1024MiB sampled
RAM,64MiB owned new-disk and130GiB free-space safeguards. The monitor does not
bound the Codex application's own memory.

Code: `scripts/inventory_us_paired_climate_overlap.py`,
`scripts/build_us_paired_county_climate.py`,
`scripts/compare_us_paired_county_climate.py`, and
`scripts/export_us_paired_county_climate.py`.
Protocols: `US_PAIRED_CLIMATE_OVERLAP_PROTOCOL_20260908.md` and
`US_PAIRED_COUNTY_CLIMATE_PROTOCOL_20260908.md`.
Hash-bound publication evidence:
`data/provenance/us_paired_county_climate_20260908.json`.
Original tables/weights/annual diagnostics remain ignored in
`data/interim/us_paired_county_climate_20260908/`.

## Next action, without weakening evidence gates

This16/15county sample does not meet the prior response-fit minimum of25
counties and500rows per practice. A wider paired-climate acquisition is now
registered for the actual retained county footprint, split into three small
latitude bands and54 capped source archives. The intent is to remove the
spatial bottleneck with source-matched inputs, not lower the sample gate.
See `US_PAIRED_REGIONAL_ACQUISITION_PROTOCOL_20260908.md`. This is not a promise
that every coastal county will have complete valid climate coverage. Any
subsequent exploratory response fit needs its own frozen design and must not
be promoted to causal agricultural damages or SCC by this acquisition alone.
