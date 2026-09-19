# Structural agricultural-welfare benchmark protocol

Status: frozen before numerical execution. This is a research sensitivity, not
an empirical damage function, an agriculture replacement, or an SCC result.

## Question

What signed welfare change follows if the previously audited, joint
temperature-plus-precipitation maize production changes from the published
EPIC-TAMU and CARAIB structural benchmarks are passed through the independent
fully anticipated constant-elasticity market model under the project's
recommended default assumptions?

The calculation is deliberately limited to the 1981--2010 versus 2031--2060
period-mean crop-model contrasts already on disk. It does not monetize the
order-averaged precipitation contribution, because that contribution is not a
standalone productivity multiplier. It does not create annual paths, trend or
upper adaptation cases, matched emissions-pulse effects, or SCC values.

## Frozen inputs

- physical response: `data/interim/epic_caraib_geography_20260908/result.json`;
- baseline value proxy: `data/interim/welfare_baseline_ledger_20260914_v2/result.json`;
- price conversion: `config/price_basis_registry.toml`;
- market equations: `src/constant_elasticity_market.py`;
- response models: CARAIB and EPIC-TAMU, retained separately;
- climate cases: GFDL-ESM4 and IPSL-CM6A-LR under SSP1-2.6 and SSP5-8.5;
- calendars: both registered calendar conventions, retained separately;
- adaptation: fixed management only;
- geography: separate country maize markets;
- elasticity pairs: supply/demand magnitudes 0.08/0.02, 0.10/0.04 and
  0.50/0.06, with 0.10/0.04 labeled central;
- yield-to-supply mappings: horizontal-output and fixed-input-cost, both
  reported as modeling sensitivities; and
- value basis: covered common-support maize value, converted once with the
  registered central scalar to thousand USD2005.

## Aggregation

For each country and climate/model/calendar case, join rainfed and irrigated
joint production multipliers to their common-support baseline-value proxies.
Within a country, aggregate regimes before market equilibrium as

`s = log(sum_r w_r exp(s_r))`,

where `w_r` is the fixed covered-value share and `s_r` is either `log(A_r)` or
`(1+e) log(A_r)`. Evaluate the paired surplus formula at baseline supply shift
zero and increment `s`. Sum signed country results without loss truncation.

Countries without complete baseline values stay in an explicit unvalued ledger.
Zero common-support rows are not assigned effects. No subtotal is rescaled to
100 percent coverage.

## Failure and reporting rules

If any joint country/regime multiplier is nonpositive, retain its identity and
covered value, do not take its logarithm, clip it, drop it silently, or impute a
replacement. The case-level full-covered-market result is unauthorized. A
separately labeled valid-subset arithmetic diagnostic may be saved, but cannot
be interpreted as that case's welfare estimate.

Every output must report valued, missing-value, invalid-response and total
common-support value. CARAIB and EPIC-TAMU are structural alternatives rather
than an ensemble. Benefits remain negative damages. Results are not extrapolated
beyond maize or the supported footprint.

An independent validator will rehash inputs, rebuild all joins and market
arithmetic without importing the builder's market functions, and test value
partitions, signs, mappings and scenario counts. `give_export_authorized`,
`empirical_damage_authorized` and `scc_authorized` must remain false.

### Post-execution reporting amendment

The first execution exposed a scientifically important but arithmetically
permitted feature: an extremely small positive country multiplier can dominate
the sum under separate, highly inelastic national markets. The first result and
receipt are retained. A v2 output adds, without changing any welfare arithmetic,
the minimum positive market supply multiplier, largest absolute country result,
and its share of summed absolute country changes. No threshold, trimming, cap,
or market substitution is introduced after seeing the result. Mechanical log
admissibility is now labeled separately from substantive interpretation, which
remains unauthorized for every case.

## Resource limits

Run one worker at a time under the existing sampled 512 MiB process-group RSS,
64 MiB owned-output and 130 GiB free-disk safeguards. The builder and validator
read only the small resident JSON/configuration inputs and write small ignored
receipts.
