# Recoverable NOAA raw-grid eviction

The 468 monthly NOAA nClimGrid-Daily gridded NetCDF files for 1981--2019
(27,857,685,556 bytes) were selected for deletion on 21 September 2026 to
restore working disk headroom. They are upstream, reproducible copies rather
than the only copy of an analysis result. Every canonical URL, HTTP identity,
local SHA-512, calendar, schema and source-version check is retained in the
committed provenance records. The files can therefore be reacquired exactly
from NOAA if a future full-grid U.S. reanalysis requires them.

The smaller official daily county-average source for 1981--2025 is retained,
as are all derived panels, validation receipts, estimates, and the student's
34,288-row daily-weather share file. No result, coefficient, manuscript output,
or unique scientific input was deleted. Existing U.S. estimates therefore do
not change. The tradeoff is operational only: new analyses requiring the full
596 by 1,385 NOAA grid must first reacquire the checksum-pinned monthly files.

The machine-readable deletion and recovery contract is
`data/provenance/nclimgrid_gridded_raw_eviction_20260921.json`. This eviction
does not open any climate-response, agricultural-damage, welfare, or SCC gate.
