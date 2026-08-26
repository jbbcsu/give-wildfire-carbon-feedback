# Provenance gate

Create one machine-readable record per acquired source with exact catalogue
and file URLs, version, license, checksum, retrieval date, query/filter, spatial
keys, units, and missing/suppression semantics. Raw files remain under
`data/raw/` and are never committed. A source is not estimation-ready until
license and redistribution boundaries are explicit.

`blue_scc_fisheries_literature_benchmark_20260826.json` is an aggregate-only
audit of the published Blue-SCC fisheries workflow and Figure 4 source data at
a frozen external repository commit. It stores file hashes, method readouts,
country-coefficient sign/count summaries, and published sectoral SCC values;
it stores no external coefficient row or source workbook and authorizes no
GIVE damage function or SCC integration.

For the staged FishMIP `tc` benchmark, the catalogue record and exact all-file
plan are kept separately: `fishmip_isimip3b_tc_catalog.toml` records
the reviewed source and gates, while
`fishmip_isimip3b_tc_acquisition_plan.csv` pins every dataset/file ID, version,
URL, catalogue byte size, SHA-512, year interval, and frozen acquisition stage.
These catalogue checksums become verified local provenance only after a
complete downloaded file matches them. All four frozen GFDL-ESM4 smoke files
(BOATS and EcoOcean, historical and SSP1-2.6) now meet that condition. Each
model passes its exact calendar-aware historical/future join. The other 16
files remain unacquired; the smoke does not authorize their acquisition.
