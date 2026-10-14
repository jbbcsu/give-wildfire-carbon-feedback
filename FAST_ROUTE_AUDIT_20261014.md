# Municipal drought/water-supply fast-route audit

Audit date: 2026-10-14

Scope: municipal/household water-supply damages, with inland riverine/pluvial flooding as a comparator

Decision: **no published package presently clears the GIVE transfer gates**

This is a source and transfer-feasibility audit. It does not estimate a damage
function, allocate mixed-sector values, or calculate an SCC.

## Result

The closest welfare model is Dolan et al. (2021), implemented with GCAM 5.1.1.
It is unusually relevant because it calculates consumer-plus-producer surplus
and includes municipal water demand in a global model with 235 water basins.
It is not transferable as a municipal GIVE component from the released
artifacts:

1. the surplus is for a combined water market serving irrigation, livestock,
   municipal, manufacturing, primary energy, and electricity demand;
2. raw supply/demand curves needed to reconstruct the published welfare metric
   are available only by request;
3. the contrast is constrained versus unlimited water, not baseline versus a
   marginal CO2 pulse;
4. GCAM output is at model time steps rather than an annual damage path; and
5. the paper notes that the RCP4.5 hydrology forcing can be inconsistent with
   the emissions trajectory of a sampled scenario.

MimiFUND v3.13.0 is the shortest technical pulse route: it has annual global
regional water-impact paths, uncertainty distributions, permissively licensed
source and calibration data, and an official paired marginal-model interface.
It still fails the scientific transfer boundary. Its regional coefficients are
for aggregate “water resources,” with no released municipal/irrigation/
industry/energy/recreation/ecosystem decomposition or explicit municipal
welfare concept. The source component also consumes regional temperature while
the scientific documentation describes global mean temperature. This audit
does not relabel that aggregate endpoint as municipal.

CLIMADA’s published GloFAS river-flood module is the strongest open physical
comparator, not a faster welfare route. It is globally applicable and has
explicit ensemble/bootstrap/vulnerability uncertainty, but the demonstrated
endpoint is event displacement rather than annual welfare. Its hazard maps
cover river systems with catchments above 5,000 km², and the authors explicitly
warn that the module is not a pluvial-flood model. No marginal-pulse workflow
or reconciled exposure-class boundary is released.

## Seven transfer gates

| Candidate | Climate response | Annual welfare | Coverage | Uncertainty | Marginal pulse | License | Overlap boundary | GIVE-ready |
|---|---|---|---|---|---|---|---|---|
| Dolan/GCAM water surplus | Partial | Fail | Pass | Pass | Fail | Fail for complete inputs | Fail | No |
| MimiFUND water resources | Partial | Partial | Pass | Pass | Pass | Pass | Fail | No |
| CLIMADA/GloFAS river flood | Partial | Fail | Partial | Pass | Fail | Pass | Fail | No |

The machine-readable reasons and source bindings are in
`config/fast_route_screen_v1.json`.

## Required accounting boundary

The admissible component is limited to municipal/household water-supply
reliability and municipal treatment, pumping, storage, and conveyance costs.
It must exclude or explicitly reconcile:

- crop and agricultural-market damages already represented by GIVE;
- energy-demand and energy-supply damages already represented by GIVE;
- coastal flooding and protection already represented by CIAM;
- irrigation, livestock, manufacturing, primary-energy, electricity, and
  hydropower water impacts;
- inland flood capital/displacement losses; and
- recreation, ecosystem-service, and nonuse values.

Allocating a mixed water-market surplus using withdrawal shares, GDP shares,
or population shares is not admissible. Nor is subtracting separately estimated
agriculture or energy damages from an aggregate water value: neither operation
preserves consumer/producer incidence or interaction effects.

## Exact artifact request for the lead GCAM route

Request one immutable, licensed bundle tied to Dolan et al. (2021) and GCAM
5.1.1 containing:

1. **Source and environment** — exact GCAM and GCAM.surplus revisions, all
   modified inputs absent from public GCAM 5.1.1, build/run instructions, and
   dependency lock information.
2. **Matched raw curves** — constrained and unlimited supply/demand curves for
   every successful run, basin, market, and model time step, with stable run
   IDs, scenario-factor IDs, units, currency, and price year. Include the 124
   failed-run IDs and failure reasons rather than silently dropping them.
3. **Municipal welfare decomposition** — author-supported municipal consumer
   surplus, producer surplus/resource cost, and total, together with the
   identity that reconciles municipal plus other sectoral components to the
   released total water-market surplus. If the equilibrium model does not
   permit additive sector attribution, state that explicitly; no ad hoc
   allocation will be used.
4. **Climate response and pulse pair** — annual hydrology/water-market inputs
   and outputs for a matched baseline and marginal CO2 pulse with identical
   socioeconomic, land, technology, groundwater, reservoir, policy, and random
   states; pulse year, gas, mass in tCO2, injection convention, and first
   divergence year must be explicit.
5. **Uncertainty pairing** — draw/scenario manifest with ESM, socioeconomic,
   agricultural productivity, groundwater, reservoir, and land-policy IDs,
   any weights or the explicit statement that the factorial ensemble is
   unweighted, and all correlations/pairings preserved between baseline and
   pulse.
6. **Geography** — the complete 235-basin definition and a country/GIVE-region
   crosswalk with a conserving treatment of transboundary basins. Population,
   demand, GDP, or area allocation may not be invented after receipt.
7. **Provenance, license, and boundary** — checksums; redistribution and
   derivative-use terms for every input/output; welfare sign convention;
   currency/price year/time basis; and a signed accounting note excluding or
   reconciling GIVE agriculture, GIVE energy, CIAM coastal protection,
   manufacturing, hydropower, ecosystems/recreation, and inland-flood assets.

Minimum machine-readable formats: UTF-8 CSV or Parquet for tabular paths,
NetCDF for gridded hydrology, JSON for manifests, and SHA-256 checksums. Annual
rows require at least `run_id`, `path_role`, `pulse_id`, `basin_id`,
`country_iso3` or an authoritative mapping key, `year`, `sector`,
`consumer_surplus`, `producer_surplus_or_resource_cost`, `total_welfare`,
`currency`, `price_year`, `time_basis`, `missingness_status`, and all scenario/
draw IDs.

## Comparator artifact request

CLIMADA becomes a viable inland-flood damage candidate only with:

- globally complete riverine and pluvial hazard coverage or explicit excluded
  geography (not renormalized);
- future-climate annual event sets paired under baseline and marginal-pulse
  climate forcing;
- welfare rather than displacement/direct-asset output, with adaptation and
  reconstruction accounting;
- exposure classes that exclude or reconcile agriculture, energy, and coastal
  CIAM assets; and
- a country/GIVE mapping, uncertainty pairings, checksums, and licenses for all
  external hazard, protection, exposure, and vulnerability inputs.

## External benchmark allowed, but not promoted

Dolan et al. (2021) is a defensible manuscript benchmark for the proposition
that global water scarcity can create material, highly uncertain welfare
effects transmitted through multisector markets. It should be presented only
as scenario-based global water-market evidence. It is not a municipal-only
damage estimate, is not a marginal SCC, and must not be added to GIVE.

## Primary sources

- Dolan et al. (2021), *Nature Communications*:
  https://doi.org/10.1038/s41467-021-22194-0
- GCAM.surplus v1.0.0 archive:
  https://doi.org/10.5281/zenodo.4470017
- GCAM 5.1.1 source:
  https://github.com/JGCRI/gcam-core/tree/gcam-v5.1.1
- MimiFUND v3.13.0:
  https://github.com/fund-model/MimiFUND.jl/releases/tag/v3.13.0
- FUND scientific documentation:
  https://www.fund-model.org/files/documentation/Fund-3-9-Scientific-Documentation.pdf
- Riedel et al. (2024), *Geoscientific Model Development*:
  https://doi.org/10.5194/gmd-17-5291-2024
- Riedel replication archive:
  https://doi.org/10.5281/zenodo.10518953
- CLIMADA core and petals releases:
  https://github.com/CLIMADA-project/climada_python/releases/tag/v6.1.0 and
  https://github.com/CLIMADA-project/climada_petals/releases/tag/v6.2.0
