# Climate migration: literature and welfare-accounting audit

## Conclusion

Climate-driven migration outside coastal CIAM is missing from GIVE, but the
screened evidence does not support an additive migration SCC. Migration is a
choice or constraint-mediated response to heterogeneous climate impacts. It can
reduce damages by allowing adaptation, while forced displacement and mobility
frictions can impose real and nonpecuniary costs. A migrant count is therefore
not itself a welfare loss, and there is no defensible universal cost per migrant.

The appropriate finished product at this stage is a fail-closed integration
contract. No numerical value is interpreted as zero; the category remains an
unquantified omission.

## Exact GIVE boundary

GIVE's CIAM integration already prices coastal relocation. The archived source
defines relocation costs for people, mobile capital, and demolition following
coastal dry-land loss. Under retreat, the relocation subcost enters
`RetreatCost`; under no adaptation it enters `NoAdaptCost`. The optimal adaptation
choice assigns the relevant relocation amount to `OptimalRelocate`, while
MimiGIVE constructs marginal sea-level damages from `OptimalCost` under matched
base and pulse runs. Adding a generic sea-level displacement estimate would
therefore double count.

GIVE does not have a corresponding explicit module for inland disaster
displacement, slow-onset noncoastal internal migration, or international
migration. However, most triggers of those movements—lost agricultural income,
heat productivity, mortality, flooding, cyclone destruction, or ecosystem
loss—are or may be separately represented in the damage expansion. Their income
and property losses cannot be counted again as “migration costs.”

## Screened executable models

### Cruz and Rossi-Hansberg

*The Economic Geography of Global Warming* is the strongest open global
structural benchmark. It models a high-resolution dynamic spatial economy with
costly migration and trade and reports climate welfare with migration as an
adaptation mechanism. Its CC-BY-4.0 replication package is public and
checksum-pinned here (2.303 GB).

It is not an additive migration module. Its welfare response jointly reflects
temperature effects on productivity and amenities, spatial reallocation,
innovation, trade, and migration. Adding its total welfare to GIVE would overlap
multiple GIVE sectors. A counterfactual that changes migration frictions measures
the value of an adaptation margin within that structural model, not a separable
damage caused by migration. It is suitable as a mutually exclusive structural
sensitivity or eventual replacement model.

### Burzynski et al.

*Climate Change, Inequality, and Human Migration* jointly represents internal
and international migration, inequality, temperature, sea-level rise, fast-onset
events, conflict, and other economic channels. The CC0 replication deposit is
open, but its 80 listed files total 116.6 GB. The integration is scientifically
valuable but precisely why its output is not additive to sector-by-sector GIVE:
coastal, disaster, productivity, conflict, and migration mechanisms are coupled.

### Groundswell

The World Bank's Groundswell work projects internal population redistribution by
comparing climate-impact scenarios with development-only counterparts through
2050. These are scenario-based migration quantities, not annual monetized welfare
under a marginal carbon pulse. The modeled attractiveness channels include water,
crop productivity, ecosystems, floods, and sea-level rise, which also create
overlap. The projections can validate direction and broad spatial patterns but
cannot be multiplied by an assumed cost per migrant.

## Reduced-form evidence

Peer-reviewed studies establish heterogeneous links between weather, climate
stress, disasters, and mobility. Examples include the Hoffmann et al. meta-analysis,
Missirian and Schlenker's asylum-application response, and Deryugina et al.'s
long-run post-Katrina outcomes. These studies differ in migration definition,
hazard, population, spatial scale, and outcome. Local earnings or transfer changes
after a disaster are not a globally transferable welfare coefficient, and a
disaster study does not isolate marginal anthropogenic climate attribution.

## Required integration design

The preferred future analysis is a structural spatial-equilibrium **sensitivity
or replacement**, evaluated under identical GIVE baseline and pulse climate paths.
It must report consumption-equivalent welfare by origin and destination and keep
the climate productivity/amenity functions explicit so overlapping GIVE modules
can be disabled.

An additive exception could be considered only for incremental real relocation
resources or separately identified nonpecuniary losses. The estimator would need
to exclude coastal CIAM relocation, original property/income losses, government
transfers, and receiving-region gains already captured elsewhere. It must model
voluntary adaptation separately from forced displacement and preserve both origin
and destination incidence.

Until an implementation passes every gate in the machine-readable contract,
`numeric_scc_authorized=false`.

