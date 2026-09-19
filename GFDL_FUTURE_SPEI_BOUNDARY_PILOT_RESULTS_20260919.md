# Frozen SPEI transform passes a source-consistent GFDL boundary pilot

## Result

The observationally fitted SPEI transform can be applied without refitting to
a complete ISIMIP3b historical/future boundary within the registered memory and
storage limits. The corrected run passed independent saved-array validation:
3,122,758 checks, exact reconstruction of every reported aggregate, identical
2011--2014 historical values across all three scenario paths, and zero missing
values after each accumulation scale's required leading warm-up.

This is an engineering result. It does not show a climate-change effect on
drought, a drought effect on yield, agricultural damage, or an SCC increment.

## Fixed design and provenance

The pilot uses 512 fixed crop-support grid cells and the GLO parameters fitted
only from 1982--2011 observational GSWP3-W5E5 water balances. Twelve registered
GFDL-ESM4 `r1i1p1f1` daily files were fully rehashed: historical 2011--2014
`pr`/`tasmin`/`tasmax` and the matching 2015--2020 fields for SSP1-2.6,
SSP3-7.0, and SSP5-8.5. Every byte count and SHA-512 matched the prior ISIMIP
provenance. No outcome, post-2011 value, or GFDL value was used to refit the
standardization parameters.

The saved output contains 120 months per scenario and 1-, 3-, and 6-month
Hargreaves-Samani P-minus-ET0 SPEI. The first attempt completed the numerical
work but failed while writing its receipt because a relative output path was
compared with the absolute project root. Its failed resource receipt and output
are retained. The path-only bug was fixed; the second run used a fresh output
namespace and passed without changing any scientific rule.

## Bounded descriptive diagnostics

All 36,864 future cell-month values per scenario and scale are finite. The
unweighted 2015--2020 summaries are:

| Scenario | Scale | Mean SPEI | Fraction <= -1 | Fraction <= -1.5 |
|---|---:|---:|---:|---:|
| SSP1-2.6 | 1 month | -0.084 | 0.230 | 0.112 |
| SSP1-2.6 | 3 months | -0.147 | 0.232 | 0.119 |
| SSP1-2.6 | 6 months | -0.237 | 0.264 | 0.128 |
| SSP3-7.0 | 1 month | -0.047 | 0.201 | 0.081 |
| SSP3-7.0 | 3 months | -0.107 | 0.212 | 0.092 |
| SSP3-7.0 | 6 months | -0.188 | 0.229 | 0.109 |
| SSP5-8.5 | 1 month | -0.052 | 0.201 | 0.089 |
| SSP5-8.5 | 3 months | -0.115 | 0.220 | 0.103 |
| SSP5-8.5 | 6 months | -0.198 | 0.239 | 0.117 |

These are cell-month diagnostics for the first 512 cells, not area- or
production-weighted drought incidence. The short paths do not order monotonically
by forcing, which is expected before appreciable scenario separation and is a
useful guard against mislabeling raw scenario weather as a causal forcing
response. The negative means may reflect the GFDL realization, the observational
reference transform, or both; this pilot cannot distinguish them.

Tail clipping remains explicit. Across the nine scenario-scale summaries there
are 232 lower and 51 upper probability clips. They are retained in the saved
clip-code array and are not silently winsorized away or treated as independent
drought events.

## Resource result

The successful builder took 74.16 seconds, peaked at 182,714,368 bytes of
sampled process-group RSS, and added 15,165,433 bytes under the 512 MiB RAM,
64 MiB output, and 130 GiB free-space guards. Independent validation took 0.82
seconds and peaked at 127,844,352 bytes. These are sampled process measurements,
not kernel-enforced memory limits.

Before the run, 120 reproducible long-form crop-window SPEI Parquet files were
removed to restore the disk floor. Their upstream manifest, per-file hashes,
validation receipt, and independently validated lossless 512.85 MB wide form
remain. No raw climate, yield data, fitted parameters, wide-form features, or
scientific receipt was deleted. See
`data/provenance/local_derived_storage_eviction_20260919.json`.

## Next gate

The same frozen-transform pipeline is ready for later-century ISIMIP windows,
but the full five-ESM matrix still lacks 10 precipitation, 10 mean-temperature,
30 minimum-temperature, and 30 maximum-temperature files. Once external storage
is available, acquire and process those files sequentially into small monthly
crop-support shards. Only after full crop-window allocation and the prespecified
yield-response validation can drought enter the fixed/trend/upper adaptation
analysis. Paired marginal pulse and zero-pulse/convergence gates remain required
before any SCC result.

Machine-readable summary:
`data/provenance/gfdl_future_spei_boundary_pilot_20260919.json`.
