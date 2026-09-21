# Registered EPA/FAIR annual precipitation-pulse benchmark

## Purpose

Demonstrate the exact low-cost pathway from a matched GIVE/FAIR temperature
pulse to published country-level annual precipitation changes. This is the
closest quantity-only analogue to the published climate-link step used in the
wildfire project. It is a climate-input benchmark, not a crop response,
agricultural damage, welfare estimate, or SCC increment.

## Frozen inputs and formula

Use the validated EPA benchmark result SHA-256
`f444a693120b4040c959f5425a1fc2e641a6150fd4566aaf033ed2b202388c19`
and its scenario-deduplicated country/model slope table SHA-256
`e6bc9a4dbc0af19650f2f243802e0e1974d3599292cf2704aad0e746bf0c0572`.
Use the validated core-GIVE FAIR path SHA-256
`aedf6b66dd296337e1cb6105d2aa56ec94f3e15e5ac92c2abcdf74b6a42b6067`
and provenance receipt
`data/provenance/give_fair_temperature_path_smoke_20260827.json`.

For country `c`, climate model `m`, year `t`, and pulse size `p`, calculate

`delta_precip[c,m,t,p] = beta[c,m] * delta_temperature[t,p]`,

where `beta` is EPA's area-weighted annual precipitation slope in
mm yr-1 K-1 and `delta_temperature` is pulse minus paired baseline in K.
Do not add an intercept or invent baseline precipitation. Missing EPA
country/model slopes remain missing and are never imputed.

## Checks and compact output

Require the exact 1750–2300 by four-pulse FAIR product, identical baseline
path across pulse sizes, zero-pulse identity, no divergence through 2020, and
three positive pulse sizes (0.0001, 0.00005, 0.000025 GtC). Require the same
4,703 finite EPA country/model pairs and 184-country support as the parent
benchmark.

For 2021, 2030, 2050, 2100, 2200, and 2300, report for every positive pulse:

- the FAIR temperature difference;
- min, 5th, 25th, median, 75th, 95th, max, and mean annual precipitation
  difference across finite country/model pairs;
- positive/negative pair fractions; and
- counts of positive/negative country ensemble medians.

Across every post-2020 year, verify decreasing-pulse convergence after
normalizing both temperature and precipitation differences by pulse size.
Record maximum absolute and relative normalized disagreement between the two
smallest positive pulses. A separate implementation must reconstruct every
reported selected-year scalar and convergence diagnostic.

## Interpretation boundary

The benchmark may establish that published annual-quantity patterns can be
mapped to the actual marginal FAIR temperature path. It cannot represent
crop-season timing, wet days, dry spells, Rx1day/Rx5day, drought, joint
temperature–moisture dependence, yields, irrigation, adaptation, economic
loss, replacement of GIVE agriculture, or SCC. Those remain separate gates.
