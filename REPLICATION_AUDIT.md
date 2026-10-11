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

## Full 10,000-draw Lancet result

The prespecified 10,000-draw Lancet run completed successfully under Julia
1.12.5, one thread, the authors' random seed (`24523438`), RFF-SP
socioeconomics, a 2025 CO2 pulse, and the paper's 2% near-term Ramsey discount
schedule. The resulting partial SCCs, in 2020 US dollars per metric ton of CO2,
are:

| Sector | Mean | MC standard error | 5th percentile | Median | 95th percentile |
|---|---:|---:|---:|---:|---:|
| Agriculture | 29.05 | 0.28 | -2.90 | 23.64 | 80.41 |
| Labor (Lancet) | 29.26 | 0.23 | 0.19 | 25.01 | 70.78 |
| Mortality | 97.92 | 0.44 | 43.10 | 90.27 | 178.66 |
| Energy | 9.42 | 0.04 | 4.60 | 8.61 | 16.86 |
| Sea-level rise | 2.03 | 0.04 | 0.51 | 1.61 | 4.42 |
| Total (Lancet) | 167.68 | 0.78 | 70.15 | 152.53 | 310.75 |

This is a successful numerical replication of the paper's rounded agriculture
estimate of $29/tCO2 for the Lancet specification. It is not, by itself, a
replication of the paper's $41 labor or $179 total headline estimates. The
article explicitly bases those headline results on two labor response
functions, whereas this completed run fixes the Lancet response function. The
Lancet-only mean is therefore a structural sensitivity result, not a failed
estimate to be overwritten or relabelled. The exact headline comparison remains
gated on completing the matching 10,000-draw ISO run and reconstructing the
paper's cross-function distribution. The official Supplementary Information
confirms that ISO 7243:2017 and the alternative empirical Lancet response are
the two structural labor specifications; it does not provide a scalar shortcut
that would justify substituting the headline mean for either one.

## Full 10,000-draw ISO result and structural reconciliation

The matching ISO run completed with the same Julia environment, seed, RFF-SP
socioeconomics, 2025 pulse, discount schedule, one-thread execution, and
10,000 draws. Its results are:

| Sector | Mean | MC standard error | 5th percentile | Median | 95th percentile |
|---|---:|---:|---:|---:|---:|
| Agriculture | 29.10 | 0.28 | -2.90 | 23.70 | 80.47 |
| Labor (ISO) | 51.86 | 0.44 | 1.04 | 42.15 | 133.88 |
| Mortality | 98.19 | 0.44 | 43.18 | 90.42 | 179.15 |
| Energy | 9.45 | 0.04 | 4.61 | 8.64 | 16.95 |
| Sea-level rise | 2.04 | 0.04 | 0.51 | 1.61 | 4.43 |
| Total (ISO) | 190.64 | 0.95 | 76.35 | 172.42 | 364.94 |

The arithmetic midpoint of the independently replicated ISO and Lancet means
is $40.56/tCO2 for labor, $29.07/tCO2 for agriculture, and $179.16/tCO2 for
the total. These reproduce the article abstract's rounded $41, $29, and $179
headlines, respectively. We treat this as a transparent equal-weight
structural-mean reconciliation, not proof of an undocumented pooling rule:
the archived analysis script runs both functions separately but does not
encode a cross-function aggregator.

The local wrapper retained sector summaries rather than trial-level draws.
Consequently, we do not average the two functions' quantiles or standard
errors and do not claim to have reconstructed the article's cross-function
confidence interval. That would require retained trial-level outputs and a
source-verified pooling rule. The two complete single-function distributions
remain the structural sensitivities. For the cross-sector GIVE expansion, the
equal-weight mean is an evidence-backed central benchmark, with $29.26--$51.86
as the labor structural range. The $29.07 updated agriculture mean is a
candidate replacement for existing GIVE agriculture; it must not be added on
top of either total agriculture or the precipitation replacement module.
