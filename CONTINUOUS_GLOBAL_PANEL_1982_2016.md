# Continuous global maize/soy panel: 1982–2016 construction checkpoint

## Purpose and boundary

This work filled the missing historical feature years needed to turn the
already validated 1982–1989 and 2012–2016 maize/soy endpoints into a continuous
1982–2016 diagnostic panel. The exact construction interval is 1990–2011 (22
harvest years). New artifacts are written only below
`data/interim/continuous_global_panel_1982_2016_v1/`; existing early, late, and
partial middle-period outputs are never overwritten or silently spliced.

This is feature construction only. The contract does not authorize model
selection, coefficient export, causal interpretation, future projection,
damage calculation, or SCC calculation. Direct precipitation, stage-resolved
precipitation, heat, and historical scPDSI remain separate candidate families.

## Exact gap audit

The complete target requires 720 partitions: 36 ten-latitude-cell chunks × 2
crops (maize and soybean) × 2 irrigation regimes (rainfed and fully irrigated)
× 5 feature families.

Partial middle-period artifacts already present are validation references only:

- maize/rainfed direct season and stage: 1990–2000;
- soybean/rainfed direct season and stage: 2002–2010.

The gaps are therefore maize/rainfed 2001–2011, soybean/rainfed 1990–2001 and
2011, all 1990–2011 direct features for both fully irrigated regimes, and all
1990–2011 heat and historical stage-scPDSI partitions for all four
crop–irrigation combinations. Pattern transforms, GDHY joins, and MIRCA
allocation occur only after validated direct partitions are complete.

## Completed build and measured outputs

The authorized sequential build completed on 2026-08-26 with exactly 720
validated partitions. The fail-closed post-build preflight and atomic assembly
completed on 2026-08-27. Twenty aggregate feature tables pass all registered
source, schema, key, calendar, stage/season, direct/heat, and historical-scPDSI
subset gates. Subsequent GDHY joins and fixed-MIRCA allocation produced
separate continuous 1982--2016 direct, heat, and historical-scPDSI candidates
for maize and soybean; their common direct/scPDSI support has 491,918 and
204,917 observed crop-grid-year outcomes respectively. No family is stacked,
and no causal, damage, future-projection, or SCC calculation is authorized by
this construction milestone.

## Source readiness

The readiness audit confirms local presence and registered provenance for four
decadal files each of ISIMIP3a GSWP3-W5E5 precipitation, mean temperature, and
maximum temperature (12 files; 25,077,717,340 bytes). Each variable has exactly
14,244 contiguous daily timestamps from 1981-01-01 through 2019-12-31 on the
same 360 × 720 grid. It also verifies exact crop-calendar/climate grid identity,
the four GGCMI crop-calendar hashes, GDHY annual support for 1981–2016, MIRCA
2000 irrigation weights, the registered CRU scPDSI size and SHA-256, and the
validated early/later diagnostic receipt.

The initial audit exposed an important compute defect: concatenating full-grid
decadal files without dask eagerly materialized their payload. The revised
input layer now (1) validates chronology, grid, dimensions, and units from
coordinates only and (2) slices each file to the required crop-year interval
and ten latitude cells before concatenation. The same fail-closed scientific
checks are preserved with bounded memory.

Every completed partition now has a uniform source-bound receipt. The receipt
binds the output hash and row count to the exact task latitude indices, crop,
irrigation regime, years, configured thresholds/stages, calendar SHA-256,
registered daily-climate identities (or raw scPDSI SHA-256), and relevant
builder-code hashes. A missing or stale receipt makes an existing partition
invalid and the orchestrator refuses to overwrite it. The original
direct-season pilot predated this contract; it was preserved under
`quarantine_unbound_pre_receipt/` and the registered target was rebuilt rather
than grandfathered.

## Storage and compute plan

Scaling the existing 13 endpoint years to 22 middle years gives a provisional
partition-storage estimate of:

| Family | Estimated new partition bytes |
|---|---:|
| direct season | 211,371,094 |
| direct stage | 623,456,892 |
| heat season | 130,164,772 |
| heat stage | 346,477,137 |
| historical stage scPDSI | 261,070,368 |
| **partition total** | **1,572,540,263** |

Combined tables, GDHY joins, MIRCA allocations, pattern candidates, and audit
artifacts are provisionally budgeted at 3.1–5.2 GB in total. This is a planning
range, not a measured final size. All five pilots were measured in isolated
child processes; the largest observed peak RSS was 1.635 GiB for direct stage
and the largest heat peak was 1.301 GiB. The former 1 GB heat budget was too
low. Reserve at least 2.5 GiB of free memory per sequential builder plus normal
OS/audit headroom, and do not run partition builders in parallel. Scaling the
five measured builder times over 144 crop/irrigation/latitude combinations is
about 5.7 raw builder-hours; retain a conservative 7–12 hour sequential wall
window for I/O, validation, and latitude/crop variation. This estimate is not
authorization to launch the remaining build.

## Validated bounded pilots

The maize/rainfed, latitude-index 100–110 partitions for 1990–2011 all passed
their family validator and uniform source receipt:

| Family | Rows | Bytes | Wall seconds | Peak RSS bytes | SHA-256 |
|---|---:|---:|---:|---:|---|
| direct season | 73,766 | 2,721,371 | 45.791563 | 1,446,641,664 | `83136e5749f458883057a0058d603f3cdd13f63f4ba1eda5ffe8c1a296b09bd5` |
| direct stage | 221,298 | 7,378,721 | 50.413948 | 1,755,578,368 | `23d29317148356393a3de75e2ca254899c9df45a5bd2f1bbb2d6c15fe64f4745` |
| heat season | 73,766 | 1,891,110 | 19.935304 | 1,153,433,600 | `7bf0189a872fadb15b396a3bc1847f98253a67cbb678f0b2bb98134b9ba8b260` |
| heat stage | 221,298 | 5,012,361 | 23.362290 | 1,396,883,456 | `65319659974450ea9c158ead9b5c4bea09888c252b0647f02db7e0da2b33535e` |
| historical stage scPDSI | 189,078 | 3,106,980 | 2.899197 | 731,283,456 | `4afe058848c63f817f5e4695ae5e08a1c5f0507810424e2a19e179782a4f9202` |

The final readiness audit reports exactly 5 valid, 715 missing, 0 invalid, and
0 locked tasks (one valid pilot in each family). It is stored at
`outputs/continuous_global_panel_1982_2016_v1/readiness_after_all_family_pilots.json`.

Independent direct-season and stage-metric overlap comparisons passed with
zero numerical difference across all compared columns:

- 6,706 rows for 1990–1991;
- 30,177 rows for 1992–2000.

These legacy artifacts were used only for comparison and were not copied into
the new output. Direct-stage aggregation also reconciles to the season table
for all 73,766 keys (maximum precipitation difference
`1.1368683772161603e-13` mm); heat-stage aggregation and stage-day-weighted
mean temperature reconcile to their season table within
`7.105427357601002e-15`. The historical scPDSI table contains 63,026 distinct
crop-year/grid keys, all a subset of the 73,766 direct-weather keys; 10,740
direct keys lack complete CRU monthly coverage and were not silently filled.

An idempotence check over all five selected pilot tasks reported five selected,
zero newly built, and no output modification.

## Reproducible commands

Readiness audit:

```bash
./.venv/bin/python scripts/run_continuous_global_panel_partitions.py \
  --config config/continuous_global_panel_1982_2016_v1.toml \
  --audit-out outputs/continuous_global_panel_1982_2016_v1/readiness_after_pilot.json
```

Bounded family pilot (now idempotently skipped for each valid family when the
family name is substituted):

```bash
./.venv/bin/python scripts/run_continuous_global_panel_partitions.py \
  --config config/continuous_global_panel_1982_2016_v1.toml \
  --execute --max-new-partitions 1 \
  --family direct_season --crop mai --irrigation noirr --lat-start 100
```

Independent overlap validation:

```bash
./.venv/bin/python scripts/validate_continuous_direct_partition_crosschecks.py \
  --config config/continuous_global_panel_1982_2016_v1.toml \
  --new data/interim/continuous_global_panel_1982_2016_v1/middle_1990_2011/direct_season/mai_noirr/mai_noirr_direct_season_lat100_110_1990_2011.parquet \
  --out outputs/continuous_global_panel_1982_2016_v1/direct_season_pilot_legacy_crosscheck.json
```

The full feature build and assembly are complete. No family stack, causal
response fit, damage calculation, or SCC run is authorized by this gate. The
next empirical gate is a continuous-panel development/terminal predictive
comparison, followed by the leakage-safe SPEI competitor and a separately
identified causal response design.
