# Phased plan

1. **Replication audit:** obtain exact species-loss coefficient units/draws,
   non-climate loss rate, 16-region valuation coefficients, country mapping,
   currency year, and income definition.
2. **Kernel validation:** test species-stock evolution, no-climate baseline,
   unit-income-elasticity WTP, and country aggregation independently of GIVE.
3. **GIVE integration:** implement a country-year component using FaIR global
   temperature, RFF-SP population/income, and FUND-region valuation parameters.
4. **Uncertainty:** preserve joint socioeconomic/climate draws and sample the
   empirical species-loss and valuation uncertainties.
5. **Accounting tests:** the standalone pair preflight now requires matched
   baseline/pulse draw-country-year keys and fixed inputs, recomputes deficits
   and country damages, and enforces zero-pulse and pre-divergence identity.
   Zero preference and exactly-once GIVE consumption/SCC integration remain
   open.
6. **Sensitivity:** original versus updated species-loss function, alternative
   income elasticities, alternative valuation transfer, temperature path, and
   exclusion of non-climate background loss from marginal attribution.
7. **Manuscript:** present this as a replication/extension unless all empirical
   inputs and uncertainty draws are independently reproduced.
