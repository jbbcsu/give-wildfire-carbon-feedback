# Fisheries-to-GIVE model contract

This contract permits data and model work without pre-committing to an
unsupported global coefficient. The module is isolated from terrestrial
agriculture, CIAM coastal damages, and biodiversity nonuse value.

## Estimand

For each Monte Carlo draw and year, estimate the change in fisheries welfare
caused by the marginal-emissions pulse relative to the same baseline path:

`delta_welfare = (consumer surplus + producer surplus)_pulse
                 - (consumer surplus + producer surplus)_baseline`.

Gross landings revenue, catch-potential change, and biomass change are
intermediate outcomes, not damages. Every pulse comparison must retain matched
climate model, ecosystem model, management/adaptation scenario, demand/supply
draw, trade assumption, discounting draw, and socioeconomic trajectory.

## Required input table

One row per `draw_id, scenario, year, country_id` (or an explicitly documented
EEZ-to-country allocation), containing:

- baseline and pulse harvest/availability by modeled stock or commodity;
- prices or identified demand/supply parameters sufficient for surplus;
- management/effort and range-shift assumptions;
- population and income path used by the same GIVE draw;
- ensemble identifiers for ocean climate and ecosystem models;
- aquaculture and trade treatment; and
- coverage flags that distinguish missing, unmodeled, suppressed, and zero.

## Required output table

One row per `draw_id, year, country_id`:

- `delta_consumer_surplus_usd`;
- `delta_producer_surplus_usd`;
- `delta_fisheries_welfare_usd` (their sum);
- optional nutrition quantity reported separately, never monetized implicitly;
- input/model identifiers and coverage flags; and
- an additive-eligibility flag set only after overlap checks pass.

The GIVE adapter aggregates eligible country-year welfare changes to its
region order and discounts pulse-minus-baseline damages using the same SCC
conventions as other sectors.

### Country-to-region aggregation preflight

`scripts/aggregate_welfare_to_regions.py` implements the aggregation portion
without discounting. Its crosswalk has one row per declared `country_id` and
requires `give_region_id`; duplicate or unmapped country identifiers are
errors. For every observed draw-year, each region is eligible only if every
country declared for that region is present, has `coverage_status=complete`,
and has already passed the upstream overlap gate
(`additive_eligible=true`). Otherwise, the regional surplus fields remain
blank and explicit reason codes report missing, suppressed, unmodeled, or
ineligible country rows. Complete regions conserve consumer, producer, and
total welfare independently.

The crosswalk is an explicit aggregation universe, not proof of global
coverage. A production crosswalk still requires a provenance record, version,
and reconciliation to the GIVE country/region definitions. The adapter does
not clear the ecological, welfare-identification, global-coverage, overlap, or
SCC gates.

## Locked overlap exclusions

- No coral tourism, reef nonuse value, or reef-mediated coastal protection.
- No biodiversity nonuse value; that is a separate module.
- No terrestrial food-price loss already represented by the agriculture
  replacement, unless a joint food-market model explicitly resolves it.
- No CIAM coastal property or mortality loss.
- No valuation of gross catch or revenue as welfare.

## Implementation gate

Executable welfare calibration begins only after one of two evidence paths is
selected and documented: (A) licensed FishMIP-style biophysical ensemble plus
an identified welfare model, or (B) an existing integrated global fisheries
model whose surplus outputs and pulse/scenario assumptions can be audited.
Until then, numeric parameters remain unset rather than filled with judgmental
defaults.

The schema-only validator in `scripts/validate_welfare_interface.py` checks
matched baseline/pulse identifiers, missing-versus-zero semantics, surplus
arithmetic, duplicate keys, and additive eligibility. Its synthetic test is
`python3 test/test_welfare_interface.py`. The aggregation preflight's synthetic
coverage, identity, and conservation checks are in
`python3 test/test_region_aggregation.py`; passing either test does not clear
the biophysical, welfare-identification, coverage, or SCC gates.
