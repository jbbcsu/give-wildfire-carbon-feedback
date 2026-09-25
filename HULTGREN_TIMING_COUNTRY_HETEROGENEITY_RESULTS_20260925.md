# Country heterogeneity in maize rainfall quantity and timing

## Result

A production-weighted country decomposition now separates total-rainfall
quantity from within-season redistribution for the published Hultgren maize
response. The climate contrast is the 2092--2100 SSP5-8.5 minus SSP1-2.6
endpoint across GFDL, IPSL, MPI, MRI, and UKESM. It is a scenario diagnostic,
not a marginal carbon pulse, monetary damage estimate, or SCC.

The equal-five-model global mean net precipitation response is -0.01956 log
yield points. The quantity reference contributes -0.01514 and the timing/
distribution residual contributes -0.00443. Thus the global timing term is
29.3% of the absolute quantity term in this production-weighted endpoint
comparison. This is close to, but distinct from, the previously reported
31.2% origin-constrained per-kelvin slope ratio.

Across 144 balanced-support countries, 111 have a negative equal-model mean
and 33 have a positive mean. Only 65 are negative in all five models and only
three are positive in all five; 76 change sign across models. Gross country
contributions are -0.02167 on the loss side and +0.00211 on the benefit side,
which net to -0.01956. Timing amplifies the quantity sign in 95 countries and
offsets it in 49.

The largest absolute equal-model country components are the United States
(-0.00942), India (-0.00211), Mexico (-0.00157), Romania (-0.00130), and
Brazil (+0.00113) log-yield contribution points. The United States changes
sign in one model; India, Mexico, and Romania are negative in all five; Brazil
is positive in four of five. China is particularly informative about the
distribution channel: its quantity contribution is approximately zero
(+0.000003), while timing contributes -0.000838 and drives its negative net
mean. In India, timing instead offsets about one third of the negative
quantity contribution.

## Weighting and validation

The headline decomposition uses fixed MapSPAM 2000 physical maize production,
not the flagged FAOSTAT constant-dollar field that overweights Venezuela. The
five component exports exactly reconstruct their source production-weighted
aggregates. A separate standard-library validator reconstructs country means,
the global decomposition, and winner/loser counts from the compact country-
model table.

The result strengthens the case for retaining distribution explicitly: a
small or near-zero quantity effect can conceal a material timing effect in a
country. It does not pass the existing marginal-SCC promotion gate. The five
scenario endpoints contain multiple forcings and internal variability, the
timing term is a reference-path residual rather than a uniquely identified
causal effect, and the country contributions are physical-response accounting
rather than welfare damages.

## Reproduction

- Component export: `scripts/export_hultgren_timing_component_cells.py`
- Country aggregation: `scripts/summarize_hultgren_timing_country_heterogeneity.py`
- Independent validator: `scripts/validate_hultgren_timing_country_heterogeneity.py`
- Result receipt: `data/provenance/hultgren_timing_country_heterogeneity_production_20260925.json`
- Validation receipt: `data/provenance/hultgren_timing_country_heterogeneity_validation_20260925.json`
- Compact country-model table (ignored):
  `data/interim/hultgren_timing_country_heterogeneity_production_20260925.csv`
