# GMT-to-crop-weather response: readiness and next gates

September 17, 2026. This memo concerns the **climate-feature driver**
that would map a small matched FAIR/GIVE global-temperature perturbation
into crop-calendar weather inputs. It does not estimate a yield response
or SCC.

## What is directly observed in the current pipeline

Global 0.5-degree daily ISIMIP3b source files, same-realization annual
GMST, and crop-calendar-aligned rainfed-maize season/stage features are
linked by exact ESM/member/scenario/year identities and source hashes.
UKESM has complete validated 2042--2049 and 2092--2099 panels for
three SSPs. IPSL and MPI have validated 2092--2099 panels for three
SSPs; their three-ESM comparison passes independent arithmetic audits
and shows that the UKESM/IPSL positive seasonal-rainfall sign reverses
in MPI. MRI SSP5-8.5 and GFDL SSP1-2.6 each have independently
audited 2042--2049 and 2092--2099 panels from resident sources.
The same-SSP1-2.6 GFDL/UKESM two-window equal-cell weather signs
match, but their GMST contrasts are -0.024 and +0.370 K,
respectively. Neither an ESM's scenario difference
nor its two-window transient change is a small CO2-pulse experiment.
Different SSPs differ in
more than global mean temperature, and eight-year windows contain
internal variability. Dividing an SSP weather difference by an SSP
GMST difference would therefore not identify a causal rainfall-per-K
response.

## Minimum next data and estimation work

1. Build enough **continuous** historical and future crop-year weather
   feature coverage for the same crop-calendar cells and ESM/member
   realizations, including more than the two currently selected UKESM
   decades. Prefer already resident checksum-pinned daily `pr`/`tas`
   pairs. A new multi-gigabyte raw-pair acquisition must wait until the
   64 MiB per-job output rule and >=130 GiB free-disk floor can be
   satisfied or explicitly revised; do not evade either safeguard.
   Immediately write compact verified feature tiles and preserve
   provenance. Apply any raw-eviction policy only to exact audited
   files, never to unresolved or unrelated material.
2. Before fitting, freeze a simple competing-model set: a low-complexity
   GMST response for season rain, a joint feature response that also
   covers stage distribution/wet days/dry spells/extremes, and a
   direct-daily reference. No deep network is justified from short
   discontinuous windows. The output must respect physical bounds and
   stage-to-season precipitation additivity.
3. Test whole held-out scenarios, ESMs and time blocks, plus joint
   regional pattern error and feature-covariance preservation. Compare
   against the published emulator/pattern-scaling references catalogued
   in `CLIMATE_PRECIPITATION_EMULATOR_AUDIT.md`. A response failing
   held-out tests remains an engineering diagnostic.
4. Check each ESM's FAIR baseline/pulse temperature path against the
observed training-GMST support, use common residual draws, compare
direct and centered finite-difference pulse responses, and require
convergence across decreasing pulse sizes. No extrapolated
post-2100 SCC calculation is authorized without an explicit model
and sensitivity justification.

The first continuous global source-support gate is now met for only
GFDL-ESM4 SSP1-2.6 maize/rainfed: an independent audit validates all
2032--2059 annual panels and eight 2042--49 centered 21-year feature
years across 67,420 cells (`GLOBAL_CONTIGUOUS_GFDL_28YR_AND_CENTERED_RESULTS_20260917.md`).
This does not meet the multi-ESM/scenario requirement above. Adjacent
centered windows overlap 20 of 21 annual observations; the eight
centers are not eight independent response samples. Other resident
ESMs lack the matching three-decade daily sequence. Local ISIMIP
NetCDF files occupy about 136 GiB and leave about 135 GiB free;
the current >=130 GiB free floor plus <=64 MiB owned-output rule
precludes another multi-GB raw-pair download. A storage-safe or
remote-processing path is needed before that extension.

Separately, the empirical crop-yield response and the global welfare
replacement must be identified and validated. The existing U.S. NASS
and global historical predictive comparisons are valuable but are not
automatically transferable marginal global damages. Total rainfall
should remain the primary parsimonious candidate wherever timing
features fail incremental held-out validation; drought indices should
compete as moisture representations rather than be stacked with raw
rainfall without a defined attribution design. The agriculture module
must replace overlapping GIVE agriculture damages, not add a second
term to them. Until all these gates pass, no incremental SCC number is
scientifically defensible.
