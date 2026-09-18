# Preregistered source-matched MPI coordinate check

Use only the four GCS-MD5-verified `.zmetadata` records from
`PEEPS_MPI_SSP585_STORE_METADATA_RESULTS_20260917.md`, with source manifest
hash frozen in the implementation. Fetch only their `lat`, `lon`, `time`
and declared time-bounds compressed Zarr chunks, each <=2 MiB, verifying
GCS MD5 if supplied and the metadata's compressor/shape/decoded byte count.
Retain each tiny chunk and its SHA-256 in ignored interim storage. Read no
`pr` or `tas` payload.

Require strictly increasing finite spatial coordinates; latitude in
[-90,90], longitude in [0,360); exact 1032 consecutive month IDs from
January 2015 through December 2100, no duplicates/gaps, with declared
proleptic-Gregorian calendar and full adjacent monthly bounds. Require all
four stores' lat/lon and month IDs to agree, and match the published PEEPS
MPI coefficient grid at absolute tolerance 1e-10 degrees, zero relative
tolerance. Record exact-bit equality separately; do not relax tolerance
without a documented failure and review.

Use one worker under sampled <=512 MiB RSS, <=64 MiB new owned output,
<=2 MiB log and >=130 GiB free disk. A passed coordinate check is not a
climate-value/ensemble/pattern validation, crop exposure, damage or SCC.

## Transparent v2 amendment after retained first-run failure

The first run failed its *exact-bit* across-member latitude equality at
the second store, before inspecting the remaining two. An independent
read-only decode of the two retained latitude chunks found 18 differing
entries out of 192, maximum absolute difference 2.842170943040401e-14
degrees; all 384 longitudes matched bitwise. This is below the already
preregistered 1e-10-degree PEEPS-grid tolerance and consistent with
floating serialization, not a meaningful displaced grid. The v2 rule
requires all four latitudes/longitudes to agree at **absolute 1e-10 degree,
zero relative tolerance**, while still recording exact-bit equality and
maximum difference. Month IDs must remain **exactly** equal. The v1 log,
monitor receipt and partial ignored output remain retained and are not
promoted. Run v2 to a fresh ignored directory.
