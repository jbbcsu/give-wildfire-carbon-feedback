# Expand paired climate coverage to the retained U.S. reporting sample

Prospective acquisition and climate-validation contract, not a response fit.
The completed exact-polygon inventory locates 419 retained direct-practice
counties between109.046954W and74.984165W,25.837164N and49.000692N. Their
1982–2010 subset has346 corn and252 soybean counties. The earlier one-degree
strip covers only16/15 whole counties, below the existing response sample
gates. Preserve those gates; expand climate coverage rather than fitting an
under-supported response or pretending a partial county is fully covered.

## Geography and source identity

Use the enclosing half-degree-cell rectangle109.5W–74.5W,25.5N–49.5N,
selected from county geometry only, not yields or estimated effects. Split
it into three nonoverlapping 8-degree latitude bands: south25.5–33.5,
central33.5–41.5, north41.5–49.5. Each has16 latitude centers and70 longitude
centers,1,120 cells, fewer than the original two-row global cutout's1,440.
All three bands are planned; do not retain only a favorable crop or region.

Use the same18 source files already catalogued and validated: GSWP3-W5E5
obsclim20211021 and counterclim20220506, pr/tas/tasmax,1981–1990,1991–2000,
2001–2010. Child configurations reference the original parent source config
and its hash. Revalidate the parent's published dataset/file/access/CC0/DOI
metadata using the existing source checker, but never submit its old bbox.
The new regional payload must equal the separately registered band exactly.
No global file download, altered source identity, time interpolation or output
averaging. This entails at most54 regional source archives; no new source
model or member is inferred. A full source mask can still exclude coastal
county pieces; geometry coverage is not a promise of finite daily coverage.

## Validation and resource controls

Preserve all old cutout validators unchanged. The new validator binds exact
regional coordinates, source dates/calendar/units and dataset identities.
For factual files require finite weather throughout the rectangle. For the
counterclim files, extract the four hash-verified GGCMI2015soc calendar masks
on this exact region. They must agree; every valid cell must be finite every
day and every nonvalid cell must be consistently NaN, with no imputation.
Reject any changed/intermittent mask, infinity or negative precipitation.
This is a source-domain check; subsequent U.S. crop seasons still use NASS
calendars, not GGCMI planting dates. If mask equality fails, preserve the
failure and investigate source lineage before any analysis or exception.

Register, submit, and acquire each exact archive once. Preserve uncertain
POST receipts rather than duplicate requests. A pending server job is not a
completed download; resume that same job. Enforce exact output URL, HEAD/GET
length and ETag,16MiB archive cap, safe single-NetCDF extraction, parent source
hashes, downloaded archive/NetCDF hashes, and per-job64MiB total new disk.
If the archive cannot fit, preserve metadata and subdivide under a new explicit
resource amendment; do not silently bypass a cap or download the parent file.
Use existing bounded one-thread1024MiB sampled-RSS monitoring and130GiB free
space floor. Pause new acquisition below the floor but continue safe existing
data work. Track cumulative retained bytes. Standing data authorization
applies; no per-file user request is necessary.

## Next scientific step

After complete regional climate coverage validates, recompute exact county
polygon finite-area support. Build NASS-calendar cell-first weather features
on supported counties, in small source blocks. Quantify paired climate and
source differences before a separately frozen joint response study. No earlier
coefficient or model-selection gate is promoted by this acquisition. Reused
1981–2019 validation years remain reused; the existing calendar/irrigation,
source-dependence, CO2/adaptation, attribution, welfare and GIVE-pulse problems
are not solved by downloading a larger rectangle.
