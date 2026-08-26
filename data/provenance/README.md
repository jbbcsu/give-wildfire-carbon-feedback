# Provenance records

One TOML record per acquired source. A record must include the exact file URL,
catalogue/landing page, version, license, checksum, retrieval date, coverage,
and the approved use boundary. Commit records, never raw source files.

`climate_emulator_candidates.toml` records third-party climate and crop
emulators assessed for reuse or benchmarking, including audited repository
commits and licenses. It is a decision/provenance record, not vendored code and
not permission to redistribute third-party model data.

`isimip3b_daily_catalog_selection.csv` is the outcome-blind primary climate
training selection. It pins the exact 80-dataset Cartesian product and is
regenerated or compared only after `select_isimip3b_daily_catalog.py` validates
saved official API payloads. It is metadata, not evidence of file acquisition;
every selected file still requires acquisition-time SHA-512 and content checks.

`nass_quickstats_api_2020_corn_smoke.toml` records the credential-free locked
Quick Stats API smoke. The API key is intentionally absent from all tracked and
raw manifests.

`nass_quickstats_api_2018_2022_corn_panel.toml` pins the exact five-year
all-production-practices corn-yield fallback and its counts-only temporal
support audit. It is a county outcome-coverage record, not a rainfed sample,
weather response, or SCC input.

`nass_irrigation_practice_screen.toml` pins six all-years, all-classes
irrigated/non-irrigated county-yield series plus the 2012, 2017, and 2022
Census crop-specific irrigated/total harvested-area discovery files for corn,
soybean, and wheat. It records the regional direct-practice support and the
fail-closed national share fallback; neither is a weather response or SCC
input.

`gridmet_pr_2018.toml` pins the exact 2018 precipitation NetCDF used for the
U.S. weather-file smoke by local SHA-512, byte length, ETag, Last-Modified,
decoded calendar, grid, and units. The publisher states a public-domain
dedication but gives no SPDX identifier, so the record uses `NOASSERTION`
rather than inventing `CC0`. It also carries the publisher's warning against
using gridMET to infer precipitation-intensity/frequency trends across source
inhomogeneities. The raw object remains ignored and is not itself a county
exposure or SCC input.

`nclimgrid_daily_198101.toml` pins the exact NOAA nClimGrid-Daily January 1981
four-variable NetCDF by SHA-512, byte length, live HTTP identity, embedded
version/license, grid, units, chronology, and early-morning day-label
semantics. It records NCEI's update-without-version-bump warning and the
precipitation smoothing/error limitations. The object is a primary weather
candidate smoke, not a county exposure or trend result.

`nclimgrid_daily_1981_cuming_smoke.toml` pins the six exact May--October 1981
monthly objects used in the Cuming County corn/soy engineering smoke. The
resulting feature table is a county-weather construction check only: it does
not estimate a climate--yield relationship, damages, or an SCC change.

`nclimgrid_daily_1981_2019_http_inventory.csv` records complete HEAD identities
for all 468 canonical monthly objects in 1981--2019. The exact aggregate
`Content-Length` is 27,857,685,556 bytes (25.944 GiB). This is an acquisition
plan, not content provenance: each downloaded NetCDF must still pass local
byte-length, SHA-512, schema, and daily-calendar checks before use.

`census_county_changes_1980_2019.toml` pins the official 1980s--2010s Census
county-change pages and their scope statement. They provide a conservative
historical-boundary review screen, not an automatically inferred crosswalk;
absence from the substantial-change pages does not establish that no smaller
boundary adjustment occurred.

`nass_field_crop_calendar_2010.toml` pins the exact USDA NASS 2010 usual
planting/harvesting-date PDF and records the visually audited corn, soybean,
durum, spring-wheat, and winter-wheat tables. It distinguishes published
5/95-percent and 15/85-percent date ranges. The selected engineering default
uses the floor midpoint of each most-active boundary; the broad published
begin-to-end envelope is a sensitivity, while final causal-model calendar
selection remains subject to validation. The record also pins the parsed
130-row state/crop definition table and the deterministic 10,920-row 1981--
2022 primary/broad calendar expansion; neither is realized phenology.

`us_county_spatial_input_plan.toml` records official HTTP identities, terms,
coverage limits, local SHA-512 digests, and content checks for the acquired
2019 Census county file and 2017 national CDL. The county file has supported a
bounded Cuming County/nClimGrid overlay; the CDL is pinned for the separate
fixed-2017 crop-pixel sensitivity. The record blocks invented FIPS mappings,
retrospective masks presented as observed history, and post-aggregation
nonlinear weather bases.

`mirca_os_v2_irrigation_shares.toml` pins the independently downloaded annual
harvested-area archive and the fail-closed crop crosswalk. Maize and soybean
are exact crop-class mappings; annual rice and wheat shares remain ineligible
for their season-specific GDHY outcomes.

`mirca_os_v2_rice_season_inputs.toml` pins the larger monthly growing-area
archive, the two inspected 2000 calendar tables, their object identities and
local digests, and the failed Rice1--Rice3-to-annual-Rice reconciliation. The
candidate season weights remain fail-closed and are not an SCC input.

`nga_genc_gec_crosswalk.toml` pins NIST FIPS PUB 10-4 and the official NGA
GENC-to-former-GEC crosswalk used to resolve MapSPAM's four-character legacy
administrative codes to countries. The audit requires agreement with each
row's `admin2_fips` prefix and current UN ISO3, retains old administrative
codes as historical, and does not authorize welfare weights or redistribution.

`isimip3b_mri_historical_ssp370_boundary.toml` pins the first complete
historical/projection `pr` and `tas` boundary, exact checksums, and the four
historical same-realization GMST values. It is an engineering gate for one
MRI-ESM2-0 member and SSP3-7.0, not whole-ensemble validation or an SCC input.
