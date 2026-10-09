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

A separate fail-closed audit confirms that the agriculture array is a complete
160-region by 7-warming-knot by 3-percentile panel, while each labor array is a
complete 160-region by 7-knot by 16-climate-model panel with unique keys and
finite values. The published loader uses the agricultural and non-agricultural
labor welfare columns directly; it does not use the separate total-welfare
column, so numerical equality among those columns is recorded as a diagnostic
rather than imposed as an undocumented identity.

The 1.46 GB CC-BY-4.0 RFF-SP archive has now been acquired into the ignored
project-local Julia depot, independently matched to its published MD5, and
successfully extracted to 11,007 files.

The first 100-draw RFF-SP staging runs complete under the paper's seed and 2%
discount schedule. Agriculture is $28.82/tCO2 under ISO and $28.76/tCO2 under
Lancet, already close to the paper's rounded $29 headline. Labor is $60.28
under ISO and $33.34 under Lancet; total SCC is $205.78 and $178.42,
respectively. These small-run means have Monte Carlo standard errors of $4.96
and $2.48 for labor and are not the published reproduction. They demonstrate
that the two response functions materially differ and that the Lancet staging
total is close to the paper's rounded $179 total. The registered next gate is
1,000 draws, followed by the authors' 10,000 draws; no function will be chosen
post hoc based on the preferred magnitude.

The 1,000-draw Lancet staging run has now completed under the same registered
configuration. It estimates agriculture at $30.32/tCO2 (Monte Carlo standard
error $0.82), labor at $30.06/tCO2 (standard error $0.71), and the total SCC at
$171.03/tCO2 (standard error $2.52). The 5th-95th percentile intervals are
-$0.20 to $79.59 for agriculture, $0.91 to $72.84 for labor, and $77.65 to
$312.46 for the total. These are still staging diagnostics: they demonstrate
that 100 draws were inadequate for convergence, and they do not match the
rounded published labor mean of $41 or total of $179. The prespecified
10,000-draw run is therefore required before assessing reproduction success or
investigating any remaining configuration difference.
