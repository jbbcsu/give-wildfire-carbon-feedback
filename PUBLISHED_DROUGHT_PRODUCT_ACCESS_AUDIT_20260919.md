# Published drought-product access audit: scientifically useful, not currently subsettable

## Finding

The Araujo et al. global SPI/SPEI product remains the preferred published
drought benchmark, but the current repository delivery does **not** expose the
small per-month GeoTIFF objects through the ordinary metadata/API route. The
publication describes approximately 1.4 MB GeoTIFFs separated by month, model,
scenario, index and scale. The DOI now redirects to Harvard Dataverse version
3.0, where the release is packaged as one 31--33 GB `.7z` archive per GCM plus
a small README. The five GIVE-model archives total 160,184,380,129 bytes
(149.18 GiB), already larger than the machine's total free space and necessarily
incompatible with the 130 GiB reserve.

No drought payload was downloaded.

## Exact repository state

The public metadata API response retrieved on September 19, 2026 identifies
dataset DOI `10.7910/DVN/05FVSE`, version 3.0, released November 13, 2025, with
24 files: 23 unrestricted model archives and one README. The five overlapping
GIVE models are:

| GCM archive | Dataverse file ID | Bytes | GiB |
|---|---:|---:|---:|
| GFDL-ESM4.7z | 13148266 | 32,378,393,405 | 30.16 |
| IPSL-CM6A-LR.7z | 13148275 | 31,932,097,429 | 29.74 |
| MPI-ESM1-2-HR.7z | 13148260 | 32,467,017,798 | 30.24 |
| MRI-ESM2-0.7z | 13148258 | 32,252,678,110 | 30.04 |
| UKESM1-0-LL.7z | 13148262 | 31,154,193,387 | 29.02 |

Each archive is stored through Dataverse's Globus-backed object route. The
ordinary public `api/access/datafile` request for the GFDL file returns 404;
the metadata supplies no model-archive checksum (`MD5: not available in
dataverse`). This audit does not claim that Globus transfer is impossible. It
establishes that the current standard API does not supply a checksum-bound,
small-file or internal-archive subset route, and that acquiring a full archive
would violate current storage safeguards.

## License and version qualification

The 2025 *Scientific Data* paper states that the SEDAC release is CC BY 4.0.
The currently resolved Dataverse v3 metadata declares CC BY-SA 4.0. The
repository version's license governs any files acquired from that release, so
the project must preserve the share-alike requirement unless the provider
clarifies the migration. This is a material version/licensing difference, not
a reason to treat the data as unavailable.

Primary references:

- Araujo et al. (2025), *Scientific Data*, DOI
  https://doi.org/10.1038/s41597-025-04612-w.
- Dataset landing DOI https://doi.org/10.7927/4es0-1v73, currently redirecting
  to https://doi.org/10.7910/DVN/05FVSE.
- Public metadata API:
  `https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId=doi:10.7910/DVN/05FVSE`.

## Consequence for the project

The earlier plan to fetch a handful of approximately 1.4 MB benchmark files is
not executable from the current delivery interface. Do not download even one
31--33 GB model archive while the 130 GiB free-space floor binds. Do not assume
archive integrity without a provider checksum.

The next safe access steps are, in order:

1. ask the data provider whether the original month-level GeoTIFF collection or
   an object manifest remains accessible;
2. inspect whether the Globus endpoint supports server-side selection of
   unarchived objects, without initiating a transfer;
3. after external storage is mounted, acquire one checksum-qualified archive
   as a benchmark only if selective access is unavailable; and
4. keep source-consistent ISIMIP Hargreaves SPEI as the primary path and this
   Penman--Monteith/NEX-GDDP product as an external structural benchmark.

The product remains scientifically valuable: it offers historical-distribution
mapping, 23 GCMs, four SSPs and SPI/SPEI at 3, 6 and 12 months. The access
packaging—not the scientific content—is the present blocker. No future drought,
yield, damage or SCC result follows from this metadata audit.
