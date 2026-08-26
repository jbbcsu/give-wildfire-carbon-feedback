# National all-practice U.S. weather route

Status: feature-construction route registered and bounded smoke authorized;
response estimation, causal interpretation, damages, and SCC use remain closed.

## Purpose and separation

This route expands U.S. validation support using county-level NASS corn-grain
and soybean yields for **all production practices**.  It is a distinct outcome
panel, not an infill or replacement for the regional irrigated/non-irrigated
direct-practice panel.  Its weather weights, year partitions, manifests, and
receipts use `national_all_practice` paths and cannot write to the existing
`national_v1` direct-practice trees.

The all-practice yield is not a direct rainfed yield.  The fixed 2017
crop-specific irrigation share is retained only as a prespecified sample or
interaction variable; missing or suppressed shares are never treated as zero.

## Registered support

The acquisition consists of 78 exact annual API responses (39 years for each
of two crops): 146,672 returned records, of which 8,381 are non-FIPS aggregate
records and 138,291 are reported FIPS county records.  No FIPS county record in
these locked responses has a suppressed or nonnumeric yield.  The log-yield
panel explicitly excludes 499 reported zero-yield corn rows; retaining those
rows with a prespecified two-part or alternative outcome transformation is a
required sensitivity, because deletion could omit genuine crop failures.

The resulting positive-yield panel has 137,792 crop-county-year rows across
2,657 counties before the geography/calendar screen.  The fixed 2019 TIGER
proxy audit finds 2,656 exact GEOID matches, flags 28 counties for material
historical-boundary review, and leaves 2,628 eligible counties.  After joining
the fixed 2010-vintage state/crop calendar, the registered weather-feature
support is:

- 136,539 all-practice crop-county-year rows, exactly one row per key;
- 75,089 corn-grain and 61,450 soybean rows;
- 2,628 counties, 41 states, and every harvest year from 1981 through 2019.

These are unbalanced historical observations.  They are not coefficients,
predictions, causal effects, damages, or SCC results.

## Reproducible route

The contract is
`us_county_validation/us_national_all_practice_nclimgrid_features_v1.toml`.
The launcher
`us_county_validation/scripts/run_us_national_all_practice_nclimgrid_route.py`
fixes all inputs and isolated outputs.  A route-specific feature adapter calls
the byte-preserved direct-route calculation module, replaces its paired-
practice metadata before writing, and records hashes for the launcher, adapter,
calculation module, and weight builder.  The regional feature builder and its
existing checkpoint hashes are unchanged.

Bounded smoke command:

```bash
./.venv/bin/python \
  us_county_validation/scripts/run_us_national_all_practice_nclimgrid_route.py \
  smoke --county-geoid 31039 --year 1981
```

The smoke constructs county-polygon weights and crop-year daily precipitation
and temperature features for one county and one year only.  A full build is
not implied by a passing smoke.  Full weights require explicit
`weights --all-counties`; a full year requires explicit
`feature --year YYYY --complete-year`.

Reviewed resumable full-weight command (not run in this bounded phase):

```bash
./.venv/bin/python -u \
  us_county_validation/scripts/run_us_national_all_practice_nclimgrid_route.py \
  weights --all-counties
```

The launcher resolves all 2,628 registered county GEOIDs itself, writes only
to the `national_all_practice_v1` weight tree, and resumes a county only when
its current input identity, output hash, and receipt validate.  `--force` is
intentionally absent from the reviewed full command.

Because this route has one all-practice outcome per crop-county-year, its
feature output explicitly records a one-to-one exposure application and does
not carry the direct route's `weather_exposure_shared_across_practices` flag.

## Known limitations

- County-polygon mean weather is a fixed 2019 legal-envelope proxy, not
  crop-pixel or average-farm weather.
- State/crop planting and harvest dates are fixed calendar proxies; equal-time
  stages are not observed phenology.
- Historical county coverage declines over time and is unbalanced.
- The primary positive log-yield panel excludes 499 reported zero-yield corn
  observations; a zero-retaining sensitivity is required before inference.
- All-practice yields mix irrigated and rainfed production.  Any response model
  must pre-specify how the fixed irrigation share is used and must not label the
  outcome itself rainfed.
- The bounded smoke validates data plumbing and lineage only.  Predictive and
  causal validation remain separate gates.
