# PEEPS-source MPI coordinate alignment: validated v2 gate

The first strict-bitwise check **failed** on the second SSP5-8.5 MPI
member's latitude. Its failed log/monitor and partial ignored output are
retained. An independent decode found 18 of 192 latitudes differing by at
most 2.842170943040401e-14 degrees, with longitude bitwise identical.
The protocol was amended transparently to use absolute 1e-10-degree,
zero-relative-tolerance coordinate equivalence (the same frozen tolerance
already specified against the published PEEPS grid), while keeping exact
month IDs. The v2 run was made to a fresh ignored directory and passed.

All four `pr`/`tas` member sources have 1,032 consecutive monthly positions
from January 2015 through December 2100, proleptic-Gregorian calendar,
full contiguous monthly time bounds and identical month IDs. Their
192×384 spatial coordinates are within 2.85e-14 degrees of one another
and the published PEEPS MPI coefficient grid. Member `r1i1p1f1` matches
the coefficient grid bitwise; `r2i1p1f1` does not, but passes the frozen
tolerance. Every compressed lat/lon/time/bounds chunk was bounded to
2 MiB, decoded against its metadata, and had source URL, SHA-256 and
GCS-provided MD5 recorded. **No precipitation or temperature climate
value chunk was read.**

The successful v2 worker used 145,915,904 B sampled peak group RSS and
35,594 B new owned output; free disk remained about 133 GiB. Receipts,
compressed coordinate chunks, and per-member exact/tolerance flags are
in ignored `data/interim/peeps_mpi_ssp585_coordinates_v2_20260917/`.
The retained first failure is in
`data/interim/peeps_mpi_ssp585_metadata_20260917/coordinate.log` and
`coordinate_monitor.json` plus its unpromoted partial output directory.

This establishes safe grid/time alignment for an **ensemble-mean direct
climate comparison**, not predictive agreement. Next: preregister a
bounded sample of same-source MPI monthly `pr` values from both members,
decode serially, calculate their pointwise ensemble mean and compare
published PEEPS predicted monthly levels on crop support, explicitly
reporting negative predictions and out-of-GMST-range behavior. The
historical positive-baseline anomaly design is a separate subsequent
gate. Because the SSP5-8.5 source contributed to the fitted published
SSP5-8.5 pattern, this first comparison is an **in-sample reconstruction
diagnostic**, not an independent holdout. A different scenario/member
design is needed for an actual holdout. No crop response, damage or SCC
estimate follows.

Primary published model: Kravitz and Snyder (2023),
https://doi.org/10.1371/journal.pclm.0000159 .
