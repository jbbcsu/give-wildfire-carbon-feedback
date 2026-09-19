# Four-corner structural welfare attribution protocol

Status: frozen before execution. This is a global-market, structural maize
sensitivity—not an empirical precipitation damage function or SCC result.

## Purpose

Estimate the precipitation-attributable share of the already resident
temperature-plus-precipitation crop-model benchmark without incorrectly
monetizing the order-averaged yield contribution as a standalone productivity
shock. The correct nonlinear attribution evaluates welfare at all four physical
climate corners and then applies a two-driver Shapley decomposition to welfare.

## Inputs and value allocation

- Four physical yield corners `y00`, `y10`, `y01`, `y11` come from each audited
  EPIC-TAMU/CARAIB global case ledger listed in
  `data/interim/epic_caraib_global_comparison_20260908/result.json`.
- `0/1` denote baseline/future temperature and precipitation respectively;
  the ledgers' existing arithmetic identifies `y01-y00` as precipitation at
  baseline temperature and `y11-y10` as precipitation at future temperature.
- Fixed common-support cell production and country assignments come from
  `data/interim/epic_caraib_geography_20260908/country_cell_production.parquet`.
- Country/regime common-support value proxies come from the September 14 v2
  welfare baseline ledger. Allocate each proxy across its common-support cells
  in proportion to the fixed external production weights. Countries without a
  complete value proxy stay unvalued; no rescaling is permitted.
- Convert once to USD2005 with the registered central price scalar.

## Market and attribution

Use the prespecified single global maize market, fixed management, all three
elasticity pairs and both yield-to-supply mappings. For every physical corner
and economic case, aggregate cell supply shifts before equilibrium:

`S_ab = sum_i w_i (y_ab_i/y00_i)^k`,

where `k=1` for horizontal output and `k=1+e` for the fixed-input-cost mapping.
Evaluate total-surplus benefit `B_ab` at `log(S_ab)` with `B_00=0`.

The welfare Shapley benefits are

- precipitation: `0.5[(B_01-B_00)+(B_11-B_10)]`;
- temperature: `0.5[(B_10-B_00)+(B_11-B_01)]`; and
- joint: `B_11-B_00`.

Report damage as the negative of benefit and require precipitation plus
temperature damage to close to joint damage. These are an order-symmetric
two-driver attribution; the interaction is shared equally rather than added a
second time.

## Physical validity and reporting gates

Do not clip cell yields. Report counts and fixed covered-value shares for every
nonpositive corner. A global aggregate corner is mechanically evaluable only if
its supply multiplier is finite and positive, but any nonpositive cell corner
keeps substantive structural-damage interpretation false. Retain CARAIB and
EPIC-TAMU separately. No model, elasticity, mapping, calendar or market is
selected by the size or sign of precipitation damages.

Outputs must include corner supply multipliers, corner welfare, precipitation/
temperature/joint damage, closure error, value and missing-production coverage,
negative-corner diagnostics, exact source hashes and false empirical/GIVE/SCC
flags. A separate validator will independently rebuild allocation, corners,
market equations and Shapley arithmetic without importing the builder.

Resource safeguards remain one worker, sampled 512 MiB RSS, 64 MiB owned output
and 130 GiB free disk. Raw/interim numerical outputs remain ignored.
