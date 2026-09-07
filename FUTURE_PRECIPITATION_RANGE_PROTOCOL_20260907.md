# Historical-range diagnostic for future precipitation inputs

Registered after constructing future weighted inputs, before reading their
historical range comparisons. This diagnostic follows immediately from
`FUTURE_WEIGHTED_PRECIPITATION_PROTOCOL_20260907.md`; it is not a model test
that can authorize a projected yield, damage, welfare or SCC estimate.

For each crop, stream the hash-verified historical direct-basis assembly in
8192-row batches. Retain only latitude39.25/39.75N,1982–2010 and positive
observed yields. Do not read terminal2012–2016 outcomes into any calculation.
Take cell-specific feature minima/maxima across available retained years;
require at least two usable years for a defined range and report historical
observation-count distributions. These are direct-table observed-yield
exposures, not necessarily the exact common heat/drought regression sample.
No regression is fit, and yield magnitudes do not weight ranges.

Use all11future exported continuous features. For stage shares/HHI, exclude
historical or future rows whose weighted zero-rain indicator is positive;
zero-rain quantities and heat controls stay available. Missing ranges and
undefined future shapes are reported separately, not counted inside support.
For every exact crop/grid/scenario/year record, count values below historical
min minus1e-10 or above max plus1e-10. This fixed absolute comparison tolerance
only handles numerical boundary ties; it is not an empirical support buffer.
Report evaluated counts, below/above counts and fractions for every feature,
plus any-feature violations on the common evaluable rows. No confidence
interval, significance decision, adaptive trimming or pass threshold is set.

An inside-range value does not establish joint or causal transportability.
Marginal ranges ignore correlated climate drivers and sparse interior support;
future daily Tmax controls, CO2 effects and adaptation remain unresolved. Range
violations can rule out an unqualified within-range claim, not measure crop
damage. Fixed irrigation-area shares are exposure-allocation weights, not
future adaptation, regional welfare weights or separate practice yields.

One monitored process, at most1GiB sampled group RSS, one numeric thread,
no downloads/raw rehydration, at most64MiB extra disk. Only two small derived
range tables and aggregate JSON are written; future inputs remain unchanged.
