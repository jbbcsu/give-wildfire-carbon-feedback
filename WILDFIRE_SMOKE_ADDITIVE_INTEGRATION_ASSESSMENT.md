# Wildfire-smoke PM2.5 additive-integration assessment

## Decision

The Williams et al. draft supports a source-pinned wildfire-smoke mortality benchmark of **$50.04 per metric ton of CO2** (rounded headline: $50; conditional 95% interval: $18.5–$102.6). It is already reported for a 2025 CO2 pulse in 2020 US dollars, so neither a price-year conversion nor a pulse-year conversion is warranted.

This scalar is **not currently authorized for addition** to either the nonwildfire air-pollution benchmark or the baseline GIVE SCC. It is a separate named component and a reproduction target, not a locally reproduced additive result.

The confidential draft is not stored in this repository. Its SHA-256 and byte count are pinned in a small provenance receipt so a locally held copy can be reverified without redistributing it.

## Exact normalization target

An exact joint GIVE estimate must use:

- a 2025 metric-ton CO2 pulse, with its numerical pulse size and gas-mass convention explicitly pinned;
- 2020 US dollars;
- annual marginal damages from 2025 through 2300, with the final-year convention resolved;
- matched baseline and pulse draws;
- GIVE's 2.0% near-term Ramsey parameterization: `prtp = exp(0.001972641) - 1` and `eta = 1.244458999`;
- the same global per-capita net-consumption path for discounting all sectors in a joint run; and
- country-by-year-by-draw smoke mortality damages, rather than a post hoc scalar sum.

The scalar needs no arithmetic currency or pulse-year adjustment. It does need a joint rerun for an exact total because adding damages changes net consumption and therefore the endogenous Ramsey discount factors marginally.

## Overlap audit

### Nonwildfire PM2.5

The physical emissions boundary is separable. The McDuffie et al. benchmark excludes open burning, including wildfire emissions, while Williams et al. represents wildfire smoke.

The health-burden boundary is not yet coherent enough for scalar addition. McDuffie uses a nonlinear Fusion risk model for specified disease causes and ages, while Williams uses a linearized all-source PM2.5 hazard ratio applied to all-cause mortality. Without a common health function, mutually exclusive attribution rule, and joint uncertainty draws, adding the two scalars is not guaranteed to represent a coherent total attributable mortality burden.

### GIVE temperature mortality

Baseline GIVE's Cromar mortality sector monetizes temperature-associated net all-cause mortality. The underlying review notes that air pollution was often treated as a mediator in temperature-health studies and also recognizes interaction and compound-risk concerns. No study-level decomposition or replacement adjustment is available here. Consequently, overlap with an added smoke all-cause mortality component has not been ruled out.

### Wildfire CO2

Direct wildfire-smoke mortality and the downstream warming damages caused by wildfire CO2 are distinct endpoints. There is no direct endpoint duplicate. This assessment does not read from, write to, or operationally depend on wildfire-CO2 project working files.

## What opens the gate

1. Obtain or regenerate the source's annual country-by-draw marginal smoke mortality paths under a fully specified 2025 pulse.
2. Pin the exact model/code version, scenario inputs, horizon indexing, random seeds, pulse magnitude, and gas convention.
3. Reproduce the published scalar independently.
4. Harmonize wildfire and nonwildfire PM2.5 under a coherent joint mortality-attribution design.
5. Replace or adjust GIVE temperature mortality so air-pollution-mediated deaths are counted once.
6. Run all sectors jointly with matched draws and common endogenous discount factors.

Until all gates pass, downstream software must retain both additivity flags as `false`.

## Reproduction

With the authorized local draft present:

```bash
python3 scripts/build_wildfire_smoke_integration_contract.py \
  --source-pdf "/Users/jbb/Downloads/Fire_SC_CO2_draft (1).pdf"
python3 scripts/validate_wildfire_smoke_integration_contract.py \
  --source-pdf "/Users/jbb/Downloads/Fire_SC_CO2_draft (1).pdf"
python3 -m unittest discover -s test -v
```

The validator can also check the committed receipts and outputs without the confidential PDF; supplying `--source-pdf` adds direct hash and byte-count checks.
