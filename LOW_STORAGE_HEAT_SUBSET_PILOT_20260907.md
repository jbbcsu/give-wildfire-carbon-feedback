# Remote heat cutout: completed server job, local processing pending

September 7, 2026. This is a data-acquisition workaround, not a climate emulator
or a new empirical crop-impact result.

## What succeeded

The official [ISIMIP Files API](https://github.com/ISI-MIP/isimip-files-api)
supports server-side spatial selection. Its documented
[`select_bbox` operation](https://github.com/ISI-MIP/isimip-files-api/blob/main/docs/operations.md)
cuts the requested region without spatial averaging. One request selected
[-180,180,39,40] (west, east, south, north) from GFDL-ESM4/r1i1p1f1,
W5E5-adjusted SSP1-2.6 daily Tmax, 2041–2050, version20210512.

The [official source metadata](https://data.isimip.org/api/v1/datasets/6802d6a9-1d1b-4d58-b436-b47ce82cec6f/)
identified the public CC0 1.0 file and resource DOI
[10.48364/ISIMIP.842396.1](https://doi.org/10.48364/ISIMIP.842396.1).
Source identity, version, scenario/member, rights, file length and catalogue
SHA-512 were checked before submission. The original file is2,064,668,768bytes.
The server reports one completed output with no errors. A HEAD request reports
12,891,438bytes (12.29MiB) for its ZIP, about160times smaller than the source.
No archive or climate bytes have been downloaded locally.

Reproduction: `scripts/prepare_heat_subset_pilot.py --out NEW_RECEIPT.json
--submit`, using the registered config. Do not resubmit an uncertain request
without inspecting its `.partial` receipt. The script itself has no archive
download path. Existing job and completion evidence are in
`data/provenance/heat_subset_server_request_20260907.json` and
`data/provenance/heat_subset_server_completion_20260907.json`.
The completion receipt is a transcription of observed API/HEAD fields, not a
saved response-body hash. The service reports a604800second retention value;
continued availability must be checked before any later download.

## Required next checks; not yet performed on real cutout content

Local acquisition requires the requested one-file exception to the150GiB
free-space rule, with64MiB maximum additional disk occupancy. Before extraction,
inspect ZIP members and their uncompressed sizes; count both archive and
uncompressed file against the cap, reject traversal/symlinks and unexpected
members, and stream rather than retaining the archive in RAM. Abort if the
budget cannot hold the archive, its expected climate member and small outputs.

Check the member's own SHA-256, NetCDF variable identity, K/C units, Gregorian
daily chronology, 3652expected dates,720longitudes and exactly39.25/39.75N
latitude centers. These dimensions are expectations, not verified observations.
Record missing values and eligible calendar/cell/season counts, not silently
imputed temperatures. The extracted file cannot match the whole-file SHA-512;
its lineage is server-derived and the whole parent payload has not been
cryptographically verified locally. Preserve the request, parent catalogue
hash and separately measured child hash without claiming otherwise.

Both heat builders now have an explicit `--calendar-by-coordinates` option.
For a two-row cutout, `--lat-start 0 --lat-stop 2` refers to the climate file;
the full calendar is selected by exact latitude/longitude labels. No nearest
matching, coordinate rounding, longitude wrapping or regridding is permitted.
Default full-grid behavior is unchanged. The synthetic test compares seasonal
and three-stage outputs against full-grid inputs and rejects shifted,
duplicate, nonfinite and wrongly ordered calendar dimensions.

Both synthetic tests passed: four seasonal rows and twelve stage rows match
exactly, including cross-year maturity-day inclusion and two thresholds.
The run took4.77seconds with223,608,832bytes (213.25MiB) sampled group RSS,
under a1GiB monitor. The first sandboxed launch could not invoke `ps` and
stopped before tests; the monitored retry completed. This is not real cutout
validation. Receipt/log: `outputs/cutout_calendar_tests_20260907_resource.json`
and `outputs/cutout_calendar_tests_20260907.log`.
The preexisting stage-heat integration test also passed after the change,
including multi-file chronology, seasonal/stage reconciliation and panel join
(3.15seconds,223.56MiB sampled group RSS). Its log and resource receipt use
the prefix `outputs/cutout_stage_backcompat_20260907`.

After authorization and content checks, build one crop/calendar at a time,
starting with maize/noirr harvest2042–2049 and the existing29C threshold;
the prior year supplies cross-year seasons. Reconcile stage day counts,
weighted mean Tmax and threshold integrals to the separate seasonal output,
then join to matching retained scenario features with exact keys. No national
or global coverage follows from two latitudes, and one scenario/decade cannot
supply a joint multi-scenario projection. Larger expansion needs its own
space/retention plan. Climate-to-yield transport, CO2/adaptation and welfare
validation remain separate requirements.
