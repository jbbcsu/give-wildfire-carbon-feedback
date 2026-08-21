# NASS county-yield extract record

For each raw extract, record source URL or bulk-file version, retrieval date,
NASS filters (commodity, statistic, geography, domain, practice, unit,
reference period), file checksum, license/terms, time coverage, and all
suppression/missingness categories. The preparer must resolve duplicated
county-year rows by narrowing the source query; this pipeline does not choose
among conflicting NASS practices or domains.

## U.S. Drought Monitor validation extracts

For each state-year county-statistics response, retain the raw CSV and append
the official REST URL, retrieval timestamp, byte size, and SHA-512 to
`data/raw/us_county/usdm/MANIFEST.jsonl`. The downloader is
`scripts/download_usdm_county_statistics.py`; it retrieves county **area
percent** categories by week. Document whether county area shares are used
directly or intersected with crop-area masks. USDM is an observed composite
drought validation target, not a future climate-model input and not a direct
replacement for SPEI/PDSI/soil-moisture features.
