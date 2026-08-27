# Data and redistribution policy

Source data are not version-controlled in this repository. Each acquisition
must have a source URL, version, checksum, retrieval date, applicable license,
and citation in `data/provenance/`. Raw data are ignored by Git.

GDHY is recorded as CC-BY-4.0 subject to its landing-page terms. The selected
GGCMI/ISIMIP crop calendar records are CC0-1.0. ISIMIP climate-file rights and
terms must be captured from the precise catalogue response at download time.
No credentials, access tokens, or restricted data may be committed.

NOAA NCEI nClimGrid-Daily is recorded as U.S. federal-government data with
SPDX `NOASSERTION`: the reviewed NetCDF states `no restrictions`, but neither
the product page nor file supplies a more specific SPDX identifier. The raw
monthly NetCDF files and their local SHA-512 acquisition manifest remain
Git-ignored. The exact source, version, DOI, identity checks, limitations, and
resume contract are documented in
`us_county_validation/NCLIMGRID_DAILY_BULK_ACQUISITION.md`.

USDA NASS Quick Stats responses are treated as U.S. public data, with source
attribution and all returned disclosure/suppression flags preserved. The API
credential is read only from ignored `.secrets/nass.env`; it is never written
to a query manifest, receipt, processed table, or log. Raw county responses
and the acquisition manifest remain Git-ignored. The tracked content receipt
contains only exact key-free query identities, retrieval metadata, sizes, and
hashes. Absence of a county-year from an API response is not interpreted as a
zero or as an explicitly observed suppression.
