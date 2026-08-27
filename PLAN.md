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

The 2025/2026 Blue-SCC paper and repository now pass a frozen method/source-
data audit and become the required literature benchmark. Its source data imply
$22.09755/tCO2 for fisheries under the paper's baseline settings, almost all
from nutrition/non-market use rather than the market-profit channel. This is
an external published result, not this project's estimate. Gate 1 therefore
advances from "no plug-in exists" to "published benchmark identified, exact
replication and transferability review required."

## Gate 2 — data/provenance

Create manifests before downloading: fisheries catch/effort/value data;
species distribution/stock productivity; ocean climate and biogeochemistry;
management/harvest controls; prices/substitution; population/income. Preserve
source queries, licenses, spatial keys, quality flags, and checksums. Never
impute missing catch as zero.

The first source-discovery subgate is now reproducible. A 2026-08-25 ISIMIP3b
catalogue audit found 20 public, unrestricted, CC0 global monthly `tc` datasets:
two ecosystem models (BOATS and EcoOcean) by two climate forcings (GFDL-ESM4
and IPSL-CM6A-LR), with five historical/future experiment records per pairing.
Twelve files spanning historical, SSP1-2.6, and SSP5-8.5 have since been
acquired and content-validated for the scenario matrix. The eight
preindustrial-control files remain unacquired. This does not clear the
matched-pulse, welfare, or production gates.

The all-file acquisition plan is now version-pinned and executable against a
fresh catalogue response. Its outcome-blind content smoke is limited to the
four BOATS/EcoOcean historical and SSP1-2.6 files under GFDL-ESM4 (513,826,771
catalogue bytes). After that smoke passed, the bounded scenario matrix added
the equivalent IPSL-CM6A-LR cells and both SSP5-8.5 futures. All 12 scenario
files passed complete-file checksum, schema, monthly chronology,
historical/future join, grid, unit, and missing-versus-zero checks. The eight
control files remain deferred. See `FISHMIP_CONTENT_PLAN.md`.

## Gate 3 — primary model and alternatives

Primary candidate: an explicitly stated regional/species hierarchical response
or integrated biophysical-economic model, evaluated under matched ocean
climate baseline/pulse paths. Alternatives: published FishMIP-style ensemble
outputs with a transparent welfare translation; reduced-form historical
catch/landings models only where identification is credible. Model migration,
harvest management, and substitution explicitly rather than attributing all
catch trends to climate.

The two-forcing/two-scenario scenario matrix now passes on 41,029 GFDL and
40,399 IPSL common-support cells. All eight modelled 2081--2090 mean `tc`
density changes are negative relative to the same model/forcing's 2005--2014
reference, but earlier paths and spatial magnitudes differ. The spatial audit
finds area-weighted majorities of lower-density cells in all eight
trajectories, while every trajectory retains cells with increases. The annual
scenario-separation audit finds SSP5-8.5 below SSP1-2.6 in 64--82 of 86 years,
with persistent ten-year separation beginning between 2021 and 2052 depending
on the forcing/model pair. This advances the ensemble biophysical benchmark
and exposes temporal model spread; it does not clear the matched-pulse or
welfare portions of this gate.

## Gate 4 — welfare translation and GIVE interface

Translate changes in catch/availability into producer and consumer welfare,
not gross revenue. Aggregate to countries/FUND regions with an explicit trade
or incidence assumption. Implement a replacement/addition decision only after
the overlap audit. Pair every climate/member, ecology, economy, and welfare
draw across baseline and CO2-pulse paths.

The coefficient-free country-to-region preflight is implemented. It uses a
declared one-country/one-region crosswalk, verifies draw identity and welfare
conservation, and withholds regional values when any declared country is
missing, incomplete, or not additive eligible. Remaining Gate 4 work requires
a reviewed global GIVE crosswalk and, upstream, an identified welfare model;
discounting and SCC integration remain intentionally unimplemented.

The Blue-SCC audit sharpens this gate. A first benchmark can use its published
country temperature damage coefficients only after source-license and exact-
replication checks. The market pathway must be labeled profit-plus-output-
multiplier damage rather than consumer/producer surplus. Its nutrition pathway
must remain a separate component with explicit substitution, baseline-health,
VSL, and terrestrial-food overlap sensitivities. FishMIP total-catch density
cannot be substituted for the Free et al. country profit input.

Additive eligibility is also fail-closed on a machine-readable overlap review:
the marine-capture welfare boundary must be named, the review must pass, and
all locked aquaculture, terrestrial-food-market, coral/reef, biodiversity,
CIAM-coastal, and gross-revenue exclusions must remain false. This is an
accounting safeguard, not empirical validation of the eventual model.

## Gate 5 — validation, uncertainty, publication

Require withheld years/regions/species, historical marine-heatwave tests,
conservation/stock assessment comparisons where valid, sensitivity to ocean
drivers and management/adaptation, and variance decomposition. Publish as a
separate paper with data limitations and nonmarket coral-reef services clearly
outside the initial fisheries estimate.
