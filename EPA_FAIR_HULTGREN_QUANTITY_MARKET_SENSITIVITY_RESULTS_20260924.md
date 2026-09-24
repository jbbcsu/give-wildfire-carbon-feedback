# Quantity-channel national-market sensitivities

## Result

The annual EPA/FAIR--Hultgren maize quantity bridge has now been evaluated for
all three registered supply/demand elasticity pairs and both registered
yield-to-supply mappings. The streamed output contains 1,052,064 rows: the
175,344 central path keys times six market specifications. It retains all 26
climate models, four pulse sizes, three adaptation scenarios, and both the
uncapped and frozen-tail cases.

For the smallest positive pulse and fixed adaptation, the uncapped mean annual
damage change across model-years ranges from -$12.79 to -$8.52 in the source
price basis; negative damage is a modeled benefit. The central 0.10/0.04
elasticity pair gives -$11.62 under horizontal-output mapping and -$12.79 under
fixed-input-cost mapping. The published-analogue tail rule gives a very similar
range, -$12.81 to -$8.54. Trend and upper loss-only adaptation make the means
more negative because they attenuate modeled losses without attenuating
benefits.

The near equality of fixed-input-cost results across elasticity pairs is a
first-order consequence of this convention: the productivity-to-supply
multiplier `(1 + supply elasticity)` approximately offsets the surplus
denominator `(1 + supply elasticity)` for these very small shocks. It should
not be read as general insensitivity of agricultural welfare to elasticities.

These dollar values are annual increments caused by a deliberately tiny pulse.
They are not divided by tonnes of CO2, are not discounted, and are not SCC
estimates. They cover only annual rainfall quantity for maize with fixed
within-season rainfall shares.

## Validation and resource behavior

The central horizontal-output path reproduces the prior independently audited
central artifact exactly. Zero-pulse and pre-2021 identities are exact for all
six specifications. Maximum relative disagreement between the two smallest
normalized pulses is `1.5330e-4`, below the registered `2e-4` ceiling.

An independent validator streamed all 1,052,064 rows, verified the complete
ordered key product, exact source-to-2005-USD conversion, central-path identity,
and shrinking-pulse convergence. The first implementation was stopped by the
512 MiB monitor before it produced output; replacing an in-memory Python row
list with chunked Parquet writing reduced peak sampled process-group RSS to
274 MB. Independent validation peaked at 261 MB.

## Claim boundary and next gate

These results close the registered elasticity and supply-mapping sensitivity
gate for separate fully anticipated national maize markets. Trade, storage,
other crops, future crop-value growth, and adaptation costs remain excluded.
Most importantly, the output contains marginal pulse-minus-baseline differences
rather than paired baseline and pulse agriculture damage levels. It therefore
does not authorize a GIVE replacement or SCC claim.

## Reproducible artifacts

- Builder and unit test:
  `scripts/build_epa_fair_hultgren_quantity_market_sensitivities.py`,
  `scripts/test_build_epa_fair_hultgren_quantity_market_sensitivities.py`
- Independent validator:
  `scripts/validate_epa_fair_hultgren_quantity_market_sensitivities.py`
- Receipts:
  `data/provenance/epa_fair_hultgren_quantity_market_sensitivities_20260924.json`
  and
  `data/provenance/epa_fair_hultgren_quantity_market_sensitivities_validation_20260924.json`
- Ignored derived output:
  `data/interim/epa_fair_hultgren_quantity_market_sensitivities_20260924.parquet`
