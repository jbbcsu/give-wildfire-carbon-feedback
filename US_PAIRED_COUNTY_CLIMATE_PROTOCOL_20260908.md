# Source-matched county climate benchmark on existing paired cutouts

Registered after the overlap inventory and before feature construction.
The inventory identifies only 16 fully covered corn counties (346 observed
county-years) and 15 soybean counties (227 county-years), 1982–2010. Keep this
geographically selected sample explicit. It is too small to pass the old
25-county / 500-row per-practice association contract. Do not relax that
contract, reuse its coefficients or call this an independent holdout.

Build climate features, not a crop response. Use these fully covered counties
only; no partial-polygon normalization, centroid substitution or new download.
Bind the inventory, NASS/nClimGrid source and daily-heat receipts, TIGER
components, and all 18 existing validated factual/counterclim daily sources.

Construct NEW half-degree county-polygon weights. Intersect each complete
county with every overlapping climate cell in longitude/latitude, then project
the clipped pieces to EPSG:5070 and normalize their positive areas. Confirm
the geographic cell union covers the county before normalization; every used
cell must be finite in the validated counterclim mask. Compare total projected
piece area with both the projected original county and TIGER ALAND+AWATER,
using the prior 3% declared-area audit limit. Record residuals, not just pass
flags. Weights include county water and noncrop land and are an exposure proxy,
not crop-area weights. Neither existing nClimGrid weights nor global MIRCA
irrigation weights can be relabeled as these new weights.

Use the exact retained NASS usual-date season start/end for each county/crop/
year, identically across both practices and both climate paths. Check the
retained calendar lineage and days; use floor-defined 0/.3/.7/1 stage bounds.
This is not the global GGCMI calendar and its differences are intentional.
Do not align, shift or interpolate GSWP daily dates to early-morning nClimGrid
dates: preserve publisher labels and report this remaining measurement issue.

For each county, compute within each climate cell before area weighting:
season precipitation, longest run below1mm/day, maximum rolling5-day amount,
stage precipitation shares, across-stage HHI, stage mean temperature, and
stage Tmax exceedance counts and degree-day sums at29C and30C. Convert source
precipitation flux to mm/day and Kelvin to Celsius using float64 arithmetic;
require exact daily chronology, finite values, nonnegative precipitation and
Tmean<=Tmax within1e-5C. No Tmin exists in these cutouts, so do not invent one
or pass a duplicate temperature as a fake Tmin to an older helper.

Stage amounts must sum to season amount. Zero-rain cell shares/HHI use the
existing explicit-zero convention with a weighted zero flag; exclude such
rows from shape contrasts and report counts. Heat days/integrals must sum
over stages. All calculations retain cell-first nonlinear construction.

On exact observed-supported county-years, report factual-minus-counterclim
climate contrasts and factual-GSWP-minus-nClimGrid measurement differences,
first averaged within county then equally across counties. Include county
dispersion, annual equal-county means and complete row counts. No yield
coefficient, welfare weight or SCC calculation. A paired calendar does not
remove resolution, source or day-definition differences. No sampling-
independence or causal identification claim.

First test cell-first nonlinear rain/heat, zero rain, impossible weather,
missing days, and polygon full/partial coverage. Then process one scenario
and ten-year source block at a time, selecting only the union of needed cells
before materialization. Write only a small climate table/weights/receipt in a
fresh ignored directory. Use one numeric thread, sampled1024MiB RSS ceiling,
64MiB owned disk cap,130GiB free-space floor. Compare the two completed climate
tables immediately after construction, preserving all failed runs if any.
