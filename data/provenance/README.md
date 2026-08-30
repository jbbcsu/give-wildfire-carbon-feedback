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
all eight BOATS/EcoOcean GFDL-ESM4/IPSL-CM6A-LR preindustrial-control files
also meet the complete-content gate for separate bounded drift diagnostics.

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

`fishmip_spatial_consensus_time_windows_20260828.json` extends the same
checksum-bound consensus to three fixed future decades on one common
40,398-cell intersection. It reports aggregate sign shares only and keeps all
pulse, welfare, damage, and SCC gates closed.

`fishmip_latitude_band_consensus_20260828.json` partitions the fixed
2091--2100 sign consensus into five exhaustive latitude bands. It records
aggregate sign shares and exact input/implementation hashes without exporting
cells. Latitude bands are not country or EEZ allocations, and all pulse,
welfare, damage, and SCC gates remain closed.

`fishmip_factorial_sensitivity_20260829.json` binds the tracked two-forcing,
two-scenario, two-ecosystem-model matrix and reports exact contrasts in
relative change from each model/forcing-specific historical reference. It
does not average absolute model levels or assign model probabilities; all
observed-catch, pulse, welfare, damage, and SCC gates remain closed.

`fishmip_gfdl_boats_picontrol_drift_20260829.json` binds the first fully
validated preindustrial-control pair and reports only a single-model global
reference plus three registered decade means. The social-forcing label changes
at 2015, so it is a bounded model-pair drift diagnostic rather than a pure
autonomous ecological drift or forced-climate response. Pulse, welfare,
damage, and SCC gates remain closed.

`fishmip_gfdl_ecoocean_picontrol_drift_20260829.json`,
`fishmip_gfdl_ecoocean_control_adjusted_ssp126_20260829.json`, and
`fishmip_gfdl_ecoocean_control_adjusted_ssp585_20260829.json` extend the same
exact gates to EcoOcean/GFDL-ESM4. Together the two GFDL pairs cover four
control files.

The six matching `fishmip_ipsl_{boats,ecoocean}_{picontrol_drift,
control_adjusted_ssp126,control_adjusted_ssp585}_20260829.json` receipts extend
the identical source, support, social-forcing, and downstream-gate checks to
IPSL-CM6A-LR. All 20 pinned FishMIP files are now fully validated; none of the
control-adjusted receipts is a causal or marginal-pulse estimate.

`fishmip_control_adjusted_matrix_audit_20260829.json` checksum-binds those 12
drift and adjusted receipts and rejects missing or duplicated matrix cells,
support/reference mismatches, reporting-window changes, and disagreement
between a control trajectory embedded in an adjusted receipt and its standalone
drift receipt. SSP5-8.5 late century is the only all-negative sign cell across
the four forcing/model combinations. The receipt explicitly keeps forced-
response, pulse, welfare, damage, and SCC gates closed.

`fishmip_control_adjusted_spatial_consensus_20260830.json` binds all 20 raw
files on one exact 40,398-cell intersection. It reports only global-reference-
normalized adjusted-change distributions and cross-model sign shares, exports
no cell values, and reconciles each area-weighted spatial mean to its global
difference in relative changes. The social-forcing join remains confounded and
all forced-response, allocation, pulse, welfare, damage, and SCC gates remain
closed.

`fishmip_control_adjusted_spatial_time_windows_20260830.json` repeats that
exact-support diagnostic over fixed 2021--2030, 2041--2050, and 2081--2090
windows. It reports temporal sign-share robustness without exporting cells or
turning the structural control adjustment into causal, observed-catch,
allocation, pulse, welfare, damage, or SCC evidence.

`fishmip_gfdl_boats_control_adjusted_ssp126_20260829.json` and
`fishmip_gfdl_boats_control_adjusted_ssp585_20260829.json` place the matching
forced and control historical/future files on one exact 41,076-cell support
intersection. They report only forced, control, and difference-in-relative-
change aggregates for three registered decades. The difference is a
structural sensitivity, not causal attribution or a marginal pulse response;
welfare, damage, and SCC gates remain closed.

`give_country_fund_region_crosswalk_v1.csv` is the normalized aggregation
universe derived from the baseline MimiGIVE mapping in the Rennert et al.
replication archive. Its config pins the exact source and derived hashes; the
tracked audit verifies 184 unique ISO3 countries, all 16 FUND regions, and
the exact per-region counts. This validates mapping identity only. Fisheries
country coverage, grid/EEZ allocation, trade/incidence, welfare, damage, and
SCC gates remain closed.

`scripts/validate_fishmip_grid_eez_allocation.py` defines a coefficient-free,
fail-closed preflight for a future versioned maritime overlay. It requires
exact declared FishMIP support coverage and per-cell area conservation while
keeping joint/disputed waters and high seas outside country aggregation. No
production allocation or new empirical source is included yet.

`marine_regions_eez_source_decision_20260828.toml` preregisters Marine Regions
Maritime Boundaries/EEZ version 12 (doi:10.14284/632, CC-BY) as the candidate
spatial source before any overlay result is inspected. The geometry is not
acquired; exact object identity, content/topology, joint regimes, high-seas
consistency, longitude handling, and ISO3 reconciliation remain pending.
