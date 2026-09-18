# Published PEEPS monthly rainfall: source-matched MPI reconstruction

## Status and scope

The preregistered 2015/2100, twelve-month comparison is complete and its
saved-array arithmetic independently audited. This is an **in-sample**
reconstruction of MPI-ESM1-2-HR SSP5-8.5 precipitation used in fitting the
published PEEPS patterns, not an out-of-scenario forecast, crop-year
exposure, yield effect, damage, or SCC input. The published source is
[Kravitz and Snyder (2023)](https://doi.org/10.1371/journal.pclm.0000159)
and the [author release](https://doi.org/10.5281/zenodo.7557622).

The comparator is the month-by-month arithmetic mean of the author's two
qualified direct-CMIP6 MPI SSP5-8.5 `pr` members, not one arbitrarily chosen
member. Source chunks were GCS-CRC32C checked and decoded in four fresh
bounded workers. Only small crop-center arrays were retained; raw climate
chunks were not stored. The published monthly coefficient archive was
whole-archive-MD5 verified before its twelve small MPI files were selectively
retained. Predictions used the released absolute-GMST series and author
linear formula, with the exact calendar-month duration. The fixed MIRCA2000
rainfed-maize *nearest-center* proxy has 30,821 positive-area cells and
108,086,337 ha. It is neither crop-field areal overlap nor a planting/
harvest calendar.

## Results

| Year | Published negative-month area, any month | All-area annual bias, published minus direct | All-area annual RMSE | Within-year physically valid area | Month-share TV error on that area |
|---|---:|---:|---:|---:|---:|
| 2015 | 2.856% | −29.961 mm | 131.843 mm | 97.144% | 0.126917 |
| 2100 | 9.879% | −26.084 mm | 147.021 mm | 90.121% | 0.142917 |

The direct two-member field has no negative crop-center monthly rainfall in
these two years. The all-area error intentionally **includes** invalid
negative published values rather than silently clipping them. The
month-share score uses only locations with nonnegative months and positive
annual totals in that year; its support therefore differs between years.
Every individual-month negative-area, mean, bias, MAE, and RMSE number is
preserved in the ignored primary `result.json`.

To avoid treating the differing year-specific valid areas as a temporal
comparison, a separately labeled **post-result** diagnostic intersects
the valid locations across both years: 24,472 centers, 88.266% of mapped
area. On this one fixed area, the direct annual-mean rainfall changes
by +34.172 mm from 2015 to 2100 while the published PEEPS level changes
by +43.612 mm. The difference in changes is +9.440 mm. The 2015/2100
published-minus-direct annual biases are −30.454/−21.014 mm and
month-share TV errors 0.128146/0.143390 on the same area. These are
climate-input diagnostics, not estimates of climate-change impacts on
agriculture. The point-center sample and fixed support cannot establish
global cropland-area representativeness.

## Integrity and decision

The independently coded `scripts/audit_peeps_mpi_source_reconstruction.py`
recomputed 214 reported month/year scalar metrics with `math.fsum`,
rechecked the two-member source arithmetic and crop-center map, and passed
three synthetic tests. Its fixed-two-year-support numbers are additional
post-result diagnostics. It does **not** re-decode all published and direct
cloud source fields; the separately retained primary source/checksum receipts
provide that provenance. Primary saved-array SHA-256:
`f1556e24ad9e843f064c095474b0d89954ed621d91cc51f006e63b65cb87b08d`.
Primary report SHA-256:
`f5aeaef121ef712522f6ad4ada66acab4f060e5d60e57bdaf5b479c33b7727fa`.
The v2 audit is in ignored
`data/interim/peeps_mpi_source_reconstruction_audit_v2_20260918/result.json`.

The first monolithic and second multi-chunk-in-one-process attempts were
stopped at 537.54 and 539.21 MB RSS. Both failures and their logs remain
retained. The amended four fresh source workers stayed below 512 MiB; the
final independent audit peaked at 70.07 MB. Each new owned output was below
64 MiB and the >=130 GiB free-disk floor was preserved.

**Decision:** the raw linear monthly PEEPS levels are not eligible as GIVE
rainfall forcing because they predict negative rainfall on crop support.
The benchmark remains informative but not promoted. Next compare a
physically valid published/baseline-anomaly implementation with a different
scenario or model, then evaluate crop-calendar amount/timing and direct
daily-extreme consistency before coupling to yield responses. No yield,
monetary damage, or SCC result follows from this comparison.
