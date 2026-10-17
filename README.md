# Amazon dieback carbon feedback for GIVE

This isolated project audits a terrestrial-carbon feedback for GIVE: warming may trigger Amazon forest dieback, releasing carbon that changes the climate trajectory and downstream damages. It excludes market forestry, wildfire emissions, biodiversity, hydrology, and ecosystem-service valuation.

## Decision

**Readiness benchmark only; no GIVE SCC and no scalar adjustment.** GIVE's FaIR 1.6.2 carbon cycle contains temperature-dependent land uptake but no explicit Amazon forest stock or stochastic dieback state. The open, peer-reviewed META 2021 model supplies an executable annual GMST-trigger hazard, a finite 50 GtC carbon release, and a one-year-lagged CO2-cycle connection. Its published model-specific Amazon contribution was only a 0.1% SCC increase, but that is evidence about META—not a transferable GIVE scalar.

Production coupling is blocked until the overlap with FaIR's generic land-sink feedback and exogenous land-use emissions is resolved; the hazard is reassessed against current Amazon science; baseline and marginal runs share stochastic draws; and the release schedule is made exactly stock conserving. The released META implementation can overshoot its nominal stock when the continuously sampled release duration is not an integer. The combined EPA permafrost-plus-Amazon uplift is explicitly non-separable and is not used here.

## Reproduce the audit

```bash
python3 scripts/audit_readiness.py
python3 scripts/validate_contract.py
python3 -m unittest discover -s tests
```

The scripts write machine-readable audit receipts and deliberately do not run GIVE or create an SCC estimate.

