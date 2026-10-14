# Post-queue U.S. county SPEI bridge protocol

## Scope and current status

This bridge is climate-only preparation code. It is not authorized to read
yield magnitudes, fit a crop response, project yields, calculate damages, or
calculate an SCC. Direct rainfall and SPEI remain mutually exclusive competing
moisture families and cannot be stacked or added.

The production bridge has **not** been run. Only three of the required 15
future 11-cell extensions are currently validated, so the all-15 gate is
closed. Synthetic tests exercise the implementation without opening the
incomplete real panel.

The final synthetic suite passed 11 tests. It covered missing and failed 15th
case refusal before bulk access, exact base/extension spatial arithmetic,
partial-cell missingness rejection, duplicate cells, historical/future support
equality, calendar-day weighting, calendar transport, validator disagreement
detection, and static outcome-access ordering. Its sampled process-group peak
RSS was 127,664,128 bytes (121.75 MiB) under the 512 MiB monitor. The monitor
is process-sampled rather than a kernel-enforced limit.

## Frozen gate and support

The builder first checks the exact five-model by three-scenario queue. For
every case, both `result.json` and the independent `validation.json` must exist,
identify the registered model/scenario, bind one 11-cell by 120-month
SPEI-1/3/6 artifact, keep every outcome/downstream gate false, and pass the
saved result/output hashes. This receipt-only pass occurs before any
31,208-cell cube, NASS panel, or TIGER geometry is opened. A missing or failed
case stops the program immediately; partial case families are prohibited.

After all 15 pass, the historical 31,208-cell, 468-month GSWP3-W5E5 block
manifest and the 11-cell historical extension are hash-checked and merged.
Every future base cube is similarly combined with its separately validated
11-cell extension. Base and extension keys must be unique and disjoint, and
the merged support must contain exactly 31,219 native half-degree cells.

The builder then reruns the frozen TIGER/Line 2019 equal-area intersection
calculation. All 361 counties must meet the prespecified 0.999 geometric-
coverage threshold. No county or case is emitted when that gate fails, and a
partially observed county-month is never renormalized into use.

## Calendar aggregation and outputs

Only the following metadata columns are projected from the existing NASS
panel: county, state, crop/practice labels, harvest year, eligibility, frozen
season dates, and calendar provenance. The two outcome columns are explicitly
excluded. The historical support must remain exactly 7,013 non-irrigated corn
county-years across 361 counties and 10 states for 1981--2018.

For each month, native-cell SPEI is averaged using the rerun county intersection
weights. A county-month is accepted only when its spatial denominator is
exactly one, except for the common structural leading missing months of
SPEI-3 and SPEI-6. Each frozen crop season then receives, separately for
SPEI-1, SPEI-3, and SPEI-6:

- a calendar-day-weighted mean of the intersecting county-month values;
- the minimum intersecting county-month value; and
- the exact number of source months.

The same state-specific NASS month-day windows are transported unchanged to
2092--2099. The future panel therefore has 43,320 rows
(15 cases x 361 counties x 8 years). The implementation also writes monthly
climate-only panels so that calendar aggregation can be independently
reconstructed:

- 168,948 historical county-months (361 x 468);
- 7,013 historical county-seasons;
- 649,800 future county-case-months (15 x 361 x 120); and
- 43,320 future county-case-seasons.

The production output is published atomically only after the entire family
passes. Its result receipt binds the contract, every base and extension
result/validation/cube, coverage and weight artifacts, climate panels, code,
and peak RSS.

## Independent validation

The independent validator checks hashes and all 15 case identities; reruns
coverage arithmetic and county-weight normalization; prohibits outcome-like
columns; verifies exact row, key, year, case, and structural-missingness
support; and reconstructs every historical and future seasonal value from the
monthly panels using its own calendar-overlap implementation. It also
reaggregates three geographically separated county sentinels directly from
the source cubes for three historical months and one future month in every
model/scenario case.

Both production jobs must run through `scripts/run_bounded_job.py` with
`--max-mib 512`. A sampled resource receipt is mandatory, and the builder also
fails if its in-process peak exceeds 512 MiB. The planned commands, after the
15th extension validation passes, are:

```text
./.venv/bin/python scripts/run_bounded_job.py --receipt <build.resource.json> --log <build.log> --max-mib 512 --min-free-gib 3 -- ./.venv/bin/python us_county_validation/scripts/build_us_spei_bridge_post_queue.py --output-dir <fresh-output-dir>
./.venv/bin/python scripts/run_bounded_job.py --receipt <validation.resource.json> --log <validation.log> --max-mib 512 --min-free-gib 3 -- ./.venv/bin/python us_county_validation/scripts/validate_us_spei_bridge_post_queue.py --result <output-dir>/result.json --resource <build.resource.json> --output <output-dir>/validation.json
```

Independent validation opens only the two climate-panel gates. Historical
response, projection, causal, damage, and SCC gates remain closed pending a
separate authorization and scientific review.

## Reproducibility files

- contract: `config/us_spei_bridge_post_queue_v1.toml`;
- builder: `us_county_validation/scripts/build_us_spei_bridge_post_queue.py`;
- independent validator:
  `us_county_validation/scripts/validate_us_spei_bridge_post_queue.py`;
- synthetic/fail-closed tests:
  `us_county_validation/scripts/test_us_spei_bridge_post_queue.py`.
