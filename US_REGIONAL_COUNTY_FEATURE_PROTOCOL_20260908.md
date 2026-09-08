# Regional NASS-calendar paired weather construction

Prospective extension of the completed16/15county benchmark. All54registered
regional acquisitions must first have successful source-bound receipts. Do
not select a completed band because its results are favorable. This phase
constructs climate inputs and coverage diagnostics only; no yield response,
projection, welfare or SCC calculation is authorized by the resulting table.

Use the same positive paired-practice NASS/nClimGrid source and original
1982–2010 support:6,094corn and4,308soy unique county-years before additional
climate-domain exclusions. TIGER2019 components and input/calendar lineage
must retain their existing validated hashes. Do not add the two practices as
independent climate observations. Preserve original county/calendar names,
dates and reference weather; no pseudo-yields or Tmin fields in new products.

The three registered16x70bands form one48x70rectangle, with no duplicate
centers. Require the validated counterclim mask to match across all variables
and decades within each band; factual fields must be finite on all rectangle
cells. Reuse the completed all-day mask validation through its source hash.
Inventory whole/partial/no positive-area coverage of each relevant county by
the finite-cell union. Only wholly covered counties receive new features;
retain excluded counties and observation counts in the coverage receipt.
This is an explicit geography selection, not an assumption that partial
county observations represent whole-county crop outcomes.

Construct EPSG:5070 intersection-area weights with the already tested county
weight kernel. Restrict candidate grid cells by geometric bounding boxes only
to save computation; this must give identical weights to a complete grid scan
in synthetic tests. Check area sums and the same3% declared-area audit limit.
Normalize only after proving complete geographic coverage. Weights remain
whole-county land/water proxies and are not crop or irrigation-area weights.

For both obsclim/counterclim paths and each source decade, select only the
required grid cells before materialization. Concatenate the three bands along
the selected-cell dimension, requiring matching exact time axes and complete
source identities. Release each decade's arrays before the next. Use the same
tested three-input feature kernel and NASS seasons as the pilot: rainfall
quantity/distribution, stage temperatures and29/30C Tmax heat integrals/counts,
cell-first nonlinear construction. Reject nonfinite, negative precipitation,
Tmean>Tmax+1e-5C, missing days, changed stage sums, or duplicate/altered keys.
Do not widen a numerical/physical gate in response to a failed real run.

On the573previously validated pilot county-years, require identical keys,
dates and scenario and numerical agreement with each old climate product at
the existing1e-8absolute/1e-10relative tolerance; zero-rain flags must match
exactly. Record maximum residuals and input hashes. This tests overlapping
source extraction, calendars, geometry and nonlinear construction without
requiring different floating-point array layouts to be bitwise identical.

Emit one climate table per path, a complete coverage/weights/source receipt,
and counts by crop/state/year. Compare both paths and retained nClimGrid on
exact matched keys immediately afterwards using a source-specific comparator.
No new untouched validation years are available in the retained weather
sample. Larger spatial coverage is not global representativeness, independent
validation, or proof that coefficients transport across climate sources.

One bounded job/thread,1024MiB sampled process-group RSS,64MiB owned new disk,
130GiB minimum volume free space. If the guard stops a batch, preserve it and
split the processing batch explicitly rather than increasing RAM. Existing
original-strip builders/results remain unchanged. Subsequent response fitting
still needs a separate frozen source-matched study contract and existing
sample/promotion, causal attribution and SCC gates remain in force.
