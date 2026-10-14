# FrEDI electricity T&D deterministic sentinel

The v4.1.1 electricity audit admits only the released combined `ElecTD` transmission/distribution sector. `ElecSD` was audited but excluded because it bundles required capacity expansion with the explicitly excluded heating/cooling-demand channel.

The hash-bound output contains 18 rows at a 1.5°C CONUS anomaly relative to 1995 and economic year 2020: 49 state/DC units aggregated separately for six GCM response surfaces and three adaptation variants. No model average was constructed.

Validation:

- exact 1°C/2°C support for all 1,764 T&D state/model/variant/bin keys;
- exact 2020 state growth-factor support;
- independent reaggregation maximum absolute difference `0.000000` 2015 USD/year;
- runner and final standalone validator each remained below 25 MiB peak RSS;
- output SHA-256 `b9fc0aa94c81f318be513125bab3d9cf611e889f2b2832e348763981a2920c02`.

Generation/capacity, building demand, transmission-only, distribution-only, matched-pulse, global extrapolation, and SCC claims remain closed. The numbers are deterministic implementation sentinels, not policy estimates.
