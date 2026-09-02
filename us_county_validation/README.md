# US county precipitation--crop validation module

This is a high-resolution empirical and validation track for the global
precipitation-SCC agriculture replacement. It is not a US-only SCC module and
does not transfer US coefficients mechanically to the world.

## Role

The module follows the structural logic of Qiu et al. (2025): compare a
transparent primary response with regularized and nonlinear alternatives;
evaluate nested time and spatial holdouts and climate extremes; retain a
pre-specified near-best model set; propagate model uncertainty. The adapted
chain is daily climate -> precipitation-pattern exposure -> county yield ->
agricultural damage validation. National/global welfare translation remains
in the global track.

The fixed June-2019 spatial estimator audit in
[NCLIMGRID_ESTIMATOR_SPATIAL_SENSITIVITY.md](NCLIMGRID_ESTIMATOR_SPATIAL_SENSITIVITY.md)
extends the official-NOAA-versus-polygon comparison from two counties to nine
production counties in nine states. All 36 county-variable cells pass, but
nonzero rainfall differences continue to reject estimator interchangeability
and route replacement.

The supplied [Blumberg (2026) appendix](BLUMBERG_2026_APPENDIX_NOTE.md)
adds a complementary agricultural-functional-form benchmark.  It locks a
comparison of seasonal-total, distribution, extremes, binned, and constrained
nonlinear specifications; it also makes clear that the 100th meridian is only
an irrigation-related robustness split, never a rainfed label.

## Locked initial inputs

| Input | Planned use | Authority |
|---|---|---|
| USDA NASS Quick Stats | County yield, production, and harvested area for maize, soybean, winter/spring wheat, rice | https://www.nass.usda.gov/quick_stats/ |
| NOAA nClimGrid-Daily | Primary daily weather for county-polygon area-weighted county-average proxies, CONUS, 1951-present, 1/24 degree | https://www.ncei.noaa.gov/products/land-based-station/nclimgrid-daily |
| gridMET / Daymet | Daily weather-product robustness comparisons; gridMET is not sole trend evidence | https://www.climatologylab.org/gridmet.html / https://doi.org/10.3334/ORNLDAAC/1840 |
| NASS planting/harvest reports and Crop Progress | Calendar priors and timing sensitivity | https://www.nass.usda.gov/Publications/Todays_Reports/reports/fcdate10.pdf |
| Cropland Data Layer / Crop Sequence Boundaries | Separate crop-location weighting sensitivities where the mask vintage is defensible | https://www.nass.usda.gov/developer/ |
| U.S. Drought Monitor county statistics | Observed county-week composite-drought validation benchmark | https://droughtmonitor.unl.edu/DmData/DataDownload/WebServiceInfo.aspx |

Raw US inputs stay under `data/raw/us_county/` and are gitignored. Record
license, query/download URL, retrieval date, checksum, filters, units, and
suppression handling before an estimation panel is accepted.

The primary NASS outcome source is a dated Quick Stats bulk crops snapshot,
not an unversioned API response. Run
`python us_county_validation/scripts/download_nass_bulk_crops.py` repeatedly
to acquire verified ranges. The downloader pins content length, ETag, and last
modified time; it refuses to continue if the upstream object changes and
writes a SHA-512 manifest only after the full archive is present. The initial
snapshot is `qs.crops_20260821.txt.gz` (1,128,988,003 bytes). No crop, geography,
unit, or suppression filters are accepted until the downloaded header and
field definitions have been inspected.
The current local-input audit and fail-closed panel prerequisites are recorded
in [STATUS_AND_PANEL_GATE.md](STATUS_AND_PANEL_GATE.md). After the archive is
complete and checksum-verified, the documented streaming extractor can select
one fully specified county-yield series without expanding the full archive;
its synthetic test preserves suppression flags and rejects duplicate keys or
mixed units.
The synthetic preparation test
`python us_county_validation/scripts/test_prepare_nass_county_yields.py`
checks disclosure-flag preservation and strict five-digit county GEOIDs; it
does not validate filters against the still-incomplete raw snapshot.

The separate primary weather archive is complete. The bounded bulk utility in
[`NCLIMGRID_DAILY_BULK_ACQUISITION.md`](NCLIMGRID_DAILY_BULK_ACQUISITION.md)
validated all 468 monthly NOAA nClimGrid-Daily objects for 1981--2019 against
the frozen HTTP identities, local SHA-512 values, NetCDF schema, and exact
daily calendars (27,857,685,556 compressed bytes). Raw files and their working
manifest remain ignored. The tracked
[`nclimgrid_daily_1981_2019_content_receipt.json`](../data/provenance/nclimgrid_daily_1981_2019_content_receipt.json)
publishes all 468 content hashes, frozen HTTP identities, and schema/calendar
receipts without exposing raw data or machine-local paths. This is an input
gate only; county aggregation, crop-calendar features, and the predeclared
model comparison are downstream.

### Bounded Quick Stats API fallback

If the pinned bulk archive remains unavailable, the isolated fallback is
`download_nass_quickstats_api.py`. It reads `NASS_API_KEY` (or
`QUICKSTATS_API_KEY`) only from the precipitation-repository-root
`.secrets/nass.env` file; that
file and `data/raw/` are gitignored. It first calls the official Quick Stats
`get_counts` endpoint using the exact county-yield filters, refuses to call
the data endpoint when the count exceeds 50,000, then writes the raw JSON and
a SHA-512 provenance record with the query parameters **excluding the key**.
It requires exactly one commodity-year per request. Use bounded discovery to
inspect the published series before locking its unit and utilization/practice
descriptors:

`python us_county_validation/scripts/download_nass_quickstats_api.py --commodity CORN --year-min 2020 --year-max 2020 --series-discovery --out-dir data/raw/us_county/nass_api/discovery_exact_year`

The locked corn-grain form is:

`python us_county_validation/scripts/download_nass_quickstats_api.py --commodity CORN --unit 'BU / ACRE' --util-practice GRAIN --year-min 2020 --year-max 2020 --out-dir data/raw/us_county/nass_api/locked`

The real 2018--2022 smoke acquired 1,518, 1,449, 1,699, 1,502, and 1,543 raw
corn-grain records under the exact all-production-practices series. Run
`prepare_nass_api_county_yields.py` over the five responses to reject combined
or other non-FIPS geographies without inventing identifiers, preserve
suppression flags, and require exact year/series coverage. The validated output
contains 7,253 real-FIPS county-years; 807 counties have reported observations
in all five years and 4,845 reported adjacent-year pairs are available. Run
`audit_nass_api_temporal_coverage.py` to reproduce those support counts and
reject mixed series, duplicate keys, missing years, or invalid reported values.
The five-year and earlier three-year provenance records bind the locked 2018
and 2019 responses by exact ignored path, so identically named copies in the
long national archive cannot satisfy the wrong receipt; the complete local
provenance walk now checks 110 artifacts with zero failures.
This validates bounded national/county outcome acquisition only; it is not a
high-rainfed sample or a yield-response estimate.

The separate irrigation screen is now operational. Exact all-years SURVEY
queries found long regional pairs of `IRRIGATED` and `NON-IRRIGATED` county
yields for corn, soybean, and all-classes wheat, while exact 2012/2017/2022
Census queries provide crop-specific irrigated and total harvested acres for a
national aggregate-yield selection gate. The direct practice series is not
nationally representative; the Census share is a fixed selector, not annual
practice. Full counts, exclusions, commands, and use boundaries are in
[NASS_IRRIGATION_PRACTICE_SCREEN.md](NASS_IRRIGATION_PRACTICE_SCREEN.md).

This is a bounded acquisition fallback, not authorization to mix NASS series
or call aggregate county yield non-irrigated. Run
`python us_county_validation/scripts/test_download_nass_quickstats_api.py`
for mocked authentication/count/cap/provenance checks and
`python us_county_validation/scripts/test_prepare_nass_api_county_yields.py`
for exact-series, FIPS, suppression, year-product, and duplicate checks.

The project owner authorized the NASS Quick Stats API as a bounded
fallback for the stalled bulk transfer. Store the key only in the local,
Git-ignored file `.secrets/nass.env` at the repository root, using the form
`NASS_API_KEY=...`. Never commit, log, or print the key. API-derived inputs
must retain exact query parameters, retrieval time, response checksum, and
suppression flags; they do not silently replace the dated bulk snapshot.

USDM area-share files are acquired only with the explicit, state/year-bounded
downloader in `scripts/`; its manifest preserves the official query URLs and
checksums. The downloader validates the requested state, year, format, schema,
five-digit county keys, and unique county-weeks before an atomic write; on
rerun it rejects any raw file whose size or SHA-512 differs from the pinned
manifest identity. Run
`python us_county_validation/scripts/test_download_usdm_county_statistics.py`
for synthetic response and tamper checks. A USDM category is never projected
directly into a global SCC draw.
`prepare_usdm_county_weeks.py` standardizes the exclusive county-week area
shares and preserves `D0` separately from the `D1+` drought-exposure measure;
it refuses duplicate county-week inputs, inconsistent validity dates, or
shares that do not sum to 100. Run
`python us_county_validation/scripts/test_prepare_usdm_county_weeks.py` for
synthetic checks of these invariants and five-digit county GEOID preservation.

The next bridge is intentionally calendar-explicit. Run
`build_usdm_crop_season_exposures.py --weeks PREPARED.parquet --calendar CALENDAR.csv --out SEASONS.parquet`
only with a documented calendar containing one row per state, crop, and harvest
year plus `season_start`, `season_end`, and a nonblank `calendar_source`. The
builder rejects missing, gapped, or overlapping daily USDM coverage and emits
day-weighted seasonal category shares, severity-index means, and
area-equivalent drought days. The season end must fall in the declared harvest
year.
It does not infer planting or harvest dates, estimate a yield response, or
authorize a global/SCC input. Run
`python us_county_validation/scripts/test_build_usdm_crop_season_exposures.py`
for a synthetic cross-year season and failure-mode checks.

Before constructing any estimation panel, audit county-year overlap with an
explicit commodity-to-crop mapping:
`python us_county_validation/scripts/audit_usdm_yield_coverage.py --yields YIELDS.parquet --exposures SEASONS.parquet --commodity CORN --crop maize --out COVERAGE.csv`.
The audit reports overall and annual counts for all NASS rows, reported-yield
rows, matched rows, and one-sided rows. It rejects multiple yield units,
duplicate join keys, or exposure rows that violate the historical-validation
only / not-SCC-authorized boundary. It emits no yield values or response
estimates. Run
`python us_county_validation/scripts/test_audit_usdm_yield_coverage.py` for
synthetic overlap and failure-mode checks.

The bounded nClimGrid and gridMET smokes, crop-specific irrigation-share gate,
and primary/sensitivity spatial routing are specified in
[WEATHER_IRRIGATION_MASK_ROUTES.md](WEATHER_IRRIGATION_MASK_ROUTES.md).
The full sparse-weight, calendar-class, FIPS/county-change, and nonlinear
feature-order gate is in
[DAILY_WEATHER_CALENDAR_CONTRACT.md](DAILY_WEATHER_CALENDAR_CONTRACT.md).
The exact 2018 precipitation smoke is independently pinned in tracked
`data/provenance/gridmet_pr_2018.toml`; it is public-domain-dedicated but has
no publisher-stated SPDX identifier. The publisher's precipitation
inhomogeneity warning prevents using gridMET alone to infer long-run changes
in rainfall intensity or frequency.

The current real construction smoke uses Cuming County, Nebraska (31039),
May--October 1981 nClimGrid weather, fixed NASS corn/soy calendars, and paired
practice-support outcomes. `build_county_polygon_nclimgrid_weights.py` and
`build_county_nclimgrid_feature_smoke.py` implement the primary proxy;
`build_cdl_nclimgrid_crop_weights.py` and
`build_crop_weighted_nclimgrid_feature_smoke.py` implement the retrospective
2017-mask sensitivity. `compare_spatial_feature_smokes.py` compares 18 weather
features only. All derived outputs remain ignored, and every audit records
`relationship_estimated=false` and `scc_authorized=false`.

After the pinned raw inputs are present, reproduce the complete bounded chain
with `us_county_validation/scripts/run_cuming_1981_spatial_smoke.sh`.

The isolated all-practice national route and its current Trigg County
fail-closed state are documented in
[US_NATIONAL_ALL_PRACTICE_WEATHER_ROUTE.md](US_NATIONAL_ALL_PRACTICE_WEATHER_ROUTE.md).
The partial-checkpoint distribution can be reproduced without resuming any
county build using `audit_us_national_weight_checkpoint_distribution.py`; its
synthetic threshold/hash failures are covered by the correspondingly named
`test_` script.
The official TIGER/Line fractional-water follow-up is reproduced with
`audit_trigg_tiger_areawater_mask.py`; its synthetic geometry test is
`test_audit_trigg_tiger_areawater_mask.py`. It leaves the fixed 0.95 gate
failed and writes no county partition.
An independent official-source sensitivity sample is reproduced with
`audit_nclimgrid_county_average_sample.py`; it validates all 3,107 January 1981
and January 2019 county rows across PRCP/TAVG/TMIN/TMAX and finds a complete
finite Trigg row under the same official numeric NCEI-to-FIPS mapping at both
historical endpoints. This does not replace the
polygon-weight route until boundary-vintage and estimator-equivalence gates
are preregistered and passed.
A seasonally distinct July 2000 check retains the identical 3,107-county
support and validates complete, finite, temperature-ordered rows for both
Trigg County, Kentucky, and Adair County, Iowa. The two counties sum to 69.64
and 115.50 mm monthly precipitation, respectively, and both retain the 0.005 C
rounded midpoint bound. This narrows month/region/schema drift only; it does
not establish full-panel identity or feature equivalence.
The separate official-versus-polygon estimator audit retains Cuming and
Fresno without outcome-based reselection in April 1990, July 2000, and July
2012. The drought-month extension has exact 3,107-county support and reproduces
0.0900 versus 0.0977 mm monthly rain in Cuming and 0.0600 versus 0.0706 mm in
Fresno. Its machine receipt is
`../data/provenance/us_nclimgrid_county_average_estimator_comparison_201207_20260831.json`.
Close agreement remains a bounded sensitivity and does not make the two
estimators interchangeable.
The same fixed comparison at the recent January-2019 boundary retains 31
finite days and exact 3,107-county support. Polygon-minus-official monthly rain
is +0.0441 mm in Cuming and +0.4057 mm in Fresno. The tracked receipt remains
a measurement sensitivity only and authorizes no route replacement, response,
damage, or SCC use.
The fixed December-2019 extension retains exact 3,107-county support and 31
finite days. Polygon-minus-official monthly rain is -0.3216 mm in Cuming and
+0.3431 mm in Fresno; all eight county-variable correlations are at least
0.999986. Nonzero signed differences continue to reject estimator equivalence
and authorize no route replacement, response, damage, or SCC use.

A fail-closed temporal synthesis now binds all seven selected months into 56
county-variable cells. Fifty-five have nonzero maximum differences; the only
exact constant match is dry Fresno precipitation in July 2000. The minimum
defined correlation is 0.985332 and the largest monthly rainfall-total
difference is 0.9926 mm. The two routes remain non-interchangeable.

## Primary design

1. Begin with a **high-rainfed-share county sample** for maize, soybean, and
   wheat. NASS county yield is not inherently irrigation-specific, so do not
   call it rainfed without a separate crop-specific irrigated-area measure.
   Pre-specify a primary rainfed-share threshold and test nearby thresholds;
   exclude or separately model materially mixed counties.
2. Build crop--county--year outcomes, retain reported NASS values and flags,
   and use harvested area only as an aggregation weight.
3. Construct daily nonlinear weather bases at crop-calendar/weather-cell level,
   then apply county-polygon intersection-area weights for the full-period
   primary county-average proxy. Apply fixed CDL crop-pixel weights as a
   separate sensitivity. For all wheat, never pool before independent class
   bases/shares exist; county-centroid weather remains diagnostic only.
4. Include joint temperature, seasonal precipitation total, normalized
   within-season precipitation shares, wet days, CDD, and heavy-rain metrics.
5. Estimate county and year fixed-effect primary specifications, with
   crop/agro-climatic pooling. Compare regularized and constrained nonlinear
   alternatives without allowing them to select features using test outcomes.
6. Use nested blocked year, state/region, and dry/wet-extreme validation.
   Treat the US fit as a validation/heterogeneity input to the global model.

## Irrigation identification gate

The initial national county sample will use the audited 2017 crop-specific
irrigated share from USDA Census harvested-area records, with 2012 and 2022
vintages as temporal sensitivities. A
fixed cross-sectional irrigation share is an imperfect proxy for annual
practice; it is therefore a selection device, not a claim that every included
observation is un-irrigated. The analysis will report results under multiple
thresholds and a mixed-county sensitivity specification. No US estimate enters
the global model unless this gate and its coverage diagnostics pass.

Where both NASS practice-specific yields are published, a separate regional
paired-practice validation will estimate heterogeneity directly. It cannot be
substituted for the national aggregate panel or extrapolated outside its
observed states and years.

The supplied US water manuscripts motivate a later irrigated-water constraint
extension: irrigation is an adaptation/input whose feasibility can respond to
snowpack, runoff, water rights, and seasonal scarcity. It is deliberately
outside the initial high-rainfed-share estimand; see
[the evidence and non-overlap note](../IRRIGATED_WATER_EVIDENCE_NOTE.md).

## Explicit exclusions

- No direct extrapolation of a US coefficient to unsupported global regions.
- No adding a US damage estimate beside the global agricultural component.
- No separate CO2 fertilization term after a response that already embeds it.
- No silently treating NASS suppression or missingness as zero yield.

## Competing direct-rainfall/PDSI diagnostic

The regional paired-practice corn/soy validation now has a frozen executable
protocol in
[US_COMPETING_MOISTURE_PREDICTIVE_PROTOCOL.md](US_COMPETING_MOISTURE_PREDICTIVE_PROTOCOL.md).
It treats seasonal precipitation total as the parsimonious direct-weather
baseline, admits distribution features only on uniform development-fold
predictive improvement, and evaluates PDSI in mutually exclusive models on
the same outcome changes and temperature controls. The full 23,722-row direct
panel and 20,228 common first differences now pass exact and independent
audits. The resulting regional predictive ranking is summarized in
[US_COMPETING_MOISTURE_INDEPENDENT_AUDIT.md](US_COMPETING_MOISTURE_INDEPENDENT_AUDIT.md);
it remains noncausal and cannot be used as a damage function or SCC input.
The separate hash-bound
[paired county-loss sensitivity](US_COMPETING_MOISTURE_PAIRED_LOSS_UNCERTAINTY.md)
reports conditional 5,000-draw RMSE/MAE intervals for pooled development,
terminal, extreme, and adequately clustered state tests without revising the
point protocol or promotion decision. It also records post hoc 2019-exclusion
and fixed-2012--2018-county point checks; neither is a new selection gate.
