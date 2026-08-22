# Phased plan: ocean-fisheries SCC extension

## Gate 0 — scope and overlap audit

Map existing GIVE agriculture, energy, mortality, and CIAM outputs. Define a
single welfare target and exclusions for aquaculture, fishmeal inputs,
reef-mediated coastal protection, tourism, and food-price feedback. A module
cannot proceed without a written double-counting resolution.

RFF's 2024 ocean report identifies fisheries and other ocean systems as absent
from current GIVE damages and recommends integrated ecological--economic
modeling rather than an unsupported reduced-form plug-in. The implementation
therefore follows the auditable [`MODEL_CONTRACT.md`](MODEL_CONTRACT.md), with
numeric calibration gated on licensed biophysical and welfare inputs.

## Gate 1 — literature-first feasibility assessment

Systematically assess global and regional fisheries studies for: climate
drivers (warming, acidification, oxygen, primary productivity, extremes);
spatial/species coverage; counterfactual identification; treatment of range
shifts and management; economic measure (catch, revenue, profit, surplus,
nutrition); scenario compatibility; uncertainty; and data licenses. Compare
reduced-form and integrated ecosystem/economic approaches.

## Gate 2 — data/provenance

Create manifests before downloading: fisheries catch/effort/value data;
species distribution/stock productivity; ocean climate and biogeochemistry;
management/harvest controls; prices/substitution; population/income. Preserve
source queries, licenses, spatial keys, quality flags, and checksums. Never
impute missing catch as zero.

## Gate 3 — primary model and alternatives

Primary candidate: an explicitly stated regional/species hierarchical response
or integrated biophysical-economic model, evaluated under matched ocean
climate baseline/pulse paths. Alternatives: published FishMIP-style ensemble
outputs with a transparent welfare translation; reduced-form historical
catch/landings models only where identification is credible. Model migration,
harvest management, and substitution explicitly rather than attributing all
catch trends to climate.

## Gate 4 — welfare translation and GIVE interface

Translate changes in catch/availability into producer and consumer welfare,
not gross revenue. Aggregate to countries/FUND regions with an explicit trade
or incidence assumption. Implement a replacement/addition decision only after
the overlap audit. Pair every climate/member, ecology, economy, and welfare
draw across baseline and CO2-pulse paths.

## Gate 5 — validation, uncertainty, publication

Require withheld years/regions/species, historical marine-heatwave tests,
conservation/stock assessment comparisons where valid, sensitivity to ocean
drivers and management/adaptation, and variance decomposition. Publish as a
separate paper with data limitations and nonmarket coral-reef services clearly
outside the initial fisheries estimate.
