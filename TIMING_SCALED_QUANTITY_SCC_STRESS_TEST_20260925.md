# Timing-scaled quantity-SCC stress test

This diagnostic asks a deliberately limited scale question: what would happen
to the validated -$0.00610/tCO2 annual-rainfall quantity benchmark if the
late-century maize timing-to-quantity response ratio applied unchanged to the
marginal SCC path?

Using the production-weighted pooled endpoint ratio of 0.2925, the mechanical
timing increment is -$0.00178/tCO2 and the combined value is -$0.00789/tCO2
(2020 USD, 2% schedule). Applying the five individual endpoint ratios yields
combined values from -$0.01445 to -$0.00539/tCO2. One model's timing term
offsets quantity; four amplify it.

These numbers are **not timing SCC estimates**. They impose a late-century,
SSP5-8.5-minus-SSP1-2.6 scenario ratio uniformly across countries, years, the
26 EPA climate patterns, market responses, and the matched FAIR pulse. That
ratio failed the preregistered whole-ESM promotion gate and contains multiple
forcings and internal variability. The five cases are structural stress tests,
not draws or confidence bounds.

The calculation is nevertheless informative about scale. Under this strong
proportionality assumption, adding timing changes the narrow maize result by
roughly two thousandths of a dollar per tonne in the pooled case and does not
make the maize-only SCC large. Therefore, a materially larger complete
precipitation SCC would need to arise primarily from drought/water-balance
effects, additional crops, irrigation and water costs, nonlinear extremes, or
market interactions—not merely from multiplying the current maize quantity
channel by the pooled timing ratio.

Reproduction:

- Script: `scripts/stress_test_timing_scaled_quantity_scc.py`
- Receipt: `data/provenance/timing_scaled_quantity_scc_stress_test_20260925.json`
- Independent validation:
  `data/provenance/timing_scaled_quantity_scc_stress_test_validation_20260925.json`
