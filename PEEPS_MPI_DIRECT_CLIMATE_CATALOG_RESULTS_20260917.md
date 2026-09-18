# Source-matched direct-climate catalog for published PEEPS MPI patterns

This is **catalog discovery only**, not decoded climate, a model holdout,
or an agricultural/SCC estimate. The preregistered
`PEEPS_MPI_DIRECT_CLIMATE_CATALOG_PROTOCOL_20260917.md` was executed with
the authors' frozen `pangeo_table.csv`, streamed but not saved. Its
22,939,452 bytes matched the frozen Git-blob SHA-1
`c1ce147ecdd0eac37648a4b0473f1589bf411c1f` and independently
recorded SHA-256
`631ae6453fba8950e1f369d5fbd1199a4252c932c8ffa42372fe9d84d12e6304`.
The catalog contains 182,459 rows. The exact MPI-ESM1-2-HR Amon `pr`/`tas`
historical/SSP5-8.5 selection has 24 rows:

| Experiment | `pr` members | `tas` members |
| --- | ---: | ---: |
| Historical | 10 | 10 |
| SSP5-8.5 | 2 | 2 |

For SSP5-8.5 both variables list `r1i1p1f1` and `r2i1p1f1`; the ten
historical members are `r1i1p1f1` through `r10i1p1f1`. The exact store
URIs and hash/monitor receipts are in ignored
`data/interim/peeps_mpi_direct_catalog_20260917/catalog.json`.
This establishes a concrete direct-CMIP6 source set for comparing the
published pattern with its training-source family. It does **not** establish
that all 24 stores are live, complete, on an identical grid/calendar, or
passed the author's completeness rule; those require metadata/coordinate
checks before payload reads.

The pinned author `helpers.py` first keeps `p1` members and, after requiring
at least 85 annual cycles in future scenarios, pointwise averages all
qualifying stores before fitting patterns. Thus comparing PEEPS
`ensemble_avg` against just one SSP5-8.5 realization would conflate member
variability with emulator error. For the initial source-matched SSP5-8.5
comparison, verify and combine the two qualifying `pr` realizations, and
use the author's released ensemble-mean GMST predictor; do not assume an
individual realization uses that exact predictor. See the frozen source
`data/interim/peeps_monthly_source_20260908/helpers.py`, lines 198–349.

The catalog worker's sampled peak group RSS was 33,046,528 B, with 10,896
B new owned output; free disk remained about 133 GiB. No raw climate
payload or full CSV was retained. Next: inspect the four SSP5-8.5 store
metadata and coordinates within resource bounds, then decode a small
predeclared source-matched month/year sample and compare observed ensemble
rainfall with published predictions. A *separate* historical positive
baseline is needed to evaluate anomaly anchoring. Keep this raw CMIP6
benchmark distinct from bias-adjusted daily ISIMIP crop forcing.

Primary source: Kravitz and Snyder (2023),
https://doi.org/10.1371/journal.pclm.0000159 ; frozen source code at
https://github.com/JGCRI/linear_pattern_scaling/tree/d4ed4c479f5399015708135558daa382bbbc2da0 .
