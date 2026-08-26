# nClimGrid-Daily 1981--2019 bulk acquisition

This is the fail-closed raw-weather acquisition gate for the U.S. county
validation. It acquires no period outside January 1981--December 2019 and does
not construct county exposure, estimate a yield response, calculate damages,
or authorize an SCC input.

## Executed acquisition status (2026-08-26)

The authorized full run completed with **468/468 objects validated** and zero
remaining objects. The objects contain 27,857,685,556 bytes; the final run
reported 449 newly downloaded objects and revalidated 19 already manifested
objects. The ignored local JSONL manifest contains one record per month with
the frozen inventory digest, current HTTP identity, local SHA-512, and passed
NetCDF/schema/calendar receipt. This completion statement is an acquisition
result only. It does not report a county exposure, a climate--yield
relationship, damages, or an SCC estimate.

The durable manifest's origin-status composition is 461
`downloaded_and_validated` objects and 7
`adopted_existing_and_validated` objects. This is consistent with the final
invocation counters above: 12 of its 19 revalidated checkpoints had been
downloaded in earlier bounded invocations, while 7 had been safely adopted.

The completion prose and tracked HTTP catalog alone were not sufficient
publication provenance because neither exposed the 468 acquired content
digests. The deterministic tracked receipt
`data/provenance/nclimgrid_daily_1981_2019_content_receipt.json` closes that
specific gap without committing the ignored manifest or raw NetCDF bodies. At
the completed snapshot, the source manifest is 1,403,481 bytes with SHA-512
`3e46415d4bba94362a46c6db536c756e2cc55f73624eee977b67fef63955d03deae832b35c553a8e1bcb1f758e020eb5020fa8e087979e0372f3e47c7d17ac5f`.
The receipt itself is 333,635 bytes with SHA-512
`f57448934de8710fb877fe3670ba3f4ea99dd211ada2e30b35d24c1563160106c2a10565747ceec66c37775f3502b0744955ddf51e5a22c4b0e8265845091a14`.
Its canonical chronological object-record envelope is SHA-512
`9234b635a39b94312accafa344c884a450824b9b72d5d730724f798601ae8e51445e9c600dbe946f9e58366e4bc3c3b5b2161a97c5844ccfb9887734d8154893`.

## Fixed scope and storage

The only accepted catalog is the complete tracked
`data/provenance/nclimgrid_daily_1981_2019_http_inventory.csv`. It contains 468
canonical monthly NCEI objects (39 years times 12 months). At the reviewed
snapshot its SHA-512 is
`4617d02b923705f15b32ddcad8a2211d2ae3fc25dea29f807ba886618b19255b3d9210806a0edfc55e1c0338ab52001ed3f067e8aa55ea88a70c9f9cd88dd6ae`.
The executable hard-pins this digest and the reviewed product/license-record
digest; a structurally complete but modified replacement is not accepted.

The sum of pinned HTTP `Content-Length` values is **27,857,685,556 bytes**:
27.858 decimal GB or 25.944 GiB. The largest monthly object is 65,232,982
bytes. Reserve at least 30 GB for the raw snapshot and filesystem overhead;
county weights, feature panels, temporary processing space, and backups need
additional storage. During acquisition the utility adds at most one monthly
`.part` file beyond completed raw objects.

## Commands

Validate and adopt already-present monthly smoke files without issuing a data
`GET`:

```bash
./.venv/bin/python us_county_validation/scripts/acquire_nclimgrid_daily_bulk.py \
  --max-new 0
```

Start with a bounded twelve-object acquisition:

```bash
./.venv/bin/python us_county_validation/scripts/acquire_nclimgrid_daily_bulk.py \
  --max-new 12
```

Repeat that command until `remaining_objects` is zero. The explicit one-shot
command for every still-missing object is:

```bash
./.venv/bin/python us_county_validation/scripts/acquire_nclimgrid_daily_bulk.py \
  --all
```

There is intentionally no implicit full-download default: exactly one of
`--max-new N` or `--all` is required. `--max-new` counts only new network
downloads; validation/adoption of an already-present exact object does not use
the allowance. The default `--attempts 3` applies separately to each current
identity `HEAD` and each monthly `GET`. A retryable 429/5xx response, transport
failure, or cleanly truncated response discards `.part` and restarts that month
from byte zero. Redirects, identity drift, unexpected content encoding, excess
bytes, local write failures, and content-validation failures remain
non-retryable.

## Integrity and resume contract

For each manifested or newly selected month, the command first makes a current
`HEAD` request and requires the canonical URL, byte length, ETag,
Last-Modified value, and `application/x-netcdf` content type to equal the
complete reviewed inventory. A new `GET` must repeat that exact identity and
must not redirect or apply content encoding.

The response is written to the exact `<object>.part` path. Validation order is:

1. exact byte length;
2. locally computed SHA-512;
3. exact NetCDF variables, dimensions, metadata, coordinate orientation,
   embedded license, day-label semantics, and requested month's daily
   calendar coverage.

Only after all three gates pass is `.part` atomically renamed to `.nc`. Only
after that promotion is
`data/raw/us_county/nclimgrid_daily/BULK_ACQUISITION_MANIFEST.jsonl` atomically
updated. Both the raw directory and manifest are gitignored.

Resume is at the monthly-object boundary. A validated manifested file is
rechecked against its manifest SHA-512 and NetCDF contract; it is never
silently overwritten. An interrupted `.part` is not byte-range resumed because
NCEI does not provide an independent content checksum for authenticating its
prefix. The stale part is discarded and that one roughly 55--65 MB month is
restarted. Completed months remain durable checkpoints. A crash after atomic
file promotion but before manifest update leaves an unmanifested exact file;
the next run verifies its upstream identity, bytes, SHA-512, and schema before
adopting it, without inventing a historical retrieval time.

Every resume invocation rechecks **all** previously manifested objects before
adding a new one: current upstream identity, local byte length, the full local
SHA-512, and the NetCDF/schema/calendar contract. This is intentionally more
work than trusting manifest text alone. It detects local mutation, partial
sync/storage corruption, missing bodies, and upstream drift before a mixed or
stale raw snapshot can be treated as validated. Consequently, `--max-new`
bounds new network bodies, not the amount of verification I/O; later resumes
will reread and reopen all completed monthly files.

The locally computed SHA-512 is a reproducibility pin for the acquired local
snapshot, not a publisher-supplied checksum and not an independent proof of
remote content. Its evidentiary role is paired with HTTPS, exact HTTP identity,
and content/schema/calendar validation. Any upstream identity drift, missing
manifested file, local hash mismatch, incomplete inventory, malformed or
duplicate manifest entry, redirect, truncated response, schema change, or
calendar mismatch stops the run without updating the manifest.

## License, provenance, and use boundary

Source: NOAA NCEI nClimGrid-Daily v1.0.0,
[product page](https://www.ncei.noaa.gov/products/land-based-station/nclimgrid-daily),
[dataset DOI](https://doi.org/10.25921/c4gt-r169), and
[v1.0.0 user guide](https://www.ncei.noaa.gov/data/nclimgrid-daily/doc/nclimgrid-daily_v1-0-0_user-guide.pdf).
The reviewed NetCDF says `no restrictions`; the project records the data as
U.S. federal-government data with SPDX `NOASSERTION`, because neither the
reviewed product page nor file supplies a more specific SPDX license. Do not
silently relabel it CC0. Raw NetCDF files remain local and are not committed.

The acquisition manifest binds every file to both the complete HTTP-inventory
SHA-512 and the reviewed product/license record SHA-512. It preserves exact
remote identity, local byte length and SHA-512, validation timestamp, file
status, schema/calendar receipt, source links, license assertion, and explicit
false gates for relationship estimation, damage estimation, and SCC use.

NCEI documents that product inputs can be updated without a version change and
recommends spatial/temporal aggregation rather than interpreting one grid cell
on one day. The reviewed limitations also include slight dry bias from
gridding/smoothing, larger precipitation errors in mountains and heavy events,
24-hour periods ending early in the labeled morning, and unresolved farm-scale
microclimates. Acquisition integrity does not eliminate these scientific
measurement limitations; weather-product and spatial-weighting robustness
checks remain required downstream.

## Deterministic tracked content receipt

`scripts/export_nclimgrid_daily_content_receipt.py` is entirely offline. It
strictly validates the ignored manifest against the pinned 468-row HTTP
inventory and reviewed product/license record, requires a unique chronological
record for every month, verifies the 27,857,685,556-byte aggregate, and emits a
whitelisted JSON projection. The projection retains every canonical object
name and URL, `Content-Length`, ETag, Last-Modified value, content type, local
SHA-512, and exact monthly calendar. The common NetCDF variables, dimensions,
title, product version, embedded license, and day-label semantics are recorded
once. SHA-512 envelopes bind both the chronological object records and the
entire receipt payload; the byte-for-byte ignored-manifest SHA-512 is also
included and hard-pinned by the exporter. Thus a valid-looking substituted
local hash cannot be accepted merely by regenerating the receipt. No
generation timestamp is added, so identical inputs produce identical receipt
bytes.

Regenerate the receipt from the ignored manifest:

```bash
./.venv/bin/python \
  us_county_validation/scripts/export_nclimgrid_daily_content_receipt.py
```

Fail unless the tracked receipt is the exact canonical projection of the
current ignored manifest:

```bash
./.venv/bin/python \
  us_county_validation/scripts/export_nclimgrid_daily_content_receipt.py \
  --check
```

For the strongest local audit, add `--verify-local-files`. That option rereads
all 27.9 GB, recomputes every local SHA-512, and reruns every NetCDF
schema/calendar check without making a network request. The completed snapshot
passed this full 468-object, 27,857,685,556-byte offline revalidation on
2026-08-26. It does not refresh or claim current upstream HTTP state.

Run the adversarial receipt suite with:

```bash
./.venv/bin/python \
  us_county_validation/scripts/test_export_nclimgrid_daily_content_receipt.py
```

The suite rejects valid-looking content-hash substitution relative to the
source manifest, missing months, record reordering, NetCDF-schema mutation,
noncanonical serialization, unexpected fields/path leakage, and any true
relationship, causal, damage, or SCC gate.

Run the fully offline mocked integrity suite with:

```bash
./.venv/bin/python \
  us_county_validation/scripts/test_acquire_nclimgrid_daily_bulk.py
```

The test covers the complete 468-object scope, exact real storage footprint,
stale-part restart, atomic promotion and manifesting, zero-download resume,
same-length local tampering, adoption without fabricated retrieval time,
upstream identity drift, bounded full-object retry after truncation, NetCDF metadata change,
incomplete inventory, and manifest-provenance drift. It does not download the
27.9 GB dataset.
