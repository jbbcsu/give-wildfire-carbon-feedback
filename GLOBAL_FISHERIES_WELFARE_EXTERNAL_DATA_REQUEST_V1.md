# Global fisheries welfare bridge: external data request v1

Date: 2026-09-29  
Contract: `global_fisheries_welfare_bridge_input_v1`  
Schema: `config/global_fisheries_welfare_bridge_input_contract_v1.schema.json`

## Purpose and limits

This request seeks the evidence needed to assess whether an existing global
fisheries model can support a direct-market welfare bridge for GIVE. It is a
request for source material and documentation, not permission to transfer
coefficients or calculate damages. Submission does not imply acceptance.

Please deliver one versioned bundle with immutable file names, checksums, a
data dictionary, and a contact for technical questions. Preserve original
missing, zero, suppressed, disputed, joint-area, and out-of-scope codes. Do
not impute missing countries, stocks, markets, or years, and do not
renormalize incomplete geographic coverage.

## Requested components and acceptance criteria

The component identifiers below exactly match the versioned input contract.
Every component must cite one or more versioned sources.

### 1. `license_and_reuse`

Questions:

- What license applies separately to each dataset, model-code release,
  dependency lock, geographic crosswalk, and derived output?
- Does it permit redistribution, validation, modification, and derivative
  scientific use? Are attribution, noncommercial, or share-alike conditions
  present?
- Do any third-party inputs carry different or more restrictive terms?

Acceptance criteria:

- An explicit license identifier and license text or official license URL for
  every source artifact.
- Redistribution and derivative-use permission recorded separately as true;
  `NOASSERTION`, repository visibility alone, or an article license applied by
  implication to code/data does not pass.
- Version, canonical URI/DOI, and SHA-256 checksum for every delivered file.

### 2. `raw_model_inputs`

Questions:

- Which raw stock, range, climate, price, cost, effort, management, and trade
  inputs generate the published results?
- What are the units, spatial and temporal support, missingness codes, and
  transformations for each variable?
- Are high seas, joint/disputed waters, mixed-species stocks, and omitted
  countries explicitly represented?

Acceptance criteria:

- Checksum-pinned raw inputs sufficient to reproduce every delivered response
  and welfare row.
- Stable stock/species, source-area, country, market, model, scenario, draw,
  and year identifiers with a machine-readable data dictionary.
- Global declared support and explicit missing-versus-zero semantics, with no
  silent imputation or renormalization.

### 3. `executable_model_and_dependency_lock`

Questions:

- Which executable code produces the biophysical response, incidence, prices,
  costs, consumer surplus, and producer surplus?
- Which software/runtime versions, random seeds, calibration draws, and
  management rules are required?
- Can the delivered workflow regenerate the supplied outputs from the raw
  inputs without undisclosed intermediate files?

Acceptance criteria:

- Versioned executable source plus an exact dependency/environment lock.
- One documented entry point and deterministic or seed-controlled
  reproduction instructions.
- No user-specific paths, unavailable intermediate artifacts, or undocumented
  manual transformations on the critical path.

### 4. `incidence_and_geographic_keys`

Questions:

- How are stock/source-area responses assigned to harvest rights, fleets,
  landing countries, traded products, and consumer markets?
- How are re-exports, processing, distant-water fishing, high seas, and
  joint/disputed areas handled?
- Which country identifier standard and boundary vintage are used?

Acceptance criteria:

- Explicit stock/source-area-to-market records with producer and consumer
  ISO3 identifiers.
- Harvest, landing, and consumption fractions each conserve to one within the
  declared support for every draw-year-stock-area key.
- No substitution of EEZ location, vessel flag, or landing country for
  producer or consumer incidence without documented evidence.

### 5. `consumer_and_producer_surplus`

Questions:

- What demand system, baseline quantities/prices, elasticities, and trade
  closure identify consumer surplus?
- What supply/cost system, effort response, property-rights assumption, and
  rent treatment identify producer surplus?
- Are results direct surplus measures, or are they revenue, profit, output,
  value added, or multiplier effects?

Acceptance criteria:

- Consumer surplus and producer surplus supplied separately for identical
  draw-year-stock-area-market support under both baseline and pulse.
- Welfare unit fixed to `USD_2020`, with currency conversion and price-year
  documentation.
- Direct surplus semantics are explicit; gross revenue, catch value, output
  multipliers, and unlabeled profit do not substitute for either measure.

### 6. `matched_marginal_pulse`

Questions:

- Can the model provide a baseline and a one-metric-ton CO2 pulse run using
  the same realization, climate/ecosystem models, management, socioeconomic
  path, welfare draw, and support mask?
- When is the pulse emitted, and how is it propagated through climate and
  ocean conditions?
- Are numerical noise, ensemble pairing, and stochastic seeds documented?

Acceptance criteria:

- Exact `baseline`/`pulse` pairs for every declared key, with gas `CO2`, mass
  `1.0`, unit `tCO2`, and counterfactual `same_realization_baseline`.
- Identical identifiers, units, years, and geographic/market masks across each
  pair.
- SSP/RCP, policy, management, or endpoint scenario differences are not
  accepted as substitutes for the marginal pulse.

### 7. `overlap_accounting_boundary`

Questions:

- Does the model include aquaculture, terrestrial food-market feedback,
  nutrition or mortality, coral/reef services, biodiversity nonuse value,
  coastal impacts, or indirect/induced output?
- What trade closure and market boundary determine whose welfare is counted?
- How are transfers, subsidies, taxes, rents, and multiplier effects treated?

Acceptance criteria:

- A versioned accounting-boundary identifier, explicit trade-closure
  identifier, and completed overlap review.
- Capture-fisheries direct market surplus is separable from aquaculture,
  terrestrial food welfare, nutrition/mortality, coral/reef services,
  biodiversity nonuse value, CIAM coastal impacts, and indirect/induced
  output.
- Gross revenue is never labeled or used as welfare.

## Delivery inventory

Please accompany the bundle with a completed copy of
`templates/global_fisheries_welfare_bridge_candidate_inventory_v1.json`.
Replace placeholders only with documented evidence; leave unavailable items
blank or false. The template is deliberately non-synthetic and cannot pass
the current synthetic-only validator. A future production validator would
require separate scientific review and explicit authorization.

Acceptance of a delivery requires all seven component gates to pass together.
Partial material remains useful for feasibility review but does not authorize
coefficient transfer, fitting, damage estimation, aggregation, discounting,
or an SCC.
