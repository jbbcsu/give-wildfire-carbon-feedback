# U.S. corn/soy competing-moisture predictive protocol

## Question and boundary

This diagnostic asks a narrow historical question: on exactly the same U.S.
county-year outcome changes and with the same temperature controls, does a
parsimonious seasonal precipitation total, an expanded within-season rainfall
description, or NOAA county PDSI predict held-out corn and soybean yield
changes more accurately? Irrigated and non-irrigated NASS outcomes are fitted
and reported separately. Wheat is excluded until its all-classes outcome can
be mapped to winter, spring, and durum calendars without pooling alternative
calendar candidates.

This is predictive validation. It does not identify a causal precipitation
effect, estimate climate-change-attributable yield loss, define a damage
function, or enter the SCC calculation.

## Frozen comparison

The executable contract is
[`us_competing_moisture_predictive_v1.toml`](us_competing_moisture_predictive_v1.toml).
It defines five models:

1. common temperature controls only;
2. controls plus crop-season precipitation total;
3. controls plus total and a frozen rainfall-distribution extension;
4. controls plus crop-season mean PDSI; and
5. controls plus preplant and three stage-mean PDSI values as a sensitivity.

No fitted model contains both raw precipitation and PDSI. The same three
stage-mean temperature controls enter every model. Models are fitted separately
for corn/soybean and irrigated/non-irrigated outcomes. Consecutive-year first
differences remove time-invariant county yield levels; gaps are never bridged.
The model still remains associational because climate, management, technology,
and reporting can change together.

All continuous inputs are centered and scaled on training rows only. The
diagnostic writes aggregate RMSE, MAE, and out-of-sample R-squared; it writes
neither coefficients nor row predictions. Predeclared absolute/relative
training-scale floors remove effectively constant columns, and a predeclared
SVD tolerance drops numerically unidentified design directions; both the
dropped-column count and retained design rank are reported. Leave-one-state-
out tests use only the pre-2012 development period; a state is scored alone
only when it passes the predeclared 50-row test minimum. This is deliberately
stricter than random county folds for a spatially correlated weather exposure.
The terminal 2012--2019 test is restricted to counties already observed in
development and is not used to choose a specification. A separate development-
period extreme test holds out rows outside precipitation-total cutoffs fixed
without outcomes.

Because the outcome and weather predictors are first-differenced, row-key
separation alone is not enough. A difference labelled year `t` uses the two
level endpoints `t-1` and `t`. For every scored split, the evaluator therefore
removes any training difference that shares either county/crop/practice/year
level endpoint with a test difference. The number removed is reported for
every model/split. This purges the 2011 difference for a county when its 2012
difference begins the terminal test, and also purges adjacent development
differences around precipitation-extreme test rows.

The distribution extension is promoted over quantity-only only if its RMSE
improvement reaches both predeclared floors in every eligible development
leave-state-out test: at least `0.0001` log-yield-change RMSE and at least 1%
of that state's quantity-only RMSE. Equivalently, the required improvement is
the larger of those two values. These are conservative predictive-screening
materiality gates, not claims about agronomic or welfare significance. A
positive improvement smaller than the floor, a null, or a worse result fails
promotion and is retained and reported. Terminal-time and extreme performance
are confirmation/stress tests, not opportunities to alter the feature set.

## Source, calendar, and receipt gates

The two weather/index inputs and the fixed calendar input must independently
pass deterministic pre-fit validation and carry separate SHA-256-bound
receipts. The direct input is
locked to the named NASS outcome source, dated nClimGrid-Daily source/grid,
county-polygon exposure role, 1 mm wet-day definition, unshifted publisher date
labels, and the fixed 2010 NASS calendar source/vintage/boundary/stage rule. The
PDSI input is locked to the named NASS outcome source, dated NOAA nClimDiv PDSI
source, Palmer metadata and 1931--1990 calibration, and exactly the same fixed
calendar lineage. The inputs must also agree key by key on outcome values,
calendar source/vintage/rule, stage definition, and season start/end. Every
county state must equal the state encoded by its GEOID, every used source row
must be explicitly feature-eligible, and every source season must reconcile to
the hash-bound 2010 NASS calendar row for its state, crop, and harvest year.

Each receipt validates and hashes its immediate source table. It explicitly
does **not** claim to recompute daily nClimGrid features, monthly NOAA PDSI, or
the calendar from the publisher PDF. The final validator checks raw-table and receipt
hashes, rebuilds all common-support and first-difference tables from the bound
raw inputs, checks them exactly against the stored analysis tables, and then
recomputes every aggregate metric and selection gate. Raw-source provenance
and upstream feature validators remain separately required.

## Current input gate (2026-08-26)

The NOAA/NASS side is ready for corn and soybean. The completed PDSI join has
11,861 geography-eligible crop-county-years, duplicated only because the two
named practices have distinct outcomes. These yield 20,228 valid consecutive-
year practice-specific changes: 5,952 per corn practice and 4,162 per soybean
practice. The PDSI windows have no missing index values.

The direct-weather side is complete. All 468 NOAA nClimGrid-Daily monthly
objects for 1981--2019 (27,857,685,556 bytes), 419 county-polygon weight
partitions, 39 harvest-year feature partitions, and the final 23,722-row table
pass their frozen identity, SHA, schema, calendar, practice-pair, aggregation,
and exact-recomputation gates. Its SHA-256 is
`205a94ae92c12810026c9c5d0ac0fa3760e46ebc39669e528ba20a125a0c46d7`.
The common-support builder retains all 20,228 registered consecutive-year
changes shared with the PDSI representation. The resulting fit is still a
historical predictive diagnostic only; it does not identify a causal response
or authorize damage/SCC use.

## Reproduction

```bash
./.venv/bin/python us_county_validation/scripts/validate_us_competing_moisture_source.py \
  --family direct_weather \
  --input data/interim/us_county/nass_direct_practice_nclimgrid_1981_2019.parquet \
  --out outputs/us_county/competing_moisture_predictive_v1/direct_source_validation.json

./.venv/bin/python us_county_validation/scripts/validate_us_competing_moisture_source.py \
  --family pdsi \
  --input data/interim/us_county/nass_direct_practice_pdsi_join_1981_2019.parquet \
  --out outputs/us_county/competing_moisture_predictive_v1/pdsi_source_validation.json

./.venv/bin/python us_county_validation/scripts/validate_us_competing_moisture_source.py \
  --family calendar \
  --input data/interim/us_county/nass_usual_date_calendars_1981_2022.csv \
  --out outputs/us_county/competing_moisture_predictive_v1/calendar_source_validation.json

./.venv/bin/python us_county_validation/scripts/build_us_competing_moisture_inputs.py \
  --direct-weather data/interim/us_county/nass_direct_practice_nclimgrid_1981_2019.parquet \
  --direct-validation outputs/us_county/competing_moisture_predictive_v1/direct_source_validation.json \
  --pdsi-join data/interim/us_county/nass_direct_practice_pdsi_join_1981_2019.parquet \
  --pdsi-validation outputs/us_county/competing_moisture_predictive_v1/pdsi_source_validation.json \
  --calendar data/interim/us_county/nass_usual_date_calendars_1981_2022.csv \
  --calendar-validation outputs/us_county/competing_moisture_predictive_v1/calendar_source_validation.json \
  --output-dir data/interim/us_county/competing_moisture_predictive_v1 \
  --audit-out outputs/us_county/competing_moisture_predictive_v1/input_audit.json

./.venv/bin/python us_county_validation/scripts/evaluate_us_competing_moisture.py \
  --input-dir data/interim/us_county/competing_moisture_predictive_v1 \
  --input-audit outputs/us_county/competing_moisture_predictive_v1/input_audit.json \
  --direct-weather data/interim/us_county/nass_direct_practice_nclimgrid_1981_2019.parquet \
  --direct-validation outputs/us_county/competing_moisture_predictive_v1/direct_source_validation.json \
  --pdsi-join data/interim/us_county/nass_direct_practice_pdsi_join_1981_2019.parquet \
  --pdsi-validation outputs/us_county/competing_moisture_predictive_v1/pdsi_source_validation.json \
  --calendar data/interim/us_county/nass_usual_date_calendars_1981_2022.csv \
  --calendar-validation outputs/us_county/competing_moisture_predictive_v1/calendar_source_validation.json \
  --out outputs/us_county/competing_moisture_predictive_v1/results.json

./.venv/bin/python us_county_validation/scripts/validate_us_competing_moisture.py \
  --input-dir data/interim/us_county/competing_moisture_predictive_v1 \
  --input-audit outputs/us_county/competing_moisture_predictive_v1/input_audit.json \
  --direct-weather data/interim/us_county/nass_direct_practice_nclimgrid_1981_2019.parquet \
  --direct-validation outputs/us_county/competing_moisture_predictive_v1/direct_source_validation.json \
  --pdsi-join data/interim/us_county/nass_direct_practice_pdsi_join_1981_2019.parquet \
  --pdsi-validation outputs/us_county/competing_moisture_predictive_v1/pdsi_source_validation.json \
  --calendar data/interim/us_county/nass_usual_date_calendars_1981_2022.csv \
  --calendar-validation outputs/us_county/competing_moisture_predictive_v1/calendar_source_validation.json \
  --candidate outputs/us_county/competing_moisture_predictive_v1/results.json \
  --out outputs/us_county/competing_moisture_predictive_v1/validation.json
```

The tracked synthetic test exercises the same build, evaluation, and exact-
recomputation gates but is not empirical evidence. The validator intentionally
reuses the registered builder and evaluator; it is not an independent
implementation.
