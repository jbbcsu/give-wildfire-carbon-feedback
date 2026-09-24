# EPA/FAIR--Hultgren maize quantity damage paths

## Status

This milestone connects the published EPA annual country-precipitation
patterns to the matched GIVE/FAIR marginal temperature paths, the published
Hultgren maize precipitation response, and the registered central national-
market case. It produces annual source-price-basis monetary damage paths for
2020--2300. It is **not yet a GIVE SCC**: currency alignment, the remaining
market sensitivities, paired MooreAg replacement, discounting, and SCC
normalization remain closed gates.

## Implemented chain

For each of 26 EPA climate models, country, crop cell, FAIR year, and pulse,
the annual rainfall change is the EPA slope times pulse-minus-baseline FAIR
temperature. The change is divided by the independently validated cell annual
rainfall baseline and applied proportionally to all baseline crop-season
months. Linear Hultgren precipitation terms scale once and squared terms scale
twice, preserving the exact second-order response. Rainfed and irrigated crop-
calendar bases are mixed with fixed MIRCA hectares, while the published
irrigation-share interaction remains active. Country income is joined by the
maize-value weight's ISO3 rather than by a border cell's dominant geometry.

The source weights represent $97.272 billion of matched-support maize value.
After the preregistered calendar and non-imputed PWT-income requirements,
$95.706 billion (98.391%) remains, without renormalization. Model-specific EPA
slope availability leaves 97--106 countries and $95.570--$95.706 billion per
model.

The central structural market case uses separate fully anticipated national
maize markets, supply elasticity 0.10, demand-elasticity magnitude 0.04, and
the horizontal-output yield-to-supply mapping. Fixed, trend, and upper
loss-only adaptation paths are all evaluated. Trade, storage, other crops,
adaptation costs, and future maize-value growth remain excluded.

## Tail and pulse validation

The uncapped result is accompanied by the registered published-analogue tail
sensitivity. Across 162,847,160 unique country-cell/model/year derivatives at
the smallest pulse, exact linear-interpolated 1st/99th percentiles are
`-6.5537066e-5` and `8.4606583e-5` log-yield points per GtC. The same derivative
bounds are applied to every pulse size.

All zero-pulse and 2020 identities are exact, and the minimum proportional
rainfall scale is 0.99999716. Relative normalized disagreement between the two
smallest pulses is 0.0001329 for cell responses and 0.0001526 for global
damage, both below the 0.0002 ceiling fixed from the already validated
0.0001576 upstream EPA/FAIR discrepancy. An initial 0.0001 ceiling failed
closed and produced no result; it was replaced before the successful output
because a downstream gate cannot be tighter than its accepted climate input.

An independent validator re-ranked the entire derivative pool, recovered both
tail quantiles exactly from their adjacent order statistics, and reconstructed
five fixed model/year/pulse/adaptation/tail national-market cases using a
separate pandas aggregation. Maximum monetary disagreement was $0.0000084.

## Preliminary direction, with strict interpretation

For the smallest 0.000025 GtC pulse and fixed adaptation, annual model-year
damage changes average -$11.62 uncapped and -$11.65 with the tail rule in the
source 2014--2016 price basis; negative damage denotes a modeled benefit. The
26 climate-model mean paths span approximately -$19.52 to +$6.03 per year
uncapped, and 25 of 26 model means are negative. Trend and upper loss-only
adaptation make the mean more negative because they attenuate adverse cell
responses while leaving beneficial responses unchanged.

These signs are a result for the narrow **annual precipitation-quantity
channel** under fixed within-season shares and the stated market structure.
They are not evidence that total climate change benefits agriculture. The
calculation excludes warming, timing shifts, dry spells, rainfall extremes,
drought, other crops, endogenous irrigation, trade, and adaptation costs.
Because the pulse is deliberately very small, the dollar figures above are
annual path increments, not dollars per tonne of CO2 and not SCC values.

## Reproducible artifacts

- Quantity response panel builder and test:
  `scripts/build_hultgren_quantity_response_panel.py`,
  `scripts/test_build_hultgren_quantity_response_panel.py`
- Response-panel validator:
  `scripts/validate_hultgren_quantity_response_panel.py`
- Damage-path builder and test:
  `scripts/build_epa_fair_hultgren_quantity_damage_paths.py`,
  `scripts/test_build_epa_fair_hultgren_quantity_damage_paths.py`
- Damage-path validator:
  `scripts/validate_epa_fair_hultgren_quantity_damage_paths.py`
- Provenance receipts:
  `data/provenance/hultgren_quantity_response_panel_20260924.json`,
  `data/provenance/hultgren_quantity_response_panel_validation_20260924.json`,
  `data/provenance/epa_fair_hultgren_quantity_damage_paths_20260924.json`, and
  `data/provenance/epa_fair_hultgren_quantity_damage_paths_validation_20260924.json`
- Ignored derived data:
  `data/interim/hultgren_quantity_response_panel_20260924.parquet` and
  `data/interim/epa_fair_hultgren_quantity_damage_paths_20260924.parquet`

The successful damage build peaked at 312,852,480 bytes of sampled process-
group RSS after a failed higher-memory implementation was replaced by exact
16-year streaming. Validation peaked at 205,291,520 bytes.

## Remaining path to a provisional partial SCC

Next steps are to freeze the source-price-to-GIVE currency conversion, run the
registered elasticity and fixed-input-cost sensitivities, pass annual monetary
paths through paired GIVE agriculture replacement rather than stacking them on
MooreAg, reproduce GIVE discounting and pulse normalization independently,
and test SCC convergence across the two smallest pulses. The resulting number
must remain labeled a maize precipitation-quantity partial SCC benchmark.
