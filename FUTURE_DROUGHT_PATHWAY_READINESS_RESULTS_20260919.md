# Future drought pathway: use published projections as benchmarks, not substitutes

## Decision

Do not build a new climate-to-drought emulator before using the available
published global drought products. Two recent peer-reviewed products are
directly relevant. They should enter as external benchmarks and structural
sensitivities. Neither can replace the source-consistent ISIMIP path needed for
the primary GIVE calculation, and neither supplies a paired marginal-emissions
counterfactual.

The primary engineering target remains crop-calendar SPEI derived from the
same bias-adjusted ISIMIP3b realizations used by the precipitation pathway,
using the historical 1982--2011 transform already frozen for the agricultural
response comparison. Direct precipitation and drought-index response families
remain mutually exclusive alternatives; they are not summed.

## Published products located

1. Araujo et al. (2025), *Scientific Data*, provide monthly SPI and SPEI at
   0.25 degrees for 23 NEX-GDDP-CMIP6 models, 1980--2100, four SSPs, and 3-,
   6-, and 12-month scales. The dataset is CC BY 4.0. It uses a
   Penman--Monteith PET route and is validated against ERA5-Land drought
   characteristics in six world regions. The archive is about 800 GB, but its
   approximately 1.4 MB month/model/scenario/scale GeoTIFF layout makes a
   registered subset feasible without acquiring the archive. DOI:
   https://doi.org/10.1038/s41597-025-04612-w; data DOI:
   https://doi.org/10.7927/4es0-1v73.

2. Xiong and Yang (2025), *Scientific Data*, provide a 1-degree monthly
   PDSI_CMIP6 ensemble for 11 models, historical 1850--2014 and four SSPs
   through 2094. It incorporates climate-model hydrologic outputs and compares
   projected PDSI with modeled soil moisture. Four GIVE climate models are
   explicitly in its model table: GFDL-ESM4, IPSL-CM6A-LR, MPI-ESM1-2-HR, and
   MRI-ESM2-0. The full-period calibration, model-native hydrology, 1-degree
   remapping, manual removal of extreme values, and different forcing lineage
   make it a structural benchmark rather than a transportable primary exposure.
   The Zenodo record is a single 13.8 GB zip and does not display a dataset
   license in the reviewed metadata, so reuse requires a license clarification.
   DOI: https://doi.org/10.1038/s41597-025-05790-3; data DOI:
   https://doi.org/10.5281/zenodo.16131240.

These products show that global climate-to-drought projections already exist;
the novel task here is not inventing drought climatology. It is aligning a
published or source-consistent drought exposure with crop calendars, the
validated yield estimand, irrigation treatment, adaptation scenarios, and the
paired SCC accounting rules.

## Reproducible local readiness audit

`scripts/audit_future_drought_pathway.py` reads the frozen ISIMIP3b catalog and
file metadata only. It does not open NetCDF values or hydrate cloud files. The
audit confirms a complete public, unrestricted, CC0 catalog matrix of five
ESMs, four experiments (historical plus SSP1-2.6, SSP3-7.0, SSP5-8.5), and four
daily variables (`pr`, `tas`, `tasmin`, `tasmax`): 80 source datasets.

The resident raw tree contains 92 NetCDF files and 146.49 GB of logical data.
For the two registered later-century windows (2041--2050 and 2091--2100), 20
of 30 precipitation files and 20 of 30 mean-temperature files are resident.
None of the 30 required minimum-temperature or 30 required maximum-temperature
files is resident. Therefore the locked Hargreaves-Samani SPEI primary cannot
yet be computed for the full matrix. The catalog identifies every missing
dataset, but the exact 80-file checksum/size acquisition manifest (10 `pr`, 10
`tas`, 30 `tasmin`, and 30 `tasmax`) must be captured before download. With the
130 GiB free-space floor currently binding, bulk acquisition is prohibited
until external storage is available or other project data are moved after
explicit review.

A bounded no-download next step is available: GFDL-ESM4 has a complete local
four-variable boundary set for historical 2011--2014 and all three SSPs for
2015--2020. This can validate frozen-parameter application, historical/future
calendar continuity, temperature ordering, monthly water-balance construction,
and crop-window allocation. Because this is a short, low-forcing period, it is
an engineering validation only, not evidence about end-century drought damages.

Machine-readable receipt:
`data/provenance/future_drought_pathway_readiness_20260919.json`.

## Ordered implementation plan

1. Implement the resident GFDL boundary pilot on fixed crop-support cells. Apply
   the already fitted observational 1982--2011 SPEI parameters without
   refitting on 2012+ or future values. Verify zero-change, chronology,
   crop-window, tail-clipping, and source-hash gates.
2. Register a small Araujo-product subset covering the five GIVE ESMs where
   available, the three GIVE SSPs, 3/6-month scales, fixed benchmark years, and
   crop cells or country aggregates. Do not download the 800 GB archive.
3. When external storage is mounted, snapshot exact ISIMIP file metadata and
   process `tasmin`/`tasmax` sequentially to monthly crop-support P-minus-PET
   shards, deleting each validated raw temporary only after checksums and
   derived receipts pass. Do not hold daily cubes in memory.
4. Compare the ISIMIP Hargreaves primary with the published Penman--Monteith
   SPEI and PDSI/soil-moisture benchmark. Report disagreement as drought-index
   and forcing uncertainty; do not select the index that produces the largest
   damage.
5. Only after the drought-yield family clears the existing geographic,
   terminal, and interval gates should it be mapped through fixed, trend, and
   upper adaptation scenarios. A scenario projection is not a marginal SCC:
   paired base/pulse identifiers and zero-pulse/convergence tests remain
   required before GIVE integration.

## What this does not establish

This audit estimates no future drought trend, crop loss, monetary damage, or
SCC. It does not promote the historical SPEI or scPDSI response evidence. It
does not infer missing source values or treat published ensemble means as a
GIVE marginal pulse. Those gates remain closed.
