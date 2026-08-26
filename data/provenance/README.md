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
