# Existing U.S. inputs versus paired climate support

Prospective feasibility inventory; no new regression, prediction or damage
calculation. Use the exact retained direct-practice NASS/nClimGrid table and
its validated source receipt, daily-heat receipt, predictive protocol and
existing TIGER2019 component hashes. Do not read the NASS credential file,
download weather or hydrate evicted data. Resident TIGER files were checked
before this inventory. Stream county shapes, not all geometries into memory.

For the 1982–2010 overlapping period, count unique crop/county/year records
and distinct counties, ignoring duplicated weather across the two reported
irrigation practices. Check that both practices exist at each key. Inventory
all counties with retained 1981–2019 direct-weather records as well.

Transform TIGER polygons using their stored CRS into longitude/latitude.
Classify exact polygon coverage by (a) the 39–40 N latitude strip and (b) the
union of the 686 finite half-degree counterclim cells. The latter mask is
read from one day ONLY after its source hash and completed static-daily-mask
receipt validate. This is reuse of a completed daily validation, not a new
claim that one day proves temporal completeness. Cell boundaries are center
plus/minus 0.25 degrees. Reject changed centers or counts.

Classify each geometry as wholly covered, partially overlapping, or no
positive-area overlap using polygon operations in geographic coordinates.
These are topology/support classifications, NOT projected areas or exposure
weights. Do not use centroids, rounding, buffering or relaxed bounds to turn
partial counties into full coverage. Report full-coverage county IDs locally
for the next registered step. No county features are created from existing
GGCMI-calendar crop summaries, which use a different calendar and weighting.

Audit available years against the existing 1981–2018 association sample and
the already evaluated 2012–2019 predictive terminal period. Inspect source
manifests for additional NASS years without claiming their weather is ready or
their outcomes untouched. An existing holdout reused in multiple completed
analyses is not new independent confirmation. County NASS outcomes are more
direct than reconstructed grid yields but may share upstream national inputs
with GDHY; do not claim full statistical independence without a lineage audit.

First test geographic full/partial/touching/disjoint cases, including a hole
in the climate-cell union, duplicate county/crop/year/practice records and
unpaired practices. Then one existing-data job under sampled1024MiB RSS,
64MiB owned new disk,130GiB free-space floor, one numeric thread. Export a
small hash-bound inventory and report whether a source-matched county climate
benchmark is feasible without new downloads. The inspection does not change
any prior response/causal/welfare/SCC gate.
