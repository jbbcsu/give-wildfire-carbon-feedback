# First author-released PEEPS precipitation coefficient: bounded source pilot

Date: 17 September 2026 (Mountain time). This is a **source acquisition and
structure result only**. It does not establish precipitation prediction,
yield change, monetary damage, or SCC.

## Source and selected artifact

Kravitz and Snyder (2023), PEEPS v1.1,
https://doi.org/10.1371/journal.pclm.0000159; exact author dataset record
https://doi.org/10.5281/zenodo.7557622 (CC BY 4.0). The outer
`outputs.tar.gz` is 3,244,457,764 bytes (Zenodo MD5
`eed1a0e8a43bf915c78ec68d0f37e357`). The HTTP server supports byte
ranges. Only bytes `0-283115519` were requested, streamed directly through
the nested `outputs/dec_patterns.tar.gz`, and one exact member was saved in
the ignored project interim area:

`MPI-ESM1-2-HR_ssp585_pr_monthly_patterns_dec.nc` — 1,196,250 bytes,
SHA-256 `13e17ee549adfe109356b765cc25a50c2adc539399b95c09eeae73ec0b237699`.

The first attempt failed before data download because the system Python's
certificate store could not validate TLS. Its monitor receipt/log are kept
in `data/interim/peeps_published_mpi_ssp585_dec_20260917/`. The retry used
`certifi`'s CA bundle **with TLS verification on**, not an insecure bypass.
It completed in 52.60 s, with sampled peak process-group RSS 40,108,032 B,
sampled new output 1,199,048 B, and free disk still approximately 133 GiB,
under 512 MiB/64 MiB/130 GiB safeguards. The source file, extraction
receipt/log, and subsequent validation receipts are in the ignored
`data/interim/peeps_published_mpi_ssp585_dec_v2_20260917/`; no wildfire
project files were read or written for this acquisition.

The 1.2-MB NetCDF opened and passed a separate 114,933,760-B-peak bounded
structure validator. It has finite `slope` and `intercept` arrays on one
`param` by 192 latitude by 384 longitude cells (73,728 values each),
monotone coordinates, and metadata `source_id=MPI-ESM1-2-HR`,
`experiment_id=ssp585`, `grid_label=gn`, `variant_label=ensemble_avg`,
`variable_id=pr`, `variable_units=kg m-2 s-1`. The reported slopes range
from -2.7113008367941783e-05 to 2.6067429915736125e-05 in source units
per model predictor unit. This is the **author's published coefficient
file**, unlike the separate project-fitted GFDL/IPSL PEEPS-style benchmark.

## Important limits before application

- The range extraction verifies the exact HTTP range, nested member header,
  NetCDF readability, metadata, byte count and *retained file* SHA-256. It
  does **not** verify the MD5 of the entire 3.2-GB outer archive or provide
  an author-published per-member checksum. A second independent source or
  full streamed whole-archive hash is still needed for strongest bitwise
  provenance.
- The archived December ESM list overlaps the project's ISIMIP selection for
  MPI-ESM1-2-HR, MRI-ESM2-0 and UKESM1-0-LL, but not GFDL-ESM4 or
  IPSL-CM6A-LR. This single December/SSP5-8.5 file is not a complete crop
  year, model ensemble, or scenario comparison.
- The [author source code](https://github.com/JGCRI/linear_pattern_scaling/blob/main/helpers.py)
  regresses gridded precipitation on **absolute annual global `tas`**,
  calculated as a cosine-latitude-weighted monthly global mean followed by
  an equal-month annual arithmetic mean. The GIVE/FAIR and project's native-
  area/day-weighted GMST definitions must be reconciled; interpreting the
  fitted intercept as a zero-warming rainfall baseline would be wrong.
- No crop-weighted precipitation amount, month-share, daily-spell, yield,
  damage or marginal-pulse predictions have been computed from this file. A
  limited same-scenario grid-cell physicality probe follows below. Published
  linear coefficients must still pass nonnegative-rainfall and whole-
  scenario/crop-area holdouts. The previous locally fitted linear patterns
  failed positivity, so positive predictive skill cannot be assumed.

## Matched author GMST and first physicality check

The corresponding author-released
`MPI-ESM1-2-HR_ssp585_ensemble_avg_tgav.nc` was subsequently acquired by
the same selective extractor from a **1 MiB HTTP range** over the same
outer source. It is 11,194 bytes, SHA-256
`7a279e9f37519a5b9361bb872b9e08b351125a1959f4787429862c82978785f6`,
and contains 86 contiguous annual `tas` values for 2015--2100. Extraction
peak sampled RSS was 37,453,824 B; the file and receipt are in ignored
`data/interim/peeps_published_mpi_ssp585_tgav_20260917/`. The author's
code establishes that this annual predictor is absolute GMST in K, not a
zero-centered warming anomaly.

Using the author's published `slope * annual_tas + intercept` formula,
the bounded diagnostic `scripts/probe_peeps_author_december_prediction.py`
found the following **same-scenario, December-only, native global grid
(land plus ocean)** negative predictions. Four cell/year arithmetic
sentinels per year passed a separate 50-digit Decimal calculation. The
probe's sampled worker RSS was 111,869,952 B. Full machine-readable values,
source hashes, and receipts are in
`data/interim/peeps_published_mpi_ssp585_dec_v2_20260917/prediction_probe.json`.

| Year | Author GMST (K) | Negative cells / 73,728 | Minimum predicted rain (mm/day) |
|---|---:|---:|---:|
| 2015 | 288.19250 | 109 | -0.07051 |
| 2030 | 288.61539 | 13 | -0.00307 |
| 2050 | 289.10880 | 0 | 0.000007 |
| 2100 | 291.37342 | 782 | -1.03158 |

This directly demonstrates that a **published** linear pattern can violate
nonnegative rainfall, even when evaluated with its own scenario's author
GMST. It does not show which of those cells are cropped or how much
crop-area-weighted rain is affected, and it is not an out-of-sample test.
Do not silently clip negatives or declare the published PEEPS fields SCC
ready. Published slopes could still be evaluated as *marginal anomalies*
around a positive, source-matched reference rainfall field, or a positive
published model could be used, but either route requires a preregistered
baseline/physicality and crop-support check.

Next: acquire a minimal matched monthly `pr` set or same-model direct
climate fields, test reference and unit alignment, and quantify failures
on crop support with whole-scenario holdouts before any GIVE pulse use.
