# Preserve the disk cap while distinguishing unrelated filesystem writes

Two small full-grid regression-test attempts were stopped by the volume-wide
starting-free-space-minus64MiB check. Logs and resource receipts are retained;
no crop builds had begun. A subsequent read-only probe with no analysis job
running observed free disk fall from158.46756to158.46595GiB in1.2seconds.
This demonstrates filesystem changes outside an analysis run, not their cause.
Dropbox processes were present; that does not establish which process wrote.

For the next bounded tests/builds, use explicit owned-output and job-scratch
paths to monitor this job's incremental disk use, including its log and a
128KiB receipt reserve. Keep the same64MiB cap,1024MiB sampled process-group
RAM and130GiB absolute free-disk floor. The floor applies to the whole volume;
the64MiB accounting applies to this job's authorized additions. Neither crop
completeness nor scientific promotion criteria change. Other applications'
writes are not silently classified as this project's data acquisition.

Set a fresh ignored scratch directory as TMPDIR, disable Python bytecode writes,
and reject overlapping/broad watched roots or symlinks. All explicit outputs
must be watched; source data must already be resident. This is sampled monitoring,
not a kernel quota. Builders additionally check their own file totals at each
output boundary. Do not use this mode for arbitrary commands writing outside
the declared paths or for evicted raw hydration. Raw inputs, failures and
derived data are not deleted. Report interrupted runs separately from successes.
