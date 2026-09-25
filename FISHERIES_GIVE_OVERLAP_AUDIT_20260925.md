# Fisheries benchmark overlap with core GIVE

## Decision

The published $22.09755/tCO2 fisheries benchmark is **not eligible for direct
addition to GIVE**. It remains an external scale benchmark, not a local
fisheries SCC estimate. Both its $0.05704 market component and $22.04051
nutrition/non-market component require separate resolution before either can
enter GIVE.

## Code-backed overlap screen

The pinned core GIVE mortality component is enabled by default. It multiplies a
country temperature coefficient by global temperature, applies that change to
the country's baseline mortality rate, converts the resulting excess deaths to
persons, and values them with VSL. The inspected component contains no
cause-specific exclusion for fisheries nutrition. The damage aggregator also
includes agriculture by default and sums mortality and agriculture into total
damage.

The audited Blue-SCC nutrition pathway instead links projected seafood nutrient
availability to selected cause-specific relative risks, baseline mortality,
seafood dependence, substitution, and VSL. Because both pathways value
mortality and the retained GIVE response lacks a fisheries-nutrition exclusion,
additivity cannot be assumed. This is a **potential overlap requiring causal-
pathway and cause-of-death reconciliation**, not proof that every death is
double counted.

The published market pathway is also not yet additive. It uses country profit
projections with regional direct, indirect, and induced output multipliers,
rather than an explicit consumer-plus-producer-surplus measure. Indirect and
induced output effects must be separated and tested against agriculture,
energy, and any macroeconomic damages. Seafood substitution and undernutrition
must likewise be reconciled with terrestrial food-price welfare.

## Required implementation order

1. Keep market and nutrition outputs separate; never install the published
   total as one undifferentiated damage component.
2. For nutrition, map causes and baseline deaths against Cromar's retained
   mortality response and harmonize VSL/income conventions. Report the pathway
   separately until its deaths are demonstrably incremental.
3. For market welfare, remove or isolate multiplier effects and estimate direct
   consumer and producer surplus under explicit management, trade, and
   adaptation assumptions.
4. Resolve terrestrial-food substitution jointly with the agriculture
   replacement or exclude that welfare channel.
5. Only then pair baseline and marginal-pulse paths and run GIVE.

The executable audit is
`scripts/audit_fisheries_give_overlap.py`; its machine-readable record is
`data/provenance/fisheries_give_overlap_audit_20260925.json`. It binds the
aggregate Blue-SCC audit and exact core GIVE component hashes while copying no
restricted external data.

