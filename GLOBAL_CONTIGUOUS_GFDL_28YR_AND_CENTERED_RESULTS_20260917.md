# GFDL global contiguous crop-weather feature and centered-source results

Status: **validated climate-source and feature engineering only**.
Registered design: `GLOBAL_CONTIGUOUS_GFDL_RIMEX_SOURCE_PILOT_PROTOCOL_20260917.md`.
No fitted GMT response, yield effect, damage, or SCC is reported.

## Source and support

- ISIMIP3b bias-adjusted daily `pr` and `tas`, version `20210512`,
  GFDL-ESM4 `r1i1p1f1`, SSP1-2.6, three contiguous source decades
  2031--2040, 2041--2050, and 2051--2060. Exact public source
  identifiers, byte sizes, SHA-512 checksums, content checks and
  rights are in the project provenance receipts. Primary archive:
  https://doi.org/10.48364/ISIMIP.842396.1.
- Crop and management: rainfed maize (`mai_noirr`); fixed registered
  crop calendar with 67,420 valid 0.5-degree global cells.
- Harvest-year features: every year 2032--2059, preserving actual
  daily sequences at source-decade boundaries. Existing independently
  audited 2032--39 and 2042--49 panels were reused unchanged; only
  2040--41 and 2050--59 were newly built.
- Centered features: for each cell, growth stage, and annual indicator,
  arithmetic means of 21 consecutive harvest years centered on each
  year 2042--49. Annual dry-spell lengths and annual rainfall maxima
  are averaged *as annual indicators*, not recalculated after joining
  daily values across years. This follows the centered-indicator
  support required for evaluating a RIME-X-style warming-level
  response (https://doi.org/10.5194/gmd-19-6797-2026); it is not
  itself an estimated response.

## Independent checks and results

| Artifact | Passed support | Independent check | Sampled peak RSS |
|---|---:|---|---:|
| 28 annual global panels | 1,887,760 season; 5,663,280 stage rows | Exact source, calendar and tile hashes; physical bounds; stage sums; 252 selected raw-daily cell-season reconstructions | 176,603,136 bytes (audit) |
| Centered 21-year global panel | 539,360 season; 1,618,080 stage rows, eight centers | All 36 tile receipts and hashes, center-year/calendar keys, stage sums; 168 independent recomputations from the 28 annual panels | 412,909,568 bytes (audit) |

The centered parity pilot exactly matched all 5,488 prior two-row
season and 16,464 stage reference rows after an explicit schema-only
mapping of fixed crop-calendar geometry (1e-9 absolute tolerance).
The largest 5,630-cell latitude tile passed the memory stress test
at 273,072,128 sampled bytes. Other tiles were built serially in
at most two-latitude-row memory chunks. No worker exceeded the
512 MiB sampled RSS, 64 MiB owned-output or 130 GiB free-disk gates.

The first annual-source audit attempt failed on an empty tile when
NumPy received an object-typed empty groupby array. Its failure
receipt/log remain retained; the reviewed `v2` skipped only numerical
comparisons for proven paired-empty tables and passed. The first
centered parity attempt stopped on the old/new fixed-geometry column
label difference, also with its failure receipt/log retained. The
`v2` retry compared the geometry values after explicit renaming and
reduced memory through two-latitude-row streaming. No failed attempt
is reported as a passed result.

The ignored exact-audit receipts are:

- `data/interim/gfdl_ssp126_2032_2059_global_contiguous_qc_v2_20260917.json`
- `data/interim/gfdl_ssp126_global_centered_21yr_pilot_v2_20260917/global_manifest.json`
- `data/interim/gfdl_ssp126_global_centered_21yr_pilot_v2_20260917/independent_global_centered_audit.json`

The code paths are `scripts/continue_gfdl_contiguous_global_missing_years.py`,
`scripts/audit_gfdl_contiguous_28yr_global.py`,
`scripts/pilot_gfdl_global_centered_21yr_tile.py`,
`scripts/continue_gfdl_global_centered_tiles.py`, and
`scripts/audit_gfdl_global_centered_21yr.py`.

## Interpretation and remaining gates

The 28-year time series is one ESM realization and one emissions
scenario. Its eight centered windows share 20 of 21 years between
adjacent centers; they are not eight independent climate-response
observations. They cannot identify a global precipitation-per-K
relationship, separate greenhouse-gas forcing from aerosols or
circulation variability, or support a marginal CO₂ perturbation.
Nor are there matched crop-yield outcomes in this source artifact.
The next required work is a multi-ESM/multi-scenario warming-response
design with out-of-sample validation and joint precipitation/
temperature/dependence checks, followed by yield estimation,
agricultural welfare calibration and GIVE SCC integration. Under the
current >=130 GiB free-space floor and <=64 MiB new owned-output
limit, additional multi-gigabyte global daily raw pairs cannot be
acquired locally without an explicitly revised storage or remote-
processing route. Published monthly pattern products are benchmarks,
not substitutes for validated crop-stage daily extremes or dry spells.
