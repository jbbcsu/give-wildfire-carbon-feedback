# Working before external storage arrives

Use retained derived panels. No bulk reacquisition of the evicted daily
climate files. Process one partition/job at a time, select only required
columns, stream reductions, and checkpoint compact outputs. Disk-backed
computation still needs free disk; swap is not a substitute for bounding work.

Launch analysis jobs through `scripts/run_bounded_job.py` using the project's
Python environment. Pass a new `--receipt`, new `--log`, `--max-mib 1024`,
and then `--` followed by the analysis command. Numerical libraries are
restricted to one thread. Run `scripts/test_run_bounded_job.py` to test the
monitor, including descendant memory and log overflow termination.

The default free-space floor is 150 GiB, preserving the acquisition reserve.
While already below that reserve, a separately reviewed existing-data job
with tiny outputs may explicitly set `--min-free-gib` to the freshly measured
starting free space minus at most 64 MiB. Never use this exception for bulk
downloads or large temporary arrays. Resource checks apply to the receipt's
filesystem; put receipt, log and all outputs on the same filesystem.

The launcher checks combined process-group RSS every 0.2 seconds and kills
only its own job group if RSS, log or disk budgets are exceeded. It records
the outcome and sampled peak. Process visibility is required; if unavailable,
it fails before launch. This is not a kernel-enforced allocation cap: a fast
spike can occur between samples. Descendants must not detach from the group.
It does not cap the Codex app, other apps, filesystem cache or total memory
pressure. Keep outputs to the conversation small and avoid concurrent jobs.

Validated September 4 example: 24 U.S. fits completed at 206.7 MiB sampled
peak RSS with no new downloads. These analyses do not require a new drive.
The larger global pipeline still requires staged I/O and a storage preflight.
Existing scheduled tasks are not automatically changed by adding this file;
their launch commands must use this wrapper to receive these protections.
