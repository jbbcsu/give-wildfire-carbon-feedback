# Frozen twenty-year PEEPS-versus-source rainfall-climatology diagnostic

Registered before decoding any new source chunks or scoring the twenty-year
means. This follows the invalid raw-level and invalid anchored-anomaly
findings. It tests whether averaging many years changes the published
monthly pattern's source-reconstruction properties; it does **not** erase
invalid individual-year rainfall or create an out-of-sample evaluation.

Use the already hash-pinned PEEPS twelve MPI-ESM1-2-HR SSP5-8.5 monthly
coefficient files, author absolute-GMST series, two qualified direct
MPI SSP5-8.5 `pr` members, and fixed 30,821 MIRCA2000 rainfed-maize
nearest-center mapping from
`PEEPS_MPI_SSP585_RECONSTRUCTION_PROTOCOL_20260917.md`. The early
calendar-year period is **2015–2034** and the late period **2081–2100**,
exactly twenty complete years each. These endpoints are selected to
separate periods while staying inside the author's released 2015–2100
GMST path; they are not chosen using twenty-year results. Treat each
year equally. For each member/year/month, convert native `pr` flux to
that calendar month's mm using actual month length; average two members
equally, then twenty years equally. Apply each published month's linear
coefficient to the author's GMST for **each individual year**, convert
to mm with that year's month length, and average over the same years.
Do not substitute a period-average GMST before month-length conversion.

Only six frozen GCS Blosc time chunks cover both periods: `r1i1p1f1`
chunks 0 and 1, and `r2i1p1f1` chunks 0, 1, 3 and 4. Decode each chunk
in a fresh, one-worker-at-a-time bounded job; verify its source metadata,
content length, GCS CRC32C/MD5 when present, decoded size, finite/nonnegative
native rainfall, and fixed crop-center map. Save only twelve-by-center
monthly partial sums and month counts, not the raw chunks. Expected merged
count is exactly twenty years per month/member/period. Independent audit
must bind all six source receipts and recheck partial-sum/count arithmetic
where feasible. No source chunk or credentials may be committed.

On **all** fixed crop-center area, report both periods' published negative
monthly-climatology area and the late-minus-early direct/published annual
mean changes, their bias, spatial RMSE, annual-change sign agreement, and
the amount-versus-within-year redistribution decomposition of monthly
*climatology changes*. Month-share errors may be reported only on a
clearly identified common positive-level support. Compare exact support
and physicality with the single-year diagnostic; do not present a lower
climatology error as held-out or proof of forcing validity. No crop-year
calendar, daily extremes, yield, damages, or SCC are estimated here.

Post-v1 implementation clarification, before publication: the first
primary score used one direct/published-valid support **per period**;
these two supports need not be identical. Preserve that v1 receipt, and
add a separately labeled fixed intersection of positive direct/published
months across **both** periods. Report its area coverage and recompute
both period month-share distances on it. This is a support correction,
not a model refit or a new skill-claim selection. Retain the original
period-specific numbers for audit but do not compare them as a temporal
skill change.

One numerical worker at a time; sampled group RSS <=512 MiB, each owned
new output <=64 MiB, free disk >=130 GiB, log <=2 MiB. Stop and retain
receipt on any resource or source-integrity failure, never silently
lower a gate or skip a chunk.
