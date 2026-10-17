# Method

1. Run the standard RFF-socioeconomics GIVE baseline and a matched 0.0001 GtC
   pulse in 2025. Convert GIVE global mean temperature to the FrEDI CONUS
   anomaly using FrEDI's 1.421 multiplier relative to 1995.
2. For each of 48 states and DC, append FrEDI's zero-damage baseline at zero
   warming to its published 1--5 C `GCM Ensemble` knots. Evaluate the official
   piecewise-linear response for the baseline and pulse temperature in each year.
3. Sum states, difference pulse minus baseline, convert FrEDI's 2015 dollars to
   2020 dollars with annual-average BEA GDPDEF (105.362 / 97.315), and apply the
   matched GIVE Ramsey discount factor.
4. Divide discounted marginal damages by 366,666.6667 metric tonnes CO2.

The full-horizon estimate follows FrEDI's linear endpoint extrapolation above
5 C after 2246. Two pre-specified bounded summaries avoid that extrapolation:
2025--2092 stays within 0--3 C, and 2025--2246 stays within all released 0--5 C
knots. The sole released response is a GCM ensemble; no uncertainty draws or
confidence interval are fabricated. State values are decomposition, not draws.

The endpoint is a **partial SCC**, not an all-sector SCC and not a global estimate.
It can be summed into GIVE only after checking that riverine property losses are
absent from every other enabled module. In particular, coastal CIAM, FrEDI
Roads/Rail, and any future urban-drainage module remain separate.

