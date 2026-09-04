# Provenance records

One TOML record per acquired source. A record must include the exact file URL,
catalogue/landing page, version, license, checksum, retrieval date, coverage,
and the approved use boundary. Commit records, never raw source files.

`local_isimip3b_raw_eviction_20260903.json` records the deliberate local
deletion of 60 public, reproducible ISIMIP files after exact receipt, byte,
SHA-512, content-audit, and derived-GMST checks. It is a storage-management
receipt, not a deletion of unique evidence. Code must treat its paths as
intentionally evicted and may reacquire them only under the registered source
identity for a specific unfinished calculation.

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

`us_nclimgrid_county_average_*_audit_*.json` records hash-bound, outcome-free
NOAA county-area-average source samples for January 1981, July 2000, and
January 2019. The July 2000 pair covers Trigg County, Kentucky, and Adair
County, Iowa. These receipts test source support, numeric code mapping, finite
daily values, and temperature ordering; they do not replace the registered
polygon-weight estimator or authorize a response, damage, or SCC input.

`us_nclimgrid_county_average_estimator_comparison_*_*.json` directly compares
the official county route with the fixed polygon-weight proxy for the same
Cuming and Fresno counties in April 1990, July 2000, and drought-month July
2012. The receipts bind all weather inputs and weights and record daily and
monthly difference metrics. They are bounded measurement sensitivities, not
evidence of general estimator equivalence or SCC eligibility.

`nclimgrid_daily_1981_cuming_smoke.toml` pins the six exact May--October 1981
monthly objects used in the Cuming County corn/soy engineering smoke. The
resulting feature table is a county-weather construction check only: it does
not estimate a climate--yield relationship, damages, or an SCC change.

`nclimgrid_daily_1981_2019_http_inventory.csv` records complete HEAD identities
for all 468 canonical monthly objects in 1981--2019. The exact aggregate
`Content-Length` is 27,857,685,556 bytes (25.944 GiB). The authorized bounded
acquisition subsequently retrieved all 468 objects. Its ignored local manifest
records one object-level local SHA-512 and successful byte-length, schema, and
daily-calendar receipt per month, all tied to this frozen inventory. This
completes raw acquisition only; downstream feature receipts remain required.

`nclimgrid_daily_1981_2019_content_receipt.json` is the deterministic,
tracked-safe publication projection of that ignored manifest. It exposes all
468 local SHA-512 content identities together with each canonical URL and
frozen HTTP identity, one common validated NetCDF schema, and each month's
exact daily calendar. It also binds the byte-for-byte ignored manifest at
SHA-512
`3e46415d4bba94362a46c6db536c756e2cc55f73624eee977b67fef63955d03deae832b35c553a8e1bcb1f758e020eb5020fa8e087979e0372f3e47c7d17ac5f`.
The receipt contains no raw observations, credentials, receipt-generation
timestamp, or machine-specific absolute path. Its relationship, causal,
damage, and SCC gates are all false. Regenerate or check it only with the
offline exporter documented in
`us_county_validation/NCLIMGRID_DAILY_BULK_ACQUISITION.md`.

`nass_quickstats_national_all_practice_1981_2019_content_receipt.json` is the
tracked-safe projection of the ignored national corn/soy Quick Stats API
archive. It binds 78 annual objects for 1981--2019, 190,394,822 raw bytes, and
146,672 API records to their exact key-free query parameters, retrieval times,
byte lengths, and recomputed local SHA-512 values. The exporter also parses
every raw JSON object, reconciles its row count to the recorded preflight
count, and enforces the exact commodity/unit/practice series. It exposes no
county observations, credential, or machine-specific path and authorizes no
relationship, causal claim, damage, or SCC use.

`spei_source_decision_20260826.toml` records the primary source-consistent
computed-SPEI route, primary literature and software versions, reviewed local
daily-weather variables/licenses, NOAA and SPEIbase metadata checks, the
1982--2011 frozen calibration boundary, PET/distribution/scale choices, and
the algorithmic antecedent-coverage gate. It authorizes no full index field,
outcome fit, causal claim, damage, or SCC input.

`us_competing_moisture_independent_audit_20260826.json` is the portable,
aggregate-only clean-room audit receipt for the U.S. predictive diagnostic.
It binds the registered sources/results and independent script/test hashes,
records exact common support and split/purge gates, and reports numerical
discrepancies without coefficients or row predictions. Its causal, damage,
and SCC flags are false.

`us_competing_moisture_paired_loss_uncertainty_20260826.json` is the portable,
aggregate-only exact-validation receipt for the separate 5,000-draw U.S.
county-cluster loss sensitivity. It contains conditional RMSE/MAE differences,
percentile bounds, cluster diagnostics, state omissions, and post hoc support-
only point checks. All artifact paths are relative; it contains no fitted
coefficient, row prediction, row loss, or bootstrap draw and does not alter
the point protocol, promotion gate, causal boundary, damages, or SCC.

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

`isimip3b_rimex_contiguous_completed_matrix_audit_20260903.json` is the
deterministic inventory of all completed contiguous RIME-X crop/calendar
feature cells. It binds 11 config/audit pairs by SHA-256, counts 88 completed
scenario-year templates, reports the training/test counts for every planned
whole-ESM and whole-scenario exclusion, and names the four missing cells. It is
an inventory-only gate: joint dependence, holdout promotion, response, damage,
and SCC authorization remain false.

`isimip3b_rimex_dependence_stability_preregistration_20260903.json` binds the
outcome-blind represented-template Spearman diagnostic, its fixed tolerances,
the 88-template inventory, and the pre-existing ECC-Q mechanics contract before
real evaluation. `isimip3b_rimex_template_spearman_20260903.csv` stores one
28-pair correlation fingerprint for each complete template, and
`isimip3b_rimex_dependence_stability_audit_20260903.json` records the seven
holdouts. MRI-ESM2-0 fails the locked maximum-difference gate; the diagnostic
is not retuned and opens no joint-fit, FAIR, response, damage, or SCC gate.

`isimip3b_rimex_mri_stability_decomposition_preregistration_20260904.json`
binds the storage-light diagnostic that tests the locked MRI failure after
matching on the two scenarios available for MRI. The corresponding
`isimip3b_rimex_mri_crop_regime_template_spearman_20260904.csv` stores 1,056
crop/regime template correlations, and
`isimip3b_rimex_mri_stability_decomposition_audit_20260904.json` records the
scenario-matched, scenario-specific, center-year, and crop/regime summaries.
The MRI difference remains above the unchanged gate after matching; the result
does not authorize fitting, FAIR evaluation, response, damage, welfare, or SCC
use.

`us_national_cross_crop_selector_overlap_20260904.json` is a key-only audit of
common corn/soybean support under the already fixed 2017 irrigation-share
selectors. It reads no yield magnitudes and records intersections and annual
counts only; it is not an irrigation effect, response, damage, or SCC input.
