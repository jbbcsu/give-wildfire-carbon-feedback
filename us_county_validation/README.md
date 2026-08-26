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

The supplied [Blumberg (2026) appendix](BLUMBERG_2026_APPENDIX_NOTE.md)
adds a complementary agricultural-functional-form benchmark.  It locks a
comparison of seasonal-total, distribution, extremes, binned, and constrained
nonlinear specifications; it also makes clear that the 100th meridian is only
an irrigation-related robustness split, never a rainfed label.

## Locked initial inputs

| Input | Planned use | Authority |
|---|---|---|
| USDA NASS Quick Stats | County yield, production, and harvested area for maize, soybean, winter/spring wheat, rice | https://www.nass.usda.gov/quick_stats/ |
| gridMET | Primary daily county crop-area weather features, CONUS, 1979-present, about 4 km | https://climatetoolbox.org/data/past-weather-data |
| Daymet | 1 km daily weather robustness comparison | https://daymet.ornl.gov/getdata |
| NASS planting/harvest reports and Crop Progress | Calendar priors and timing sensitivity | https://www.nass.usda.gov/Publications/Todays_Reports/reports/fcdate10.pdf |
| Cropland Data Layer / Crop Sequence Boundaries | Crop-area masks/weights where the historical period permits | https://www.nass.usda.gov/developer/ |
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
This validates bounded national/county outcome acquisition only; it is not a
high-rainfed sample or a yield-response estimate.

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

The bounded gridMET smoke, crop-specific irrigation-share gate, and
crop-area-weight routing are specified in
[WEATHER_IRRIGATION_MASK_ROUTES.md](WEATHER_IRRIGATION_MASK_ROUTES.md).

## Primary design

1. Begin with a **high-rainfed-share county sample** for maize, soybean, and
   wheat. NASS county yield is not inherently irrigation-specific, so do not
   call it rainfed without a separate crop-specific irrigated-area measure.
   Pre-specify a primary rainfed-share threshold and test nearby thresholds;
   exclude or separately model materially mixed counties.
2. Build crop--county--year outcomes, retain reported NASS values and flags,
   and use harvested area only as an aggregation weight.
3. Aggregate daily weather to crop-area-weighted county exposures; do not use
   county centroid weather as the main measure where crop masks are available.
4. Include joint temperature, seasonal precipitation total, normalized
   within-season precipitation shares, wet days, CDD, and heavy-rain metrics.
5. Estimate county and year fixed-effect primary specifications, with
   crop/agro-climatic pooling. Compare regularized and constrained nonlinear
   alternatives without allowing them to select features using test outcomes.
6. Use nested blocked year, state/region, and dry/wet-extreme validation.
   Treat the US fit as a validation/heterogeneity input to the global model.

## Irrigation identification gate

The initial county sample will use crop-specific irrigated versus non-irrigated
harvested-area data where available from USDA Census/irrigation products. A
fixed cross-sectional irrigation share is an imperfect proxy for annual
practice; it is therefore a selection device, not a claim that every included
observation is un-irrigated. The analysis will report results under multiple
thresholds and a mixed-county sensitivity specification. No US estimate enters
the global model unless this gate and its coverage diagnostics pass.

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
