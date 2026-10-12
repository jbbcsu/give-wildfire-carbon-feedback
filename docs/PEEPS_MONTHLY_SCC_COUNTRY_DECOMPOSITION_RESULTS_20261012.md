# Country and region decomposition of the PEEPS monthly diagnostic

## Result

The small fixed-adaptation global joint diagnostic of `$0.004269/tCO2` masks
large offsetting country components. At the smallest pulse and 2% discount
schedule, positive components (damages) sum to `$0.011572/tCO2`, while negative
components (benefits) sum to `-$0.007304/tCO2`. Fifty-nine of 107 countries
have positive joint components and 48 have negative components.

| Direction | Country | Joint monthly pattern | Quantity reference | Timing increment |
|---|---|---:|---:|---:|
| Damage | United States | +0.007231 | +0.006138 | +0.001093 |
| Damage | Mexico | +0.001295 | +0.001056 | +0.000239 |
| Damage | Romania | +0.000820 | +0.000710 | +0.000110 |
| Benefit | China | -0.002829 | -0.002876 | +0.000048 |
| Benefit | Brazil | -0.001348 | -0.001391 | +0.000042 |
| Benefit | India | -0.000832 | -0.000668 | -0.000163 |

Values are 2020 USD per tCO2 and are national-market accounting components.
The United States alone has a larger positive component than the global net;
China, Brazil, India, and other negative components offset most of it. Timing
also differs in sign: it adds damages in the United States and Mexico, but
adds benefits in South Africa and India under this model.

At the FUND-region level, the largest positive components are USA
`+$0.007231`, Eastern Europe `+$0.001853`, and Central America
`+$0.001380/tCO2`. The largest negative components are China
`-$0.002829`, Latin America `-$0.001462`, Sub-Saharan Africa
`-$0.001388`, and South Asia `-$0.000929/tCO2`.

## Validation and boundary

Country components reconstruct every global channel/pulse/adaptation/discount
result with maximum absolute error `1.04e-16` USD/tCO2. The country-level joint
= quantity + timing identity passes with maximum error `1.11e-17`. The bounded
successful job peaked at 295.1 MB, below the 512 MiB ceiling. Antigua and
Barbuda is absent from the archived GIVE/FUND crosswalk and is retained as
`UNMAPPED`; no regional assignment was guessed.

This is still one ESM/scenario, maize only, and monthly mean precipitation.
Country values are accounting contributions under separate national maize
markets, not causal local effects or total country damages. Daily drought,
extremes, other crops, trade, and paired GIVE agriculture replacement remain
outside the result.

## Reproducibility

- `scripts/decompose_peeps_monthly_scc_by_country.py`
- `data/provenance/peeps_monthly_scc_country_decomposition_20261012.json`
- Country table (gitignored):
  `data/interim/peeps_monthly_scc_country_decomposition_20261012.csv`
- Region table (gitignored):
  `data/interim/peeps_monthly_scc_region_decomposition_20261012.csv`
