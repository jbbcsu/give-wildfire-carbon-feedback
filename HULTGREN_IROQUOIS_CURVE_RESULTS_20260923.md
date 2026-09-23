# Published maize local-response checkpoint

## Result

The isolated Python evaluator reproduces the pinned Hultgren et al. maize
temperature-response calculation for the paper's Iroquois County, USA example.
The source subset contains 59 observations and has the local moderator values
used by the authors' plotting code: long-run growing-season Tmax 25.527721 C,
the long-run precipitation moderator 88.434906 in the source data's units, log
GDP per capita 10.173247, and irrigated share 0.007540.

Starting from the authors' Stata `.ster` estimate, an independent Stata export
and the Python evaluator agree over every integer temperature from 1 through
40 C. The maximum absolute differences are `1.32e-9` log-yield units for the
response and `1.84e-10` for the coefficient-only standard error. The underlying
degree-day basis also matches exactly: 8--31 C growing degree days and killing
degree days above 31 C.

Selected one-day responses relative to an 8 C day are:

| Daily Tmax | Delta log yield | Coefficient-only SE |
|---:|---:|---:|
| 20 C | 0.001363 | 0.001097 |
| 31 C | 0.002613 | 0.002103 |
| 35 C | -0.031567 | 0.005219 |
| 40 C | -0.074292 | 0.012131 |

These values reproduce a local published-response checkpoint. They are not a
future temperature projection, a precipitation effect, an agricultural damage
estimate, or an SCC increment.

## Reproduction and provenance

Run `scripts/run_hultgren_maize_iroquois_curve.sh`. It verifies the historical
data hash, runs the source-equivalent response calculation in Stata, and then
compares the output with `src/hultgren_maize_response.py`. The raw Stata curve
remains in ignored interim storage. The versioned validation receipt is
`data/provenance/hultgren_maize_iroquois_curve_validation_20260923.json`.

The computation is bound to the pinned replication source at commit
`3ccdffcd4e4ff6e55566ce76e2aac130ee86349a`, the recovered historical data blob,
the published `.ster` estimate, and the previously exported 49-coefficient and
49-by-49 covariance files. No source data are redistributed.

## Remaining gate

This closes the local published-response checkpoint in the future-projection
contract. The next unresolved gate is still empirical: reproduce the published
monthly precipitation and daily temperature bases from primitive historical
weather on matched local calendars, then compare administrative-unit-first and
grid-cell-first aggregation before evaluating future weather.
