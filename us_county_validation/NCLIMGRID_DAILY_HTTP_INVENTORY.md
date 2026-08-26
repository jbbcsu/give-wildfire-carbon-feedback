# nClimGrid-Daily HTTP identity inventory

`scripts/inventory_nclimgrid_daily_http.py` makes `HEAD` requests only. It
catalogs the 468 canonical monthly nClimGrid-Daily objects from January 1981
through December 2019. It does not download NetCDF response bodies and does
not construct weather features, estimate a yield response, or produce damages.

The catalog records `year`, `month`, canonical object name and URL,
`Content-Length`, `ETag`, `Last-Modified`, and `Content-Type`. All fields are
required. Duplicate months, names or URLs that do not match the fixed NCEI
naming rule, malformed metadata, redirects, and missing months in a final CSV
are rejected.

For a bounded first pass:

```bash
.venv/bin/python us_county_validation/scripts/inventory_nclimgrid_daily_http.py \
  --max-new 12
```

An incomplete run is written to
`data/provenance/nclimgrid_daily_1981_2019_http_inventory.csv.partial`. Running
the same command again first rechecks every recorded object. Any changed
identity stops the run without updating the pin. The `.partial` file is
atomically promoted to the tracked-friendly `.csv` name only when all 468
months are complete. Omit `--max-new` to finish the metadata inventory. At
most eight concurrent requests are allowed; the default is four.

The HTTP inventory is necessary but not sufficient provenance. NCEI notes that
inputs to nClimGrid-Daily can be updated. On acquisition, each local file must
still be checked against the pinned byte length, hashed locally with SHA-512,
opened and schema-validated, and checked for its exact daily calendar coverage.
Only those content-level checks can support a reviewed acquisition record and
scientific use. This catalog does not authorize a bulk download.

The project owner subsequently authorized the separate raw-data acquisition
and Dropbox storage. That authorization does not turn this HTTP catalog into a
content checksum. The bounded, content-validating implementation, exact
storage footprint, resume semantics, local-manifest contract, and commands are
documented in
[NCLIMGRID_DAILY_BULK_ACQUISITION.md](NCLIMGRID_DAILY_BULK_ACQUISITION.md).
