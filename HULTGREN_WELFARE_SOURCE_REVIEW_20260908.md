# Published welfare route: primary-source review and implementation boundary

The publisher supplement for Hultgren et al. (2025), *Impacts of climate change
on global agriculture accounting for adaptation*, is now locally available.
Section K was text-read and visually checked in full: PDF pages79–88, printed
SI-76–SI-85, including Figures S19–S21 and Table S13. The rest of this95page
supplement has not been fully reviewed. Acquisition hash and source URL:
`data/provenance/hultgren_methods_si_acquisition_20260908.json`. The original
PDF and review renderings remain outside Git; no redistribution license has
been asserted. [Publisher article](https://www.nature.com/articles/s41586-025-09085-w),
[publisher supplement](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41586-025-09085-w/MediaObjects/41586_2025_9085_MOESM1_ESM.pdf).

## What is now verified and relevant

K.1/K.4 distinguish a foreseen production change, to which planting can respond,
from an unanticipated annual shock after planting. Storage moderates the latter
through a39% shrinkage of the *price-level deviation* from the anticipated
equilibrium. This is not a39% reduction in damages, not log-price averaging,
and not an explicit inventory/stockout model. These mechanisms are absent from
our earlier fully anticipated closed-market accounting core.

K.3 aggregates income-adjusted potential yields, irrigation shares, planted
areas and crop calorie factors. Crop-revenue projections set baseline value;
GDP is not itself crop revenue. Market geography is a country baseline with
continent/global alternatives. Thus a global SCC target does not by itself
imply one frictionless global commodity market. These scope/weight choices
cannot be replaced by equal grid-cell means or a dollar value per yield unit.

K.6 gives three supply/signed-demand scenario pairs:0.08/−0.02,0.10/−0.04,
and0.50/−0.06. These are author scenario assumptions, not our newly estimated
parameters or interchangeable with the six alternative AER Appendix A8 fits.
K.4.2 also considers expenditure bounds; K.4.1 applies a55% additional
flexibility adjustment. Neither is automatically our fixed/trend/upper
adaptation scenario. Importing them on top of an adaptation-inclusive yield
response could count adaptation twice.

K.5 fits temperature-indexed monetary damage functions and evaluates a FaIR
emissions pulse. It is a route from validated monetary outcomes to SCC, not
permission to transform our precipitation means directly into dollars.
Our GIVE implementation must retain GIVE's scenario, pulse-unit, discounting,
currency and replacement conventions; this source's reported SCC is not ours.

## Ambiguities retained, not silently resolved

1. Printed SI-80 first describes15previous years, then specifies a13year
   Bartlett kernel. Exact expectation construction needs replication-code
   inspection. The new component therefore requires an externally supplied
   expected supply ratio; it does not select a smoothing window.
2. Printed SI-81 lists66%,66%,47%,50% and describes55% as their unweighted
   average. Those printed numbers average57.25%. Retain the stated55% as a
   reported author assumption, flag the arithmetic discrepancy, and do not
   substitute57.25% or import either as a fitted adaptation estimate.
3. The compact surplus equations do not separately label all baseline versus
   realized supply-cost/inventory conventions. The storage-adjusted price is
   not generally the intersection of demand and the realized long-run supply
   curve. Do not feed it into our old closed-market surplus function as though
   it were. Replication-code inspection or a separately justified inventory/
   welfare model is still necessary. For demand elasticities near zero,
   compute finite *surplus differences*, not divergent utility integrals
   starting at zero quantity.

## Implemented next step: prices/quantities only

`src/anticipated_weather_market.py` independently expresses K.1/K.4's
unambiguous normalized price/quantity sequence. Let e>0 be supply elasticity,
d>0 demand-elasticity magnitude, a=log(Q1_expected/Q0), b=log(Q1_realized/Q0).
Then anticipated log price is −a/(e+d), anticipated log quantity is
d*a/(e+d), and pre-storage realized log quantity adds(b−a). The pre-storage
log price is minus that realized log quantity divided by d. Final price is
the arithmetic blend of raw and anticipated prices with explicit shrinkage
weight. Final quantity is read from the demand curve.

The code uses stable log arithmetic, accepts only finite valid inputs, and
returns ratios only. Tests check the fully anticipated limiting case against
the existing independent market core, direct power-form arithmetic, storage
endpoints, bad domains and threshold-independent numerical behavior. There
are no fitted yield inputs, baseline dollars, surplus, inventory accounting,
adaptation adjustments or SCC outputs. This is an independently implemented
*part* of the published procedure, not a complete paper/code replication.

Next economic work: inspect the monetization replication files and license,
resolve expectations/cost/inventory conventions, obtain harmonized baseline
calorie/revenue inputs, and specify the adaptation accounting boundary before
exporting any empirical welfare curve. The source-access blocker is resolved;
these scientific requirements are not.

## Replication scope checked after the PDF review

At commit`3ccdffcd4e4ff6e55566ce76e2aac130ee86349a`, the public GitLab root
README describes replication of main figures, the main table and regressions,
with impact data supplied separately. Root listing contains no license-named
file; this does not prove no license exists elsewhere. Complete recursive
listings for`Table1` and`Fig3/3d_damages` show figure/calorie-analysis inputs
and utilities, but did not locate the K.4 monetary market implementation.
No raw impact bundle was downloaded, no environment file was read, and no
third-party code was copied or executed. Public API access succeeded after
the web reader's cache miss; do not repeat that failed web route.

Observed response SHA256s (read-only response evidence, not saved payloads):

- Root README: `de7b45104eda4f195620cfd8089c77294117512d78036b6ae371b921f2fcf4ac`.
- Recursive Table1 listing: `82cd3f3f100122a05ed67780d4a9d3d3e8db8cb760817c3b3abcd4b99c9dbcad`.
- Recursive Fig3/3d_damages listing: `3542df1741dd5cc1d38aea895e96a74a68e900cbbefffe5caa070c56fcec8bf9`.

[Pinned replication README](https://gitlab.com/ClimateImpactLab/cil-ag-replication-package/-/blob/3ccdffcd4e4ff6e55566ce76e2aac130ee86349a/README.md).
The inspected paths do not establish that the full monetary pipeline is
unpublished; locating its actual repository/source remains the next source task.
