# National U.S. nClimGrid county-weather feature pipeline

## Purpose and boundary

This pipeline removes the direct-weather data bottleneck for the historical
U.S. corn/soy competing-moisture validation. It constructs county-crop-year
precipitation and temperature features on exactly the paired NASS irrigated
and non-irrigated outcome support. It does not fit a yield response, identify
a causal precipitation effect, calculate damages, or authorize an SCC input.

The registered support is 419 counties in 11 states, 11,861 distinct
county-crop-years (7,016 corn and 4,845 soybean), and 23,722 practice-specific
outcome rows over 1981--2019. The weather exposure is deliberately identical
for the two irrigation practices; their outcomes remain distinct. Irrigation
is not inferred from the weather product.

The executable contract is
`us_national_nclimgrid_features_v1.toml`. Raw and derived data remain under
gitignored `data/raw/` and `data/interim/`; only code, tests, documentation,
and small provenance contracts are tracked.

## Fixed sources and provenance gates

* Weather is NOAA NCEI nClimGrid-Daily v1.0.0, approximately 1/24 degree,
  DOI `10.25921/c4gt-r169`. The complete 1981--2019 HTTP inventory has 468
  monthly objects. Each required object must reconcile to the reviewed HTTP
  identity, local acquisition-manifest SHA-512, exact byte length, daily
  calendar, four-variable schema, embedded version, and license record.
* Crop calendars come from the pinned 2010 USDA NASS usual-date report. The
  pipeline uses the same immediate table and deterministic receipt as the
  competing-moisture diagnostic:
  `data/interim/us_county/nass_usual_date_calendars_1981_2022.csv` and
  `outputs/us_county/competing_moisture_predictive_v1/calendar_source_validation.json`.
  It reproduces the fixed-primary state/crop/year dates and source, vintage,
  boundary, and equal-duration-stage metadata exactly. The receipt validates
  the derived table; it does not claim to recompute the source PDF.
* County geometry is the 2019 Census TIGER/Line county file after the tracked
  historical-county exclusion gate. This is a fixed county-average proxy, not
  crop-pixel or average-farm weather.
* The direct outcome source is the exact paired NASS Quick Stats irrigation-
  practice screen. Suppressed or absent outcomes are never imputed.

## Cell-first construction and weather mask

Nonlinear quantities cannot in general be reconstructed from county-mean
daily weather. For each fixed state/crop calendar, the builder therefore:

1. extracts every positively intersecting nClimGrid cell;
2. aligns daily observations to the season and equal-duration 0/30/70/100
   stage boundaries;
3. constructs seasonal and stage precipitation totals, stage shares, timing
   centroid and concentration, wet days, conditional wet-day intensity,
   consecutive dry days, Rx1day, Rx5day, and temperature summaries at each
   cell; and
4. applies normalized county-polygon intersection-area weights to the already
   constructed cell bases.

The legal TIGER polygon includes water, while nClimGrid masks some coastal
water and reservoirs. The first national pilot correctly failed when those
masked values were encountered. The corrected weight contract defines a
fixed validity mask as cells finite for all four fields on every day of the
validated January 1981 object, excludes those cells before normalization, and
retains two explicit coverage measures: valid area divided by the full legal
polygon, and valid area divided by TIGER declared land. Later months still
fail if this fixed mask is not stable.

Across the registered 419 counties, 30 contain at least one masked
intersection. The smallest valid/full-polygon fraction is 0.529533 in a
water-rich coastal county, while the smallest valid-area/declared-land ratio
is 0.983710. Every county passes the predeclared 0.95 declared-land coverage
gate. This is weather-supported polygon weighting, not silent missing-value
filling.

## Resumable artifacts and failure behavior

`build_us_national_county_nclimgrid_weights.py` writes one atomic Parquet and
one deterministic receipt per county. A partition resumes only when current
source hashes, contract, calendar receipt, reference-weather identity, county
support, output hash, schema, area reconciliation, and coverage all match.
The completed checkpoint contains 419 county partitions and 79,355 positive
valid county-cell intersections.

`build_us_national_nclimgrid_features.py` writes one atomic partition per
harvest year. The receipt binds only the exact monthly weather objects and
county-weight partitions used by that year, so later acquisition-manifest
growth does not invalidate completed years. It refuses missing days, changed
coordinates or units, nonfinite selected weather, incomplete practice pairs,
calendar drift, key drift, or practice-specific weather.

`assemble_us_national_nclimgrid_features.py` refuses bounded smokes and missing
years. It requires all 39 complete year receipts, rehashes raw weather by
default, reconstructs exact national outcome support, and runs the locked
competing-moisture direct-source validator. The separate final validator reruns
the registered assembly implementation and requires exact dataframe equality;
it is not represented as an independent implementation.

## Validated real execution

The complete 1981 partition is built from April--November daily files. It has
504 practice rows representing 252 county-crop-years in 192 counties: 159
corn and 93 soybean crop-years. It extracts 28,167 unique valid weather cells,
has no missing or nonfinite feature, and preserves exactly one shared weather
exposure per irrigation-practice pair. A bounded Cuming County run also
reproduces all 53 numeric fields shared with the earlier independently built
1981 smoke to numerical tolerance.

All 39 harvest-year partitions are now complete and validate against the
23,722 registered practice rows. Default assembly rehashed the raw monthly
objects and produced the exact 23,722-row direct-weather table (SHA-256
`205a94ae92c12810026c9c5d0ac0fa3760e46ebc39669e528ba20a125a0c46d7`).
The assembly receipt SHA-256 is
`bd338871ad03532304a592d6de96594cbcf49bde144b428dd15d13260c068a4e`;
the exact-recomputation receipt SHA-256 is
`f2284fc41c169d9835d7721a6bc6bf562e4b96ffcd8ceeccfbd0cbc5293dc53d`.
These remain preprocessing validation results, not causal precipitation-yield
effects, damages, or SCC inputs.

## Reproduction

Generate the shared calendar receipt:

```bash
./.venv/bin/python us_county_validation/scripts/validate_us_competing_moisture_source.py \
  --family calendar \
  --input data/interim/us_county/nass_usual_date_calendars_1981_2022.csv \
  --protocol us_county_validation/us_competing_moisture_predictive_v1.toml \
  --out outputs/us_county/competing_moisture_predictive_v1/calendar_source_validation.json
```

Build or resume all county weights:

```bash
./.venv/bin/python us_county_validation/scripts/build_us_national_county_nclimgrid_weights.py
```

Build or resume each year (1981 resumes from its validated checkpoint):

```bash
for year in {1981..2019}; do
  ./.venv/bin/python us_county_validation/scripts/build_us_national_nclimgrid_features.py \
    --year "$year" || exit 1
done
```

Assemble and recomputation-validate the direct-weather table:

```bash
./.venv/bin/python us_county_validation/scripts/assemble_us_national_nclimgrid_features.py

./.venv/bin/python us_county_validation/scripts/validate_us_national_nclimgrid_features.py \
  --out outputs/us_county/national_nclimgrid_features_v1/exact_recomputation_validation.json
```

Run the synthetic failure and scalar/vector parity suite:

```bash
./.venv/bin/python us_county_validation/scripts/test_us_national_nclimgrid_pipeline.py
```

The suite covers FIPS/state mismatch, broken irrigation pairs, calendar-month
scope, cell-coordinate drift, vectorized versus scalar feature equality,
cell-first aggregation, practice sharing, and false response/SCC gates.
