# Preregistered PEEPS-source MPI SSP5-8.5 metadata gate

Use only the four exact `MPI-ESM1-2-HR`, `ssp585`, `Amon`, native-grid
`r1i1p1f1`/`r2i1p1f1` precipitation and temperature stores from the
Git-blob-verified author PEEPS source catalog. Check the catalog SHA-256
before requesting anything. Fetch each store's consolidated `.zmetadata`
via its fixed Google Cloud Storage HTTPS translation with identity
encoding and a 2-MiB per-response ceiling. Verify server MD5 if supplied,
record SHA-256, exact URL, byte size, license and producer fields.

Require root source/experiment/member/grid/table identity, expected
variable units (`pr` kg m-2 s-1, `tas` K), rectangular `time,lat,lon`
layout, positive native coordinate dimensions, and a declared time
calendar. Record chunk shape, dtype and uncompressed bytes, but read no
climate or coordinate payload in this step. Do not assume all four share
time coverage/coordinates until those arrays are separately decoded and
checked. Reject response drift, missing member, duplicate key, unexpected
host, oversize metadata or missing license.

Run one monitored worker, sampled RSS <=512 MiB, new owned output <=64
MiB, log <=2 MiB, free disk >=130 GiB. Retain only the four metadata
objects and a small manifest in ignored project interim storage. This
is a source feasibility/identity gate, not a pattern-validation, yield,
damage or SCC result.
