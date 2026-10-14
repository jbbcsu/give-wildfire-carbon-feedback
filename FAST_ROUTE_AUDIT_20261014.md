# Global transport-heat and electricity-supply feasibility audit

Audit date: 2026-10-14

Decision: **no reviewed package is presently transferable into GIVE**

This is a bounded literature and artifact screen. It does not extrapolate
FrEDI outside the United States, transfer a regional coefficient, fill missing
country values, or calculate a damage function or SCC.

## Bottom line

Two evidence chains are concrete enough to preserve, but each stops before an
SCC-ready interface:

1. **Road and rail:** Koks et al. (2019) and its AGPL-3.0 GMTRA code provide a
   globally resolved, country-reportable model of direct expected annual repair
   damage with sensitivity analysis. The published calculation is for current
   earthquake, cyclone, and flood hazards, not climate-change heat. Its flood
   layer also depends on Fathom data used by permission. Wang et al. (2024)
   supplies global annual heat-exposure projections, but explicitly does not
   monetize risk or model vulnerability. Mulholland and Feyen (2021) supplies
   annual monetized road-rutting and rail-buckling responses at warming levels,
   but only for EU27 plus the United Kingdom. Combining these studies would
   require an unsupported global transfer of European heat fragilities, asset
   values, and maintenance cycles, so this audit does not combine them.
2. **Electricity supply:** Turner et al. (2017) couples global hydrology and
   1,593 dams to 32-region GCAM and reports climate-related generation-capacity
   investment effects across 16 GCMs. The published endpoint is cumulative,
   discounted investment through 2100 rather than an annual welfare path. The
   paper-specific hydropower inputs, GCAM configuration, and run outputs were
   not located in a pinned release. Current GCAM source is open under ECL-2.0,
   but generic GCAM is not a substitute: its documentation says hydropower is
   prescribed as exogenous `fixedOutput` and that hydropower costs are not
   estimated. Gernaat et al. (2021) releases global renewable potential and
   cost-supply data, but only historical and late-century climate slices, not
   annual realized damages or a marginal-pulse path.

The shortest defensible next step is therefore an author-artifact request, not
new estimation. The machine-readable gate record is in
`config/candidate_screen_v1.json`.

## Candidate screen

| Candidate | Global | Climate/heat response | Annual monetized path | Uncertainty | Open/pinned implementation | Marginal pulse | Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| Koks et al. 2019 / GMTRA | Yes | No | Current-climate EAD only | Yes | Partial; code open, Fathom restricted | No | Reject |
| Wang et al. 2024 global heat exposure | Yes | Yes | No; kilometres exposed only | Yes | Partial; source datasets named, no code archive located | No | Reject |
| Liu et al. 2023 precipitation exposure | Yes | Yes, precipitation only | No | Yes | Yes for code/results; 9.7 GB archive | No | Reject |
| Mulholland & Feyen 2021 heat O&M | No; EU27+UK | Yes | Warming-level annual O&M | Yes | Paper open; complete executable package not located | No | Reject |
| Schweikert et al. 2014 / IPSS | No; 10 countries | Yes | Yes for applications | 54 GCM scenarios | Reusable software/release not located | No | Reject |
| Turner et al. 2017 / GCAM | Yes, 32 regions | Yes, hydropower only | No; cumulative discounted investment | 16 GCMs | Partial; GCAM open, study inputs/config absent | No | Reject |
| van Vliet et al. 2016 | Yes | Yes, hydro + thermoelectric capacity | No | Multi-model | No; plant inventory includes proprietary Platts data | No | Reject |
| Gernaat et al. 2021 | Yes | Yes, renewables | No; historical/2071-2100 potentials and cost-supply curves | Multiple GCMs | Data open; full model chain not pinned here | No | Reject |

### Why the global heat studies do not complete the transport model

Wang et al. use annual CMIP6 indicators from 2015–2100 and report expected
annual exposure of 18.9 million km of OSM road/rail assets. The authors state
that they identify exposed length rather than monetized risk, do not quantify
hazard magnitude, and do not represent vulnerability; they also warn against
global extension of local empirical thresholds. Liu et al. similarly releases
global precipitation return-period exposure code and a versioned 9.7 GB Zenodo
dataset, but the endpoint is exposure and a design safety factor, not damage.

Mulholland and Feyen are the strongest heat valuation evidence: road rutting
and railway buckling are linked to additional annual O&M under 1.5, 2, 3, and
4 degrees C warming. Yet EU asset values, maintenance cycles, pavement design,
and rail stress-free temperatures are constitutive inputs, not a coefficient
that can be assigned to other countries without validation. The published
warming-level results are also not a matched annual baseline/pulse ensemble.

### Why the electricity studies do not complete a grid/supply model

Turner et al. evaluate power-sector emissions and cumulative generating-
capacity investment discounted to 2010, in five-year GCAM steps. Their country
map allocates regional cumulative investment according to each country's
current hydropower-generation share, which is not a released country-level
annual welfare simulation. The experiment omits other climate-sensitive supply
and demand channels, including thermal cooling-water constraints and changing
cooling demand. It is useful global supply evidence, but not a complete grid
damage model or a marginal CO2 pulse.

Van Vliet et al. quantify climate effects on usable capacity at 24,515
hydropower and 1,427 thermoelectric plants, but do not monetize the response;
the plant inventory includes proprietary Platts data. Gernaat et al. provides
open NetCDF/CSV renewable potentials and cost-supply curves for historical and
2071–2100 climate windows. Those data could inform a future energy-system run,
but cannot themselves yield annual welfare or grid damages.

No screened global study supplies monetized transmission/distribution damage,
outage welfare, and generation-supply impacts in one open, annually resolved
package. This negative result is narrower than saying no such work exists: it
means none was found in the bounded primary-source screen that clears all
listed transfer gates.

## Accounting boundaries required for GIVE

A future transport component may include direct climate-attributable road and
rail repair, replacement, and incremental O&M resource costs. It must exclude
or separately reconcile:

- inland/pluvial and coastal flooding already represented elsewhere;
- wildfire damage;
- vehicle, freight, time-delay, macroeconomic, and supply-chain losses unless
  their welfare incidence is independently identified; and
- CONUS FrEDI geography and endpoints, to prevent duplication.

A future electricity component may include climate-attributable generation,
transmission, distribution, storage, and reliability resource/welfare costs.
It must exclude or reconcile:

- household/commercial cooling and heating demand already in GIVE energy;
- wildfire, inland flood, and coastal flood damage to power assets;
- mitigation-policy costs and carbon payments, which are not climate damages;
- emissions from substitute generation, which cannot be monetized again as a
  same-sector damage; and
- transfers among utilities, consumers, and governments versus real resource
  costs and consumer/producer surplus.

Adaptation policy, asset growth, retirement, technology, and socioeconomic
conditions must be identical within every baseline/pulse pair.

## Exact artifact request: road and rail heat

Request one immutable, licensed bundle that combines global climate exposure
with validated engineering damage functions without assuming European
transferability:

1. Code tag/commit, environment lock, and scripts from daily climate through
   country-year outputs.
2. Global asset inventory vintage and stable asset IDs; road surface/design,
   railway type, stress-free temperature, replacement value, maintenance cycle,
   and asset survival/growth inputs with licenses.
3. Heat response functions for rutting, buckling, repair, replacement, and O&M,
   including calibration geography, parameter uncertainty, applicability rules,
   and explicit unsupported countries/assets. Unsupported coverage must remain
   missing and must not be renormalized.
4. Annual, undiscounted baseline and marginal-pulse paths with identical
   climate member, assets, socioeconomic state, and adaptation; identify pulse
   gas, mass in tCO2, year, injection convention, and first divergence year.
5. Country/GIVE-region crosswalk and conserving aggregation from asset to
   country to region; no GDP or road-length allocation of missing damages.
6. Draw manifest preserving climate, engineering, valuation, and asset-state
   dependence between the paired paths.
7. Output columns for `run_id`, `draw_id`, `path_role`, `pulse_id`, `asset_id`,
   `iso3`, `year`, `hazard`, `asset_class`, `cost_component`, `cost`, `currency`,
   `price_year`, `time_basis`, `adaptation_state`, and `missingness_status`.
8. An additive reconciliation separating heat from flood/coastal/wildfire
   hazards and direct asset/O&M cost from delay, user, and macroeconomic loss.

## Exact artifact request: electricity supply and grid

For the Turner/GCAM route, request:

1. Exact GCAM version/commit, scenario XML/configuration, build environment,
   query definitions, and all study modifications.
2. Baseline and each GCM's regional hydropower `fixedOutput` inputs at every
   model year, with the hydrology/dam-model code, 1,593-dam mapping, capacity
   assumptions, and licenses for ICOLD or replacement dam data.
3. Undiscounted region-year outputs for generation, capacity additions and
   retirements, capital, fixed/variable O&M, fuel, trade, unserved energy,
   reliability, emissions, carbon payments, and any salvage value. Include the
   exact identity used to construct cumulative investment.
4. A documented welfare identity distinguishing real resource cost,
   consumer/producer surplus, transfers, carbon-policy cost, and adaptation.
5. Matched annual or model-step baseline/pulse pairs with identical policy,
   demand, technology, socioeconomic, and random states; pulse metadata and
   first-divergence diagnostics as specified above.
6. The full region-country mapping. Do not allocate regional damages using
   present hydropower shares unless authors establish that as the modeled
   incidence rule and provide a conserving reconciliation.
7. Joint uncertainty IDs and weights, or an explicit statement that the
   ensemble is unweighted, preserving all GCM/hydrology/technology pairings.
8. Licenses and checksums for code, inputs, mappings, and outputs plus an
   overlap statement for demand, wildfire, flood/coastal, and substitute-
   generation emissions.

For a grid-complete extension, add asset-level transmission/distribution
exposure, heat derating and hazard fragilities, repair/outage costs, value-of-
lost-load or surplus semantics, restoration/adaptation state, and the same
paired annual output contract. Generic open power-flow or capacity-expansion
software alone does not satisfy this request.

Preferred formats are UTF-8 CSV or Parquet for tables, NetCDF/Zarr for gridded
climate, JSON for manifests and mappings, and SHA-256 checksums. All monetary
fields require currency, price year, exchange-rate basis, discount status, and
flow-versus-stock semantics.

## Primary sources and official repositories

- Koks et al. (2019), *Nature Communications*:
  https://doi.org/10.1038/s41467-019-10442-3
- GMTRA code (AGPL-3.0), pinned audit revision
  `1ffe03798ab4b8d6bc6bd09c2d876a6f7994b891`:
  https://github.com/ElcoK/gmtra/tree/1ffe03798ab4b8d6bc6bd09c2d876a6f7994b891
- Wang et al. (2024), *Earth's Future*:
  https://doi.org/10.1029/2023EF003632
- Liu et al. (2023), *Nature Communications*:
  https://doi.org/10.1038/s41467-023-38203-3
- Liu code and versioned data:
  https://github.com/Vapson/InfExposure and https://doi.org/10.5281/zenodo.7711820
- Mulholland and Feyen (2021), *Climate Risk Management*:
  https://doi.org/10.1016/j.crm.2021.100365
- Schweikert et al. (2014), *Procedia Engineering*:
  https://doi.org/10.1016/j.proeng.2014.07.072
- Turner et al. (2017), *Energy*, official PNNL record:
  https://eesm.science.energy.gov/publications/climate-impacts-hydropower-and-consequences-global-electricity-supply-investment-needs
- GCAM source and hydropower documentation:
  https://github.com/JGCRI/gcam-core and
  https://jgcri.github.io/gcam-doc/supply_energy.html#hydropower
- van Vliet et al. (2016), *Nature Climate Change*:
  https://doi.org/10.1038/nclimate2903
- Gernaat et al. (2021), *Nature Climate Change*, and official NAVIGATE data
  catalog:
  https://doi.org/10.1038/s41558-020-00949-9 and
  https://www.navigate-h2020.eu/navigator/apply/
