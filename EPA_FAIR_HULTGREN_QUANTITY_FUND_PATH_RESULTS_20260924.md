# Currency-aligned GIVE-region marginal damage paths

## Result and claim boundary

The annual maize precipitation-quantity marginal damage differences have been
converted from the source 2014--2016 dollar basis to billion 2005 USD and
allocated to GIVE's 16 FUND regions. The output contains 2,805,504 rows:
175,344 complete global model/year/pulse/adaptation/tail keys times 16 ordered
regions. It covers 26 EPA climate models and 106 countries represented in the
annual response paths. Every FUND region is represented and no represented
country is unmapped.

This is a currency-aligned regional **pulse-minus-baseline marginal damage
difference**, not an agriculture replacement or an SCC. A paired GIVE
replacement requires defensible baseline and pulse agriculture damage
*levels*. Setting the new baseline agriculture damage to zero would alter
baseline consumption and Ramsey discounting and is therefore not a neutral
implementation choice.

## Currency and regional mapping

The registered central conversion is
`P2005 / mean(P2014,P2015,P2016) = 0.8357992263240843`, using the U.S. GDP
implicit price deflator. This GDP-wide rebase is an explicitly disclosed
approximation for FAOSTAT farm-gate production value; the price concepts are
not identical. Country paths retain their source weights and are summed by
the repository's pinned country-to-FUND mapping. No country or region is
renormalized.

## Independent validation

The independent validator streamed every row under the 512 MiB ceiling. It
verified the hashes of all source and output artifacts, the complete ordered
16-region product for every global key, exact zero-pulse and pre-2021
identities, and the currency conversion. Regional sums reproduce each global
source path with maximum absolute disagreement `7.11e-14` source dollars;
the maximum recorded currency-conversion error is zero. The build and
validator peaked at approximately 243 MB and 265 MB of sampled process-group
RSS, respectively.

## Remaining gate to an SCC

Discounting these differences outside GIVE can provide a transparent
diagnostic, but it cannot reproduce the effect that a replacement damage
level has on regional consumption and therefore on endogenous Ramsey discount
factors. The next scientifically complete step is to specify and validate
paired baseline and pulse agriculture damage levels, replace Moore agriculture
exactly once, and independently reproduce GIVE discounting and pulse
normalization. Until then, no value from this output is labeled a GIVE SCC.

## Reproducible artifacts

- Builder: `scripts/build_epa_fair_hultgren_quantity_fund_paths.py`
- Independent validator:
  `scripts/validate_epa_fair_hultgren_quantity_fund_paths.py`
- Build receipt:
  `data/provenance/epa_fair_hultgren_quantity_fund_paths_20260924.json`
- Validation receipt:
  `data/provenance/epa_fair_hultgren_quantity_fund_paths_validation_20260924.json`
- Ignored derived data:
  `data/interim/epa_fair_hultgren_quantity_fund_paths_20260924.parquet`
