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
acquired and content-validated for the scenario matrix. One checksum-pinned
All four BOATS/EcoOcean by GFDL-ESM4/IPSL-CM6A-LR preindustrial-control
historical/future pairs are also acquired and fully validated. This completes
the 20-file pinned catalogue but does not clear matched-pulse, welfare, or
production gates.

Observed-catch validation now has an official source gate. FAO FishStat Global
Production workspace 2026.1.0 (Global Capture Production 1950--2024) is
acquired under CC-BY-4.0 and passes exact-byte/SHA-512, ZIP integrity,
workspace-identity, and embedded capture-metadata checks. It records nominal
landings rather than discard-adjusted catch, assigns country mainly by vessel
flag rather than EEZ, mixes inland and marine capture until filtered, and
preserves missing/suppressed status codes. Record export, marine filtering,
country/area crosswalks, effort/management identification, and FishMIP
comparison remain pending; no missing value is treated as zero.
A post-export concentration audit finds material compositional change over the
FishMIP historical overlap: top-five vessel-flag-country and species shares
decline from 51.34%/37.71% in 1950 to 41.07%/24.23% in 2014, while the
top-five FAO-area share remains 70.84%. This rejects a composition-invariant
global scaling shortcut but does not authorize filtering, allocation,
calibration, welfare, damage, or SCC use.
A fixed-checkpoint turnover audit further finds adjacent-period composition
total-variation distances of 0.253--0.357 for countries, 0.315--0.448 for
species, and 0.138--0.314 for FAO areas. This closes only the descriptive
time-invariance screen: production allocation and calibration remain open.
The official FishStatJ 4.04.11 macOS export runtime is also frozen and passes
bundle integrity plus a bundled-Java smoke. Its Derby capture schema exposes
country/species/area/measure keys and separate annual values and symbols. A
disposable-copy headless export now independently reconciles 30,918 records
and 2,318,850 value/status pairs without treating missing or suppressed zeros
as observed absence. The supported FishStat GUI-menu export still must be
generated with symbols enabled and compared against the headless extract
before accepting a production observed-catch panel.

The all-file acquisition plan is now version-pinned and executable against a
fresh catalogue response. Its outcome-blind content smoke is limited to the
four BOATS/EcoOcean historical and SSP1-2.6 files under GFDL-ESM4 (513,826,771
catalogue bytes). After that smoke passed, the bounded scenario matrix added
the equivalent IPSL-CM6A-LR cells and both SSP5-8.5 futures. All 12 scenario
files passed complete-file checksum, schema, monthly chronology,
historical/future join, grid, unit, and missing-versus-zero checks. The first
all eight control files were subsequently admitted for bounded drift
diagnostics. See `FISHMIP_CONTENT_PLAN.md`.

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
on the forcing/model pair. A fixed five-band latitude audit finds at-least-
three-model weighted decline shares ranging from 64.77% to 95.97%, while
strict-unanimity ranges from 37.38% to 66.10%; this exposes geographic as well
as temporal heterogeneity. It does not substitute latitude bands for country
or EEZ allocation and does not clear the matched-pulse or welfare portions of
this gate.

The first BOATS/GFDL-ESM4 control pair materially narrows interpretation. Its
global mean `tc` density falls 23.66%, 30.75%, and 31.71% relative to its own
2005--2014 reference in the registered near-, mid-, and late-century decades.
The pair changes social forcing at 2015 and therefore cannot identify pure
autonomous ecological drift, but it demonstrates that raw BOATS scenario
changes are not forced-response estimates. The completed exact-support
adjustment yields forced-minus-control relative changes of -2.38/-2.03/-3.91
percentage points for SSP1-2.6 and -1.96/-2.95/-11.19 points for SSP5-8.5 in
the near/mid/late decades. This is a structural sensitivity, not causal or
marginal-pulse identification; model/forcing/social-forcing labels remain
explicit.

The EcoOcean/GFDL control pair provides a materially different bound. Its
near/mid/late control changes are -2.06%/-3.26%/-24.14%, and its exact-support
forced-minus-control changes are +2.18/+2.36/+0.72 percentage points for
SSP1-2.6 and +1.33/+0.26/-6.68 points for SSP5-8.5. Control adjustment thus
does not produce a common sign across ecosystem models and periods. These
contrasts strengthen the requirement for multiple ecosystem models and keep
all forced-response, pulse, welfare, damage, and SCC gates closed.

The IPSL controls complete the matrix. BOATS control changes are
-21.18%/-27.54%/-29.44%, with adjusted SSP1-2.6 changes of
+1.07/+0.18/+0.14 points and SSP5-8.5 changes of +1.38/-1.66/-7.46 points.
EcoOcean control changes are +1.29/+1.09/-14.05%, with adjusted SSP1-2.6
changes of -5.15/-5.99/-5.78 points and SSP5-8.5 changes of
-5.24/-6.48/-12.28 points. Across the complete 2-forcing by 2-model matrix,
all four adjusted SSP5-8.5 late-century changes are negative, while SSP1-2.6
and earlier cells retain mixed signs. This is not a probability or pulse.

The exact 20-file spatial adjustment preserves the same evidence boundary.
On 40,398 common finite cells, at least three of four adjusted trajectories are
negative over 42.22% of weighted area under SSP1-2.6 and 56.54% under
SSP5-8.5; unanimity reaches only 13.15% and 26.35%. The all-negative SSP5-8.5
global means therefore coexist with substantial local disagreement. This is a
structural spatial sensitivity, not a forced-response estimator, observed-
catch validation, country allocation, marginal pulse, or welfare evidence.

The registered 2021--2030, 2041--2050, and 2081--2090 spatial windows show
that the at-least-three-negative area share rises monotonically from 34.30% to
42.22% under SSP1-2.6 and from 33.51% to 56.54% under SSP5-8.5. Unanimity also
rises but reaches only 13.15% and 26.35% in the late window. This establishes
temporal persistence of increasing sign agreement inside the frozen matrix,
not causality, probability weights, observed-catch validation, allocation, a
matched pulse, welfare, damage, or SCC eligibility.

A stricter same-cell persistence audit qualifies that result. Requiring a
given trajectory to be negative at the same cell in all three registered
windows leaves only 15.34% of weighted area with persistent agreement from at
least three of four structures under SSP1-2.6 and 17.89% under SSP5-8.5;
persistent unanimity is 2.82% and 3.35%. Increasing aggregate sign agreement
through time therefore does not imply stable cross-model agreement at the same
locations. The same structural-sensitivity and non-SCC boundaries apply.

A matched latitude-band scenario-separation audit finds SSP5-8.5 more negative
than SSP1-2.6 in 43/60 forcing/model/window/band cells. Separation is mixed in
2021--2030, unanimous across all four structures in the three central bands by
2041--2050, and unanimous there plus the northern high latitudes by
2081--2090. Southern high latitudes remain split at end century. This narrows
the forcing contrast without supplying causal attribution, country allocation,
a matched pulse, welfare, damages, or SCC evidence.

A separate two-by-two structural-contrast diagnostic finds climate-forcing
contrasts larger in root-mean-square magnitude in 18/30 fixed
scenario/window/latitude cells and ecosystem-model contrasts larger in 12/30.
Neither dimension can be treated as negligible. This comparison is not a
probability weighting or variance decomposition and opens no forced-response,
allocation, pulse, welfare, damage, or SCC gate.

The predeclared 1.25-ratio dominance-stability check qualifies that count:
only 15/30 cells show material separation and 15 are near ties. The larger
axis is stable across scenarios in 13/15 window/latitude pairs but across all
three windows in only 3/10 scenario/latitude groups. This reinforces the need
to retain both structural dimensions and supplies no probability or variance
interpretation.

The frozen RMS-versus-mean-absolute robustness check agrees on the larger
structural axis in 20/30 cells. The mean-absolute summary yields eight exact
ties and changes ten labels relative to RMS. Summary-metric choice therefore
does not justify dropping a forcing or ecosystem-model dimension and supplies
no probability, variance, forced-response, allocation, welfare, damage, or SCC
interpretation.

## Gate 4 — welfare translation and GIVE interface

Translate changes in catch/availability into producer and consumer welfare,
not gross revenue. Aggregate to countries/FUND regions with an explicit trade
or incidence assumption. Implement a replacement/addition decision only after
the overlap audit. Pair every climate/member, ecology, economy, and welfare
draw across baseline and CO2-pulse paths.

The coefficient-free country-to-region preflight is implemented. Its reviewed
global aggregation universe is now the hash-bound baseline MimiGIVE mapping:
184 unique ISO3 countries in all 16 FUND regions, with exact region identities
and counts checked before use. The aggregator verifies draw identity and
welfare conservation and withholds regional values when any declared country
is missing, incomplete, or not additive eligible. Remaining Gate 4 work
requires a validated FishMIP/stock-to-country allocation, identified trade or
incidence assumptions, and an identified welfare model; discounting and SCC
integration remain intentionally unimplemented.

A coefficient-free grid/EEZ allocation preflight now defines the next spatial
boundary. It requires exact coverage of the declared FishMIP support grid,
unit-sum positive area fractions within every cell, a fixed source version and
license, and sovereign ISO3 keys present in the reviewed GIVE crosswalk. Joint
or disputed waters and high seas remain explicit, country-ineligible rows.
This is an executable contract only: no production EEZ geometry, fleet
incidence, trade, welfare, damage, or SCC result is supplied.

The candidate geometry is now outcome-blind: Marine Regions Maritime
Boundaries and EEZ version 12 (2023; doi:10.14284/632; CC-BY), with joint and
overlapping areas retained rather than silently assigned. The current download
page separately lists World High Seas version 2, so its topological consistency
with EEZ v12 must be demonstrated rather than assumed. Exact objects, bytes,
checksums, schema, topology, longitude handling, and ISO3 reconciliation remain
pending; no geometry has been acquired into this repository.

The official named GeoPackage request endpoints have been resolved for both
products. They return provider registration forms, not files, and require a
name, organisation, email, country, user category, purpose, and explicit
disclaimer acceptance. The official WFS metadata route was also checked. Its
capabilities identify `MarineRegions:eez` as EEZ v12 and its schema exposes
polygon type, territory/sovereign ISO slots, and MultiSurface geometry, but the
service access constraint asks users to contact VLIZ before using a layer. No
geometry was requested, no personal data were invented or submitted, no
provider contact was made, and no terms were accepted by the automation.
Acquisition therefore remains blocked on authorized human terms acceptance or
provider permission; the exact geometry object remains unpinned.

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
