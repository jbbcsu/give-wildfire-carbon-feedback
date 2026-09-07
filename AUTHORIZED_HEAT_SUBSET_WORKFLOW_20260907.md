# Ready-to-run bounded cutout workflow; approval still pending

September7,2026. `scripts/run_authorized_heat_subset_pilot.py` implements the
single-file route in `LOW_STORAGE_HEAT_SUBSET_PILOT_20260907.md`. It has not
been used to acquire real climate data. Its tests use synthetic buffers and
in-memory arrays with network access patched to fail.

## Authorization and resource boundary

The CLI requires `--authorization-file` and a new `--out-dir` inside this
project's ignored `data/interim`. Do not create a purported approval record
until the user actually approves the pending one-file exception. That record
must contain the exact approval quotation, timezone-aware approval timestamp,
`user_approved: true`, `scope: one_isimip_heat_cutout_pilot`, the registered
config's SHA-256, the completed job ID and
`additional_disk_budget_bytes: 67108864`. Keep it in ignored local data, not
in an environment file or in Git. An approval for another file or budget is
not interchangeable. Existing config/receipts are not rewritten to claim
authorization. No authorization record was created during development.

Run the CLI only inside `scripts/run_bounded_job.py` with a fresh resource
check, at most1GiB sampled group RSS, one numerical thread, and disk reserve
equal to starting free space minus64MiB. The pipeline additionally checks
its directory occupancy and free space before each streamed write and between
subprocesses. It reserves128KiB inside that budget for failure bookkeeping.
The archive must be at most16MiB and match the saved12,891,438byte length and
ETag exactly. Archive plus uncompressed climate member must leave8MiB for
small feature products, receipts and logs. No package installation, full-grid
climate download, deletion or automatic acquisition retry is included.

## Sequential execution after actual approval

1. Validate approval/config/job identity, the retained crop-calendar SHA-512
   and the matching existing GFDL/SSP126 maize/noirr season-input SHA-256.
2. Recheck the official catalogue's public source contract and completed job.
   Reject changed archive identity or HTTP redirects before consuming payload.
3. Stream the archive in at most256KiB chunks, enforcing exact byte count and
   computing its own SHA-256. Reject truncation or overrun; preserve partials.
4. Inspect ZIP member paths, duplicates, types, encryption and declared sizes.
   Permit exactly one NetCDF and only small text/JSON/Markdown sidecars. Reject
   traversal, absolute paths, links and special files. Extract only the NetCDF
   to a fixed safe filename, without `extractall`; stream and hash its bytes.
5. Check variable/dimension identity, exact latitude and longitude centers,
   Gregorian calendar, all3652daily dates in2041–2050 and supported temperature
   units. Scan365day blocks and reject nonfinite values without imputation.
6. Immediately construct maize/noirr2042–2049 seasonal heat at29C, validate it,
   construct three-stage heat, validate it and reconcile stage sums and means
   with the seasonal output. Exact-coordinate calendar selection is required.
7. Require exact crop/grid/year and planting/maturity/season-length agreement
   with the retained same-scenario rainfall seasons. Record output hashes,
   code hashes, actual sizes, source lineage and successful reconciliation.

The workflow runs one child command at a time inside the monitored process
group and does not detach. Failed commands stop the chain and preserve a
failure receipt and partial files. A restart must inspect those files; the
CLI refuses to overwrite or automatically redownload into an existing run
directory. The cutout remains a server-derived file: its child hash cannot
verify the full parent payload. A real archived-output content/feature success
has not yet occurred, and synthetic tests must not be presented as one.

## Test coverage and limits

`scripts/test_authorized_heat_subset_pilot.py` tests approval matching and
missing/false/incorrect authorization; chunk sizes, exact bytes, budget failure
and no overwrite; unsafe ZIP paths, duplicate members, links, encryption and
oversized payloads; and the date/grid/variable/finite-value NetCDF contract on
in-memory synthetic arrays. These tests do not exercise a real network
transfer, inspect the real ZIP or establish server-content integrity. The
earlier full-grid/cutout parity and stage-heat integration tests cover the
unchanged downstream numerical builders. Actual content reconciliation is a
required first-run step, not an assumed result.

All four test groups pass, including the final explicit-Boolean approval
check. The final monitored run took0.47seconds and sampled75.06MiB peak group
RSS; brief sampling can miss higher peaks and is not a kernel cap. The earlier
passing version sampled104.14MiB. Logs and resource receipts have prefixes
`outputs/authorized_heat_subset_synthetic_tests_20260907` and
`outputs/authorized_heat_subset_synthetic_tests_v2_20260907`. Neither run
invoked the acquisition CLI or accessed a network endpoint.

One file/one calendar does not complete the balanced multi-model joint-heat
basis. It does not establish irrigation benefits, climate-to-yield transport,
long-run adaptation, economic welfare or SCC. The future temperature
extrapolation limits already measured in
`FUTURE_WEIGHTED_PRECIPITATION_RESULTS_20260907.md` remain unresolved.
