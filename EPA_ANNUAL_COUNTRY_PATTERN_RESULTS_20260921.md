# Published annual precipitation response by GIVE country

## Result

The exact reviewed USEPA/PEEPS output provides a practical published-method
benchmark for the annual precipitation-quantity link to global warming. Across
184 GIVE countries, the median slope across available climate models is
positive in **103** countries and negative in **81**. Sign uncertainty is much
broader than those medians imply: only **9** countries have a positive 5th
percentile, only **4** have a negative 95th percentile, no country is positive
in every available model, and only **2** are negative in every available
model. Forty-one countries are positive in at least 80% of available models;
32 are negative in at least 80%.

These are counts of countries after area weighting *within* each country, not
a global land-, crop-, production-, population-, or value-weighted statistic.
The slopes have units mm yr-1 K-1 of GMST. They come from annual PEEPS
SSP2-4.5 precipitation patterns; the five labels in EPA's output alter
socioeconomic weights but not the area-weighted climate slope.

## Overlap with the direct-daily climate set

The three models overlapping this project's primary direct-daily set also
disagree in their country-count distributions:

| Model | Available countries | Median slope | 5th–95th percentiles | Positive-country share |
|---|---:|---:|---:|---:|
| MPI-ESM1-2-HR | 184 | -3.511 | -133.284 to +77.930 | 44.6% |
| MRI-ESM2-0 | 183 | -0.895 | -137.796 to +90.592 | 48.6% |
| UKESM1-0-LL | 184 | +3.060 | -51.516 to +47.500 | 56.0% |

Again, these are unweighted distributions across countries. They should not be
compared numerically with the project's rainfed-maize crop-area-weighted
seasonal ratios as if they shared geography, calendar, or weights. Their
value is to show that the published annual-quantity route is immediately
usable as an external country pattern, while also preserving large
between-model uncertainty.

## Source-support correction

The first registered run stopped before producing output because the EPA CSV
contains 405 `NA` values. They correspond to **81 country/model pairs**, each
missing identically under all five labels, leaving 4,703 finite pairs. Country
summaries therefore use 19–26 available models and report the denominator;
nothing is imputed. MRI-ESM2-0 lacks one country in the overlapping-model
table. This missingness was not exposed in the earlier high-level source
review and is now part of the fail-closed contract.

## Interpretation and use

This result answers the practical question about drawing on published
GMT-to-precipitation estimates: **yes, for annual precipitation quantity**.
The EPA/PEEPS slopes can serve as a low-cost, source-published country-level
benchmark and future quantity-only sensitivity. They cannot replace the
direct-daily ISIMIP route for crop-season totals, within-season timing,
wet-day frequency, dry spells, Rx1day/Rx5day, drought, or heat–moisture
dependence. The defensible hierarchy is therefore:

1. published EPA/PEEPS country slopes as the annual-quantity benchmark;
2. direct daily ISIMIP features as the primary timing/extreme evidence;
3. agricultural response and welfare estimation as separate gates.

No crop yield, economic damage, existing-GIVE agriculture replacement, FAIR
pulse, or SCC is estimated here. Multiplying these slopes by a historical
yield coefficient without aligned crop calendars, temperature/CO2 controls,
adaptation, and replacement accounting would not be defensible.

## Reproduction

The frozen input is USEPA commit
`dac5503549d5158e0257894012293acff45c0cb4`, data SHA-256
`131fa989f43f3d9354da23eecf1cb647dc5c24399671e78fab93230d8902a013`,
and aggregation-code SHA-256
`a4651abe5a743d7aa1fd2a22050ba3a3c267601524da4b9243a1a58967231241`.
The builder ran below 94 MiB sampled RSS. A separate standard-library CSV and
statistics implementation reconstructed **2,433** numerical/support checks.

- Protocol: `EPA_ANNUAL_COUNTRY_PATTERN_PROTOCOL_20260921.md`
- Builder: `scripts/build_epa_annual_country_pattern_benchmark.py`
- Independent validator: `scripts/validate_epa_annual_country_pattern_benchmark.py`
- Ignored result SHA-256:
  `f444a693120b4040c959f5425a1fc2e641a6150fd4566aaf033ed2b202388c19`
- Ignored independent-validation SHA-256:
  `be7cf1516d6e6d8d993066206b2f27b05f5222d07152a93afacf29eb5eb42678`

The upstream code is MIT licensed and the upstream repository labels data and
figures CC-BY-4.0. Raw source files remain ignored and are not included in Git.
