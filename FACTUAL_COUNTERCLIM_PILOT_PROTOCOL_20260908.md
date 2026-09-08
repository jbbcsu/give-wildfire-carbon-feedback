# Paired factual/counterclimate precipitation pilot

Registered before subset submission/acquisition and feature construction.
Purpose: quantify conditional historical precipitation/heat input differences
using existing published counterclimate, not fit a new emulator or crop response.

The official resource10.48364/ISIMIP.982724.3 methods identify counterclim as
ATTRICI1.1 detrending of associated obsclim. Current GSWP3-W5E5 daily obsclim
version20211021 and counterclim20220506 cover the same1901–2019period;
registered subset inputs are1981–2010 only. Three counterclim dataset APIs
return empty caveats/caveats_versions arrays, not proof of absence of defects.
Publication limitations in ATTRICI_METHOD_ASSESSMENT_20260908.md still apply.
The exact code commit used for20220506 is not independently verified; record
this limitation and use catalogue product identity, never claim bitwise
replication of the2021 paper's archive.

Bind all eighteen observed catalogue source IDs/SHA512sizes/versions and
publicCC0 rights in config/isimip3a_{obsclim,counterclim}_*cutout*.json.
Nine factual hashes already match the retained original climate manifest.
Submit only two-row39.25/39.75N server cutouts,720longitudes, no full global
raw hydration. Separate receipts/dirs for each scenario/variable/decade.
Daily pr/tas/tasmax axes must agree within a source and across paired sources;
dates, finite units,nonnegative pr,tas<=tasmax+1e-5°C fail closed.

Build the identical four GGCMI2015soc calendars,686cells/calendar×29harvests
(1982–2010),maize29°C/soy30°C,stages0/.3/.7/1,wetthreshold1mm/day. One latitude
per child; nonlinear features before fixed MIRCA2000 irrigation weighting.
Expected joint support500maize/327soy cells and14,500/9,483rows per source.
Use a separate observational wrapper, not a relabeled GFDL/IPSL source.
No fake observed yields: any API NaN/unobserved placeholders are dropped.

Because counterclim is derived from the factual sequence, exact cell-year
pairing IS appropriate here (unlike free-running GCM/observed comparisons).
Report factual-minus-counterclim per-cell time means then equal-cell averages,
spatial dispersion, temporal quantile differences and yearwise climate
contrasts. Core targets are seasonal total, longest dry spell,Rx5day,
stage precipitation shares,concentration,stage Tmean and threshold heat.
Shape comparisons exclude cells with any zero-precipitation regime in either
source, with explicit denominator. Do not silently replace undefined shares.

Validate newly constructed factual fields against retained observed-source
direct/heat fields on exact shared keys; report coordinate,missing and numeric
differences without changing tolerances after seeing the result. Numerical
equality tolerance:1e-8absolute,1e-10relative for derived floating fields;
flags/keys exact. Failure prevents accepting a paired result. Compare crop
calendars and weight hashes exactly. No bias correction or precipitation-only
temperature swap is applied. Joint climate contrasts are climate diagnostics,
not quantities to add separately to crop damages.

Report full1982–2010 paired climate differences, with predeclared early1982–1991
and late2001–2010 subperiod summaries to describe changing differences, not to
select a favorable window. No uncertainty intervals from treating grid cells
as independent. Two-row support is not globally representative. Product
detrending removes historical trends irrespective of cause; do not call the
difference purely anthropogenic or a marginal-emissions effect.

One monitored group/one numeric thread,1024MiB sampledRAM,<=64MiB new disk
per acquisition/build,>=130GiBfree. Count cumulative retention. No cleanup or
overwriting existing products. Acquisition is authorized; all empirical yield,
causal transport,adaptation,welfare and SCC promotion gates remain closed.
