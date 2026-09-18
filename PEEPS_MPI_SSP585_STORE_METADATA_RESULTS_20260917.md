# Published PEEPS MPI source-store metadata gate

The preregistered four-store metadata-only check passed. Exact stores
were taken from the hash-pinned author PEEPS catalog for
MPI-ESM1-2-HR/SSP5-8.5, `r1i1p1f1` and `r2i1p1f1`, monthly `pr` and `tas`.
All four consolidated `.zmetadata` responses were saved in ignored
project interim storage with SHA-256 and GCS-provided MD5 checks. They
declare the same native 192×384 spatial shape, 1,032 monthly positions,
`proleptic_gregorian` calendar, `gn` grid, expected model/scenario/member
metadata, `pr` units kg m-2 s-1 and `tas` units K. DKRZ/DWD metadata
declare CC BY-SA 4.0 terms with producer acknowledgment; derived data
must honor those terms.

| Member | Variable | Time-chunk length | Uncompressed full chunk |
| --- | --- | ---: | ---: |
| `r1i1p1f1` | `pr` | 600 months | 176.95 MB |
| `r2i1p1f1` | `pr` | 235 months | 69.30 MB |
| `r1i1p1f1` | `tas` | 600 months | 176.95 MB |
| `r2i1p1f1` | `tas` | 422 months | 124.45 MB |

These are **allocation bounds from metadata**, not memory-use measurements
for a climate decode. In particular, the first-member chunks are large
relative to the 512 MiB sampled worker cap; do not concurrently decode
members or variables. No coordinate or climate payload was read, so no
claim about exact time coverage, cross-member alignment, rainfall values,
or published-pattern predictive skill follows. The next gate is small
lat/lon/time/bounds coordinate chunks, independently checking exact
2015–2100 monthly coverage and pr/tas/member alignment. After that, read
only one compressed climate chunk at a time under a separate cap and
release it before reading the next.

The metadata worker's sampled peak group RSS was 42,123,264 B, new owned
output 56,507 B, and free disk remained about 133 GiB. Exact source URLs,
hashes, licenses, metadata objects, log and monitor receipt are in
ignored `data/interim/peeps_mpi_ssp585_metadata_20260917/` and
`data/interim/peeps_mpi_direct_catalog_20260917/`. This is a source
feasibility result, **not** an agricultural-yield, welfare or SCC result.

Source: Kravitz and Snyder (2023),
https://doi.org/10.1371/journal.pclm.0000159 ; CMIP6 source terms are
recorded verbatim in each validated metadata object.
