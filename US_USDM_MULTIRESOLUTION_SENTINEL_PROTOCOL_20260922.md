# USDM agricultural-area multi-resolution sentinel protocol

**Frozen:** 2026-09-22, before constructing a sub-4-km grid or inspecting any
1 km or native-30 m exposure result.

## Purpose and boundary

Test whether assigning each 3.96 km agricultural-support cell to the USDM
class at its center creates material spatial error. This is an
outcome-independent measurement audit. Yield, response coefficients, model
fit, significance, damages, and SCC values are not used in sentinel selection
or resolution comparison.

## Outcome-blind sentinel selection

Using only the completed 3.96 km **cultivated** grid and official weekly USDM
vectors:

1. Rank the 2,909 continental counties by cultivated CDL area and divide the
   deterministic rank into eight equal-count strata.
2. For every county-week, calculate boundary ambiguity as one minus the
   largest mutually exclusive none/D0/.../D4 agricultural-area share.
3. Within each area stratum, rank counties by the 95th percentile of weekly
   ambiguity, then maximum ambiguity, then GEOID. Select the first county from
   a state not already represented when available; otherwise select the top
   county. This yields eight counties spanning agricultural-area rank and high
   boundary complexity without using crop outcomes.
4. For each selected county, retain its three highest-ambiguity weeks subject
   to at least 28 days between selected map dates. These 24 county-weeks are
   the native-resolution boundary sentinels.

The selector writes and hashes its complete scores, selected GEOIDs/dates,
source grid, vector manifest, and rule before any finer grid is built.

## Two-part resolution comparison

- Build a 990 m (`33 x 30 m`) grid for the eight counties and compare complete
  2001--2013 annual D0--D4 exposures with the existing 3.96 km grid.
- For the 24 selected county-weeks, calculate agricultural shares directly
  from all 30 m CDL pixel centers in bounded raster blocks. Compare both 990 m
  and 3.96 km shares with this native-pixel reference for the cultivated and
  broad agricultural masks.

All six mutually exclusive shares, including no drought, are retained. Total
variation distance (TVD) is one half the sum of absolute share differences.
No mask, county, date, or class may be removed after results are visible.

## Frozen advancement thresholds

The 3.96 km national route passes this sentinel gate only if all conditions
hold:

- across the 48 mask/county-week comparisons, median native-reference TVD is
  at most 0.03, the 90th percentile is at most 0.08, and the maximum is at most
  0.15;
- across the eight-county, two-mask, thirteen-year 990 m comparison, the
  median absolute D0--D4 annual difference from 3.96 km is at most 0.15
  equivalent week, the 90th percentile is at most 0.50 week, and the maximum
  is at most 1.00 week;
- the 990 m median and 90th-percentile native-reference TVD are no more than
  0.002 and 0.005, respectively, above the corresponding 3.96 km values; and
- all spatial weights, exclusive categories, source identities, annual
  calendars, resource bounds, and independent arithmetic checks pass.

The thresholds limit typical weekly allocation error to a few percentage
points and annual category error to days rather than weeks. Failure is
reported; the sample or thresholds are not revised in response. Passing does
not make the historical yield associations causal or transferable and does not
authorize a global damage or SCC coefficient.
