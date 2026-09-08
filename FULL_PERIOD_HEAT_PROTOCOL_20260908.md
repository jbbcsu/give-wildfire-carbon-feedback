# Full-period heat extension (registered before construction)

Extend the matched GFDL-ESM4 r1i1p1f1 W5E5 SSP126/SSP585 climate inputs to
harvest years 2032–2059, retaining the existing two latitude rows (39.25 and
39.75°N), fixed MIRCA2000 irrigation weights, GGCMI calendars, maize 29°C
and soybean 30°C thresholds, and stage fractions 0/0.3/0.7/1. Reuse completed
rainfall products without reconstruction. This is a climate-input diagnostic,
not a new fitted response, global representative estimate, damage or SCC.

Acquire only the missing 2031–2040 and 2051–2060 daily Tmax spatial cutouts
from the public CC0 ISIMIP3b version20210512 source, DOI
https://doi.org/10.48364/ISIMIP.842396.1. Reuse resident 2041–2050 files.
Each new source contract binds catalogue file ID, path, size, SHA512, model,
member, scenario and version before a server request. Source-parent payloads
are not downloaded or claimed verified; local cutouts receive SHA256 checks.

Validate registered Gregorian daily chronology, including leap days (3653,
3652,3653 days for the three decades), exact grid, units, and finite values.
Reject inconsistent registrations, missing/duplicate dates, differing grids,
source lineages and noncontiguous file sequences. Build with both calendars;
require full 28-year exact rain/heat key matching and identical stage Tmean.
The 2042–2049 subset must reproduce completed joint products exactly.

One bounded job at a time, one numeric thread, initially 1024MiB sampled
process-group RAM. Each acquisition and each subsequent processing batch
may add at most64MiB, preserving at least130GiB free. Previously retained
inputs are counted separately from new processing output; they are not
redownloaded. No unique data deletion. Record cumulative retained storage.
No arbitrary heat response or welfare coefficient will be supplied to turn
these inputs into an apparent empirical damage result.
