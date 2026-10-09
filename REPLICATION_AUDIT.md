# Published labor and agriculture fast-route audit

## Decision

Use the published Moore et al. (2026) implementation as the primary fast route
for a new labor-productivity sector in GIVE. Do not copy the paper's headline
`$41/tCO2` as a scalar. The authors released the model changes, country damage
functions, uncertainty machinery, socioeconomic inputs, and SCC scripts needed
to reproduce and then integrate the sector transparently.

## What is directly reusable

- A `Labor` Mimi component with country-level agricultural and non-agricultural
  welfare losses interpolated at 0.5-degree warming increments.
- Two competing heat/productivity response specifications (`ISO` and `Lancet`).
- Fifteen GCM realizations plus an ensemble, with GCM selection represented in
  the Monte Carlo analysis.
- An updated agriculture component and seven-point country damage functions.
- Partial-sector SCC bookkeeping, including country-level labor SCC outputs.
- The exact Julia 1.12.5 package environment and a 10,000-draw analysis script.

## Gates before promotion into the cross-sector paper

1. Reproduce the authors' 2025 labor and agriculture sectoral summaries under
   RFF socioeconomic uncertainty and their random seed.
2. Verify sign, price-year, pulse-size, emissions-year, discounting, and GCM
   sampling conventions against the article and supplementary methods.
3. Confirm that agricultural labor losses and the updated crop-market damage
   function are additive in the authors' GTAP construction; do not assume this
   for other agriculture specifications.
4. Compare the published updated total-agriculture sector against the new
   precipitation-attribution module. The latter should replace or decompose the
   relevant moisture channel, not be added wholesale to total agriculture.
5. Preserve both labor response functions as structural uncertainty; do not
   select one post hoc because it gives the preferred SCC.

## Initial validation

The official archive checksum matches Zenodo, the authors' pinned dependencies
instantiate under Julia 1.12.5, and a one-thread deterministic SSP2-4.5 smoke
test successfully produced distinct ISO labor, Lancet labor, and agriculture
partial SCCs. Those values are diagnostic only and are not manuscript results.

The remaining exact-replication dependency is the 1.46 GB RFF-SP archive. It is
CC-BY-4.0 and is being acquired into the ignored project-local Julia depot. The
download is a throughput bottleneck, not an identification or code bottleneck.

