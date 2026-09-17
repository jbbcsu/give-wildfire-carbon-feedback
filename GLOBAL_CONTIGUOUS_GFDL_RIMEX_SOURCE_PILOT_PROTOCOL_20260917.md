# Global contiguous GFDL crop-weather source pilot for RIME-X readiness

Registered September 17, 2026 after the separate two-window weather
diagnostics. This is **source and feature engineering**, not a fitted
GMT response, crop-yield effect, damage or SCC.

## Scientific reason and fixed scope

The published RIME-X centered 21-year indicator conditioning cannot
be evaluated on disjoint 2042--49 and 2092--99 blocks. An earlier
GFDL-ESM4 `r1i1p1f1` SSP1-2.6 2031--2060 pilot established exact
daily-source chronology and crop-feature years 2032--2059 on only
two latitude rows. The six daily ISIMIP3b `20210512` `pr`/`tas`
files, spanning 2031--2040, 2041--2050 and 2051--2060, remain
resident and checksum/content audited. The extension target is the
same 67,420 global `mai_noirr` calendar cells, with 28 consecutive
harvest years 2032--2059 and centered 21-year inputs for 2042--49.
This is one ESM, scenario, crop and irrigation regime and cannot
validate a production RIME-X response or a marginal FAIR pulse.

## Source and memory gates

Preserve the previously validated 2042--49 generic full-grid products
unchanged. For a new crop year, pass the minimal one or two adjacent
decadal source files to the existing bounded crop-year builders; both
builders already check full-file chronology and slice to one year and
ten latitude rows before materializing data. Do **not** concatenate
three full global daily arrays. Verify each resident raw file's exact
size/SHA-512 and existing content-audit receipt before a new year
is accepted. At 2040--41 and 2050--51, require daily timestamp
continuity, matching 360×720 coordinates/units, and exact
cross-decade crop-year support. Each year has 36 serial latitude
tiles, 67,420 season and 202,260 stage rows; stage precipitation
must sum to season rainfall. Use a single feature worker at a time,
<=512 MiB sampled process-group RSS, <=64 MiB new owned output,
<=2 MiB log and >=130 GiB free disk; stop on any breach. Raw files,
interim features and receipts remain Git-ignored. No wildfire file
is read or changed.

First run one 10-latitude-row pilot at each source boundary (harvest
years 2041 and 2051), then independently compare the two overlapping
latitude rows to the exact-key 2032--2059 bounded pilot. Stop if
any feature differs beyond the predeclared floating-point tolerance
used in the existing reconciliation audit. Only after boundary parity
and resource checks pass should missing years be queued serially.
The already audited 2032--2039 and 2042--2049 full-grid products are
immutable/reused. The exact missing-year queue is 2040, 2041,
2050, 2051, and 2052--2059; the 2041/2051 10-row pilot tiles must
be revalidated and reused without replacement. The source choices
are 2031--40 for 2040; adjacent 2031--40 and 2041--50 for 2041;
2041--50 for 2050; adjacent 2041--50 and 2051--60 for 2051;
and 2051--60 for 2052--59. Any change requires a new recorded
protocol before observing outputs.
An independent 28-year full-grid audit must check source hashes,
calendar-cell support, year continuity, tile manifests, physical
bounds, independent daily-cell reconstructions, and stage-to-season
reconciliation. The separate centered-feature operation must use
only 21 real consecutive crop years and reproduce the bounded
two-row centered pilot exactly before any model fit is considered.

The first independent audit stopped on an empty tile because NumPy
does not apply `isfinite` to an object-typed empty groupby result.
The failure receipt and log are retained. The `v2` audit checks the
same source, support, and receipts, but skips only numerical
stage/season comparisons when both tables are proven empty. It
passed 252 new raw-daily sample reconstructions without changing
annual features; its receipt is the downstream gate.

## Predeclared centered-mean gate (added before global centered output)

Only after the independent 28-year global audit passes, run
`scripts/pilot_gfdl_global_centered_21yr_tile.py` first on the
latitude-100--110 tile. For every calendar cell and stage, take an
arithmetic mean of each **annual crop-year feature** over the 21
consecutive harvest years centered on each year 2042--2049. Do not
reinterpret this as a mean of concatenated daily rain: annual
maximum-rainfall and longest-dry-spell indices are averaged as
annual indicators. Require exact crop/calendar keys, stage-to-season
additive reconciliation, and matching same-realization 21-year GMST
from the earlier two-latitude pilot. The two overlapping latitude
rows must reproduce all 5,488 previously registered centered
season rows and 16,464 stage rows to 1e-9 absolute tolerance.
Only after this gate and the <=512 MiB worker RSS, <=64 MiB owned
output and >=130 GiB free-disk checks pass may other tiles be queued.
All outputs remain ignored interim data. Eight highly overlapping
centers from one ESM and one SSP do **not** identify a climate
response; no forced slope, crop impact, damage, or SCC result may
be inferred from this centered-feature operation.

If the latitude-100--110 parity pilot passes, next run the
highest-cell-count latitude-40--50 tile (5,630 calendar cells)
under the same bounds. This is the memory stress test before any
remaining full-grid queue. Only if both pilots pass, process the
other 34 tiles serially, without reopening or altering raw climate
or previously validated annual features. A separate audit must
verify all 36 centered tile receipts and digests, unique calendar
keys in every center year, 8 × 67,420 centered season rows,
8 × 202,260 centered stage rows, and matching 2042--49 GMST.
The eight 21-year windows overlap heavily and must never be
treated as eight independent forced-response observations.

The first centered-pilot attempt stopped before writing centered
outputs because the prior two-latitude reference retained fixed
calendar geometry (`season_days`, stage offsets/days) as unsuffixed
columns, whereas the reusable smoothing code labels their arithmetic
means with `_21yr_mean`. This is a schema difference, not permission
to omit those values. For the reviewed `v2` retry, map each new
geometry mean back to its corresponding old field name solely for
the parity comparison, then require all keys and all values to
match within the original 1e-9 absolute tolerance. The failed
attempt's resource/log files stay preserved in the original
interim directory; the retry writes to a distinct `v2` directory.
The failed pilot used 437,420,032 sampled bytes, already close to
the 512 MiB cap at 3,353 cells; the later largest tile has 5,630.
Therefore the `v2` builder must process at most two latitude rows
in memory at once, write row groups to one parquet file per output,
and reconcile every chunk before writing the final receipt. This
changes only execution granularity, not the 21-year window or
feature definitions. The 512 MiB sampled RSS limit remains fixed.

No global damage or SCC claim, forced rainfall-per-K slope, or
generalization beyond GFDL SSP1-2.6 is authorized by this pilot.
