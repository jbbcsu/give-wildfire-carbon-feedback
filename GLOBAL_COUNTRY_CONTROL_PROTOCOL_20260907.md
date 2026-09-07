# Country-control sensitivity: source mapping and historical estimation

Exploratory, registered before country-control fits. No production response,
welfare weights or causal/SCC promotion. First construct a country-label proxy
from the retained, hash-verified MapSPAM maize/soy union footprint. It is not
an independent administrative boundary map or GDHY's underlying source-unit ID.

Recheck the country labels against the retained official NGA/UN crosswalks.
Map each five-arc-minute center to its enclosing half-degree center, using
integer grid indices. Assign a label only when every retained fine cell in
that half-degree cell has the same resolved country label. Mixed-country
cells remain ambiguous; absent cells remain unmapped. Do not choose a majority
threshold after examining yields. Use the union footprint for both crops,
not crop-specific production-weighted country choices. Source and gridded
derived data remain ignored because redistribution is not authorized.

Join labels to the existing direct/heat/scPDSI common-support consecutive
differences ending in 1983–2010. Preserve counts of singleton-mapped,
ambiguous and absent pairs for each crop. Report country and country-year
counts. The circa-2000 crop footprint may select a historical subsample and
does not establish historical border consistency or independent outcomes.
TWN may remain an explicit GENC label for grouping; no UN M49 welfare mapping
is inferred. If coordinate or code validation fails, stop before fitting.

On exactly the singleton-mapped subset, compare unrestricted global end-year
intercepts with country-by-end-year intercepts. Keep the existing six linear
stage mean-temperature/daily-heat controls (29 C maize, 30 C soy), four
separate moisture families and partial contrasts from the global historical
association protocol. No changes to moisture terms, outcome definitions or
terminal-test exclusions. Global-year fits on the matched subset distinguish
the effect of sample restriction from the change in controls.

Absorb the chosen intercept groups from both feature differences and log-yield
differences by group demeaning. Cluster covariance by country and, separately,
20-degree geographic blocks, retaining all 16 fits and 32 covariance records.
Use CR1 correction G/(G-1)*(N-1)/(N-H-K), where H is the number of absorbed
intercept groups and K the rank of the remaining feature matrix. Do not count
millions of pixels as independent observations. Nested-country fixed effects
may make this correction conservative; no finite-sample exact-inference claim.
Small or singleton country-year groups are retained (their demeaned rows are
zero), not silently replaced. Report such groups. Do not select by significance.

Use normal conditional intervals, as in the earlier descriptive fit, and test
the absorbed estimator and cluster covariance against an explicit synthetic
dummy-variable regression before real fitting. Keep the fitted-model changes
separate from the untouched out-of-sample evidence. Country controls cannot
by themselves repair GDHY construction dependence, measurement error, omitted
local drivers, adaptation or climate transport. No coefficients are exported
as a production response bundle.

One monitored, single-thread, existing-data job at a time. Stream the CSV and
Parquet inputs, retain only necessary columns and small output, with no new
downloads. Finish the mapping, then immediately run the tested sensitivity
if it is usable; do not repeat completed broad audits.
