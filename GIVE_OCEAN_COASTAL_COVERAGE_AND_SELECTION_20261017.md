# Exact GIVE ocean/coastal coverage and next-sector selection

Status: primary-source code audit completed October 17, 2026. The selected
research target is coral-reef recreation/tourism consumer welfare, but no
numeric addition to GIVE is authorized.

## Result

Coastal sea-level-rise damages are not a missing GIVE sector. GIVE runs CIAM
for baseline and emissions-pulse paths and adds their marginal difference to
the non-CIAM marginal damages before discounting. CIAM's optimal cost includes
dry-land inundation and associated property loss, relocation, storm-surge
capital loss, storm mortality valued using VSL, wetland-service loss, and the
costs of protection, retreat, or no adaptation. A new generic coastal-flood
module would therefore duplicate material existing damages.

GIVE does contain a physical ocean-pH component linked to atmospheric CO2.
Its pH output has no connection to `DamageAggregator`, consumption, or the SCC
calculation. Ocean ecosystem/nonmarket welfare is thus a genuine gap, except
for coastal wetland services already represented in CIAM.

## Selected route

The cleanest adjacent residual is consumer welfare from coral-reef recreation
and tourism. It excludes fisheries, food/raw-material provisioning, reef
coastal protection, CIAM wetlands, generic biodiversity nonuse, and carbon
cycle feedbacks.

This is the quickest defensible *research target*, not yet the quickest
defensible numeric SCC. The public Blue-SCC coral implementation reports a
global coral nonmarket-use SCC of 2.46 dollars per tonne CO2, but that category
bundles recreation with seven other services, including moderation of extreme
events and erosion prevention. The implementation uses a nonseparable welfare
structure and publishes no recreation-only annual baseline/pulse paths.
Allocating the headline total by the recreation valuation share would be an
unsupported estimate and is prohibited here.

## Rejected shortcuts

- Blue-SCC coral market provisioning combines food, raw materials, and
  ornamental resources. It overlaps fisheries and is not a clean incremental
  consumer-welfare endpoint.
- Blue-SCC coral nonuse value overlaps a future generic biodiversity/existence
  value sector.
- Blue-SCC ports combine physical asset impacts, revenue risk, and trade at
  risk, then fit a GDP-fraction-per-degree relationship. Physical coastal
  assets overlap CIAM; gross revenue and trade at risk are not automatically
  welfare losses. The released artifact is therefore not an additive GIVE
  component.
- A separate generic coastal-flood module is rejected because CIAM already
  covers the material sea-level-rise pathways above. Riverine and pluvial
  flooding remain conceptually distinct, but are outside this ocean/coastal
  selection and require a separate overlap audit.

## Admission gate

A coral recreation component can enter GIVE only after obtaining or estimating
service-specific country-year consumer welfare under matched baseline and
marginal-pulse paths, reconciling regional and global totals, harmonizing pulse
units/currency/discounting, and explicitly excluding fisheries, coastal
protection, wetlands, and biodiversity nonuse. Until those conditions pass,
the Blue-SCC number is external literature context only.

The machine-readable contract, pinned source hashes, executable audit, tests,
and run receipt accompany this note.
