# Provenance gate

Create one machine-readable record per acquired source with exact catalogue
and file URLs, version, license, checksum, retrieval date, query/filter, spatial
keys, units, and missing/suppression semantics. Raw files remain under
`data/raw/` and are never committed. A source is not estimation-ready until
license and redistribution boundaries are explicit.

For the unacquired FishMIP `tc` benchmark, the catalogue record and exact
all-file plan are kept separately: `fishmip_isimip3b_tc_catalog.toml` records
the reviewed source and gates, while
`fishmip_isimip3b_tc_acquisition_plan.csv` pins every dataset/file ID, version,
URL, catalogue byte size, SHA-512, year interval, and frozen acquisition stage.
These catalogue checksums become verified local provenance only after a
complete downloaded file matches them.
