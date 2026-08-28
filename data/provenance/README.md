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
complete downloaded file matches them. The 12 historical, SSP1-2.6, and
SSP5-8.5 files used by the two-forcing scenario matrix now meet that condition;
each model/forcing pair passes its calendar-aware historical/future joins. The
eight preindustrial-control files remain outside the scenario diagnostic.

`fishmip_spatial_change_distribution_20260827.json` binds those 12 validated
files to aggregate late-century grid-cell sign shares and normalized change
quantiles. It reproduces the tracked global-mean scenario matrix and exports
no cell values. It is a biophysical spatial scenario diagnostic only; pulse,
welfare, damage, and SCC gates remain closed.

`fishmip_spatial_consensus_20260827.json` binds the same raw files and reports
only aggregate sign-consensus shares on the exact 40,398-cell intersection
across both forcings, both ecosystem models, and all historical/future files.
It never averages absolute model levels or exports grid-cell values and does
not open pulse, welfare, damage, or SCC gates.
