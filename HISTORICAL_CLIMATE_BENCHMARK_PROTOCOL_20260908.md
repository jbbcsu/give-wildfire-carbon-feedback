# Historical source benchmark: GFDL first

Registered before acquisition/construction. Simulated daily weather is not
paired with observed calendar-year weather. This benchmark compares1982–2010
crop-season distributions to the observed-source exposure distribution and
future2032–2059model distribution. It does not estimate yield response or SCC.

Acquire nine public CC0 W5E5 GFDL-ESM4 r1i1p1f1 version20210512 spatial
cutouts: pr,tas,tasmax in1981–1990,1991–2000,2001–2010. Source DOI
https://doi.org/10.48364/ISIMIP.842396.1. Bind exact catalogue IDs/hashes in
individual configs; no global parent downloads or inferred source identifiers.
Keep39.25/39.75N, all720longitudes. Validate each variable's units, finite
values, exact dates/grid, and nonnegative precipitation without clipping.
Daily counts3652/3653/3652. Cross-variable and cross-file axes must match.
Reject daily mean temperature above daily maximum by more than1e-5°C;
this is a numerical tolerance, not an empirical correction.

Build maize29°C and soybean30°C, each with rainfed and irrigated GGCMI2015soc
calendars, stage fractions0/.3/.7/1, wet-day threshold1mm/day. Select calendars
by exact climate coordinates, never indices into a different global grid.
Require686calendar cells per regime and29complete harvest years, then use
fixed MIRCA2000 shares; do not fabricate outcomes. Expected fixed-weight
support is500maize/327soy cells, matching the future pilot. All transforms
precede irrigation weighting. Missing source support or lineage fails closed.

Compare per-cell historical and future mean/quantile exposure distributions
on common support; separate model-minus-observed historical differences from
future-minus-model-historical differences. These are not forcing attribution
or confidence intervals. Use the observed positive-yield1982–2010sample to
define observational support, report missing cells/years explicitly, and
include complete29year model means plus model means restricted to observed
year availability as a sampling-composition sensitivity—not weather pairs.
Do not select a correction based on future yield/damage fit. Distributional
timing, drought and nonlinear heat require joint-source checks before any
transport or economic conversion.

One monitored job/thread at a time; initially1024MiB RAM and<=64MiB NEW disk
per acquisition/processing batch,>=130GiB free. Count retained inputs separately
and report cumulative storage. Preserve all partial outputs and failures.
Construct one latitude row per child process, then concatenate exact disjoint
keys. This limits simultaneous precipitation/temperature arrays and preserves
the same scientific spatial resolution; retain the small fragments for audit.
