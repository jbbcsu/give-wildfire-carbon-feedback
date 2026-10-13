# Legacy-to-updated agriculture replacement stage

Status date: 13 October 2026.

## Source finding

The published Moore et al. archive contains a direct legacy-versus-updated
agriculture comparison in `analysis/03_ag_scc_evolution.jl`. Its RFF-SP
full-uncertainty branch constructs legacy agriculture with
`MimiGIVE.get_model()` and updated agriculture with the paper's `get_model()`,
disables other damage sectors, resets the same random seed, and reports the
agriculture partial SCC for each model. The configuration is therefore
available; no literature reconstruction is needed.

The local runner freezes both versions to the existing replication contract:
2025 CO2 pulse, horizon 2300, pulse size `1e-4`, random FaIR and RFF-SP draws,
seed 24523438, the paper's 2% Ramsey schedule, 2020 USD/tCO2, Julia 1.12.5,
and one thread. Legacy and updated models run sequentially.

## 100-draw execution stage

The first code-path stage completed for both configurations:

| Model | Mean | Monte Carlo SE | 5th percentile | Median | 95th percentile |
|---|---:|---:|---:|---:|---:|
| Legacy GIVE agriculture | 92.9325 | 12.2058 | -22.9073 | 55.1860 | 293.1851 |
| Updated Moore agriculture | 28.2381 | 2.4047 | 2.3470 | 24.0700 | 77.1050 |

The updated-minus-legacy difference of means is -64.6944 2020 USD/tCO2 in
this stage. It is **not** a promoted replacement delta: 100 draws are
insufficient, especially for the legacy distribution, whose Monte Carlo
standard error is 13% of its mean.

The same seed does not make draw-level subtraction valid. Legacy agriculture
uses 3 coefficients across 16 FUND regions, while updated agriculture uses 7
country-level coefficients. The Monte Carlo definitions therefore consume and
transform random variables differently. Only separately converged means may
be differenced; a delta interval requires an explicitly justified joint
coupling or independent uncertainty calculation.

The operating-system timing wrapper did not return a peak-RSS field because
its macOS `sysctl kern.clockrate` query was sandbox-blocked. The runner now
has a same-process memory-guard wrapper that records Julia's peak RSS and fails
above 512 MiB on future stages. This completed run cannot be retrospectively
certified against the cap and is not used as a promotion result.

A two-draw guard probe then showed that process separation does not solve the
current cap: the legacy branch alone reached **2,531,426,304 bytes** peak RSS
(2.36 GiB), compared with the **536,870,912-byte** limit, and failed before
writing an eligible branch summary. The combined two-version probe also failed
the same cap. This is a runtime-memory blocker, not evidence against the source
comparison. No 1,000- or 10,000-draw run was launched.

## Frozen advancement route

1. First move the source execution to an authorized worker with at least the
   demonstrated 2.36 GiB legacy-branch requirement, or refactor the upstream
   MimiGIVE computation and independently prove numerical equivalence under
   512 MiB. The present worker is not eligible for the next Monte Carlo stage.
2. Run 1,000 draws one model version per process. Require finite complete draws, identical
   contract fields, and `(SE_legacy + SE_updated) / abs(mean difference) <=
   0.10` as a conservative convergence screen. Record `Sys.maxrss()` and enforce
   the worker's authorized memory limit.
3. If that screen passes, run the prespecified 10,000 draws one version per process. The
   resulting difference of separately converged means is eligible as the
   replacement-delta point estimate. Do not create a paired-draw interval.
4. Install updated agriculture by replacement, never addition. Labor may be
   added through its separate transfer interface. Precipitation agriculture
   remains a non-additive mechanism until it is decomposed against the updated
   total-agriculture baseline.

Claim status: source path verified and an uncertified 100-draw execution path
validated; the <=512 MiB execution gate failed at 2 draws, so further runs are blocked;
replacement magnitude, uncertainty, GIVE installation, and combined SCC remain
closed.
