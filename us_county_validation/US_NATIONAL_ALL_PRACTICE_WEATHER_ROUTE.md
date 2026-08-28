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

The required zero-retaining support audit is now executable and source-bound.
It finds 499 reported corn zero-yield county-years across 150 counties and 217
consecutive spells; 419 rows pass the fixed geography gate, but only 45 have a
usable fixed-2017 irrigation share and only 7 meet the 10% high-rainfed
selector. The longest zero spell is 10 years, while 118 rows have an adjacent
positive observation. Every reported zero lies in 1998--2009 despite 17
declared source years before and 10 after that interval, and the five most
represented states account for 73.55% of zero rows. Of the 118 rows with an
adjacent positive observation, 111 pass the geography gate, only 15 have an
eligible fixed irrigation share, and 4/5/5 meet the 10/20/30% high-rainfed
selectors. These counts show that zeroes are neither a single isolated coding
anomaly nor adequately supported for the primary high-rainfed estimand; their
temporal and state concentration also rules out silently treating them as a
generic crop-failure signal. No two-part or alternative outcome model is
selected.

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

A second, source-bound southern-support smoke uses Acadia Parish, Louisiana
(GEOID 22001) in 2019. It validates 119 positive polygon/grid intersections,
five exact monthly weather objects, and one supported soybean crop-county-year
feature row. Its tracked receipt is
`data/provenance/us_national_all_practice_nclimgrid_southern_smoke_20260828.json`.
This extends the route check beyond the original Nebraska engineering case;
it is still one county-year, not national validation or a fitted response.

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

The first full-scope execution has now validated 932 county receipts and then
failed closed at Trigg County, Kentucky (GEOID 21221). Its weather-valid area
is 0.907267979 of TIGER-declared land area, below the preregistered 0.95 gate.
The gate was not relaxed and the county was not silently excluded. The exact
failure and source/code hashes are recorded in
`data/provenance/us_national_all_practice_nclimgrid_weight_checkpoint_20260828.json`.
The same 77 valid cells, 209,051,009 m2 masked intersection, and 0.907267979
land-relative coverage recur exactly for January 1981, July 2000, and January
2019, so this is not a one-month missingness artifact. Before resumption, the
structural nClimGrid mask/TIGER land-area mismatch requires a source-level
audit and an outcome-blind exclusion or sensitivity rule.

Separate finite-value masks for `prcp`, `tavg`, `tmin`, and `tmax` in the
January 1981 reference file also reproduce the exact same 77 cells,
209,051,009.183043 m2 masked intersection, and 0.907267979 valid-area/declared-
land ratio. The blocker is therefore common to the product mask, not driven by
one weather variable.

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
  observations; their support is now audited, but a predeclared zero-retaining
  model sensitivity is still required before inference.
- All-practice yields mix irrigated and rainfed production.  Any response model
  must pre-specify how the fixed irrigation share is used and must not label the
  outcome itself rainfed.
- The bounded smoke validates data plumbing and lineage only.  Predictive and
  causal validation remain separate gates.
- The full county-weight build is currently fail-closed at GEOID 21221 under
  the registered weather-valid-area threshold; 932 of 2,628 receipts are
  complete and no national feature panel is authorized from that partial set.
