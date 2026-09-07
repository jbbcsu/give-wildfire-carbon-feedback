# Direct climate-feature scenario contrasts

Descriptive comparison registered before calculation. Use the retained,
hash-pinned expanded ISIMIP3b feature table, not an emulator. Its support is
maize/rainfed-calendar cells at 39.25 and 39.75 degrees north, not the globe
or the entire United States. Read one ESM at a time in 8,192-row batches.

For each of five ESM/member combinations, compare SSP5-8.5 and SSP3-7.0,
separately, with SSP1-2.6 in 2042–2049 and 2092–2099. Require exact matching
cell/year support and all eight years. Average within each cell over years,
then equally across cells. Report all model-specific means, differences and
10th/50th/90th spatial quantiles of cell-mean differences. Summarize the five
ESM mean differences by their median and range, not a confidence interval or
probability distribution. These selected ESMs are not independent draws.

Retain all 11 features: growing-season mean temperature, rainfall total,
wet-day count, maximum dry spell, Rx1day, Rx5day, three rainfall stage shares,
normalized timing centroid and concentration HHI. For shares, timing and HHI,
use only cells with positive total rain in all eight years of both paths;
report any excluded cells. Do not give undefined shape a zero value. Report
whole-season zero-rain occurrence separately on the full sample. Share changes
are percentage points when displayed, not percent changes in rainfall.

Report the full calendar-support band and its USA- and CHN-labeled subsets
using the retained singleton-country footprint proxy. These subsets are
cross-sections within the band, not national projections or observations.
Country-ambiguous/absent cells remain in the full band but not those subsets.
No crop-area, production or welfare weights are introduced. Missing subset
support is reported, never guessed. Both scenarios use exactly the same cells.

Check scenario/year uniqueness, crop/regime identity, same ESM/member and GMST
identity, finite values, physical feature bounds, stage sums (one for positive
rain and zero for zero-rain seasons), and paired keys. Retain the corresponding
same-realization annual GMST contrast without estimating a marginal slope.
Test pairing and dry-shape handling with explicitly synthetic fixtures.

A shared model/member name does not guarantee matched weather noise after
scenario divergence. Eight-year differences contain internal variability and
are not 30-year climate normals. SSP contrasts include multiple forcing
differences; neither pathway is a no-climate-change counterfactual. This is
not isolated CO2 attribution, an emissions pulse, a globally validated
precipitation response, an agricultural impact, or an SCC. Do not apply the
historical yield coefficients or alter the rejected emulator's gates.

One monitored job; no source downloads, raw-data rehydration or large outputs.
