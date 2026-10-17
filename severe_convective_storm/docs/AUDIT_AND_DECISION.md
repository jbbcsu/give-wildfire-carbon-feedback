# Audit and decision: severe convective storms and hail property damage

## Decision

Implement a **bounded Swiss building-hail benchmark**, not a GIVE SCC module. The benchmark is useful evidence that this omitted channel can be material locally and that an end-to-end hazard–exposure–vulnerability workflow exists. It is not sufficient evidence for a global marginal SCC.

Schmid, Gebhart, and Bresch (2026) compare an 11-year present-day convection-permitting simulation (2011–2021) with a pseudo-global-warming experiment at +3 °C relative to preindustrial. Holding exposure fixed, their Swiss calibration-region annual average building loss rises from CHF 74 million to CHF 90 million, a published rounded increase of 22%. The arithmetic implied by the rounded monetary values is 21.62%; that is a diagnostic, not a more precise empirical estimate.

## GIVE coverage

A case-insensitive search of the inspected GIVE source (`src`, `packages`, and `data`) found no hail, tornado, thunderstorm, or severe-convective-storm property module. Storm-related matches belong to CIAM/coastal storm surge. The project-level RFF/GIVE omission audit also does not separately enumerate hail. Therefore, the endpoint appears missing, while coastal flooding and tropical-cyclone pathways remain outside this module.

## Why this study is the strongest bounded bridge

- It joins a climate perturbation to simulated hail fields and then to direct building damage in one peer-reviewed chain.
- It uses 2.2 km convection-permitting simulations and an explicit +3 °C pseudo-global-warming experiment rather than extrapolating a historical loss trend.
- Its vulnerability functions descend from an open-source CLIMADA hail model calibrated on Swiss claims and building exposure. The underlying 2024 model used 250,000 reports and 989,000 buildings across four cantons.
- The climate-study event-set and code have persistent records, but the large event set is unnecessary for reproducing the paper's published endpoint benchmark and was not downloaded.

The European monetary result is not promoted. Applying Swiss vulnerability to other countries introduces transfer uncertainty, and a European total still would not establish a global marginal SCC.

## Why SCC integration fails closed

The paper supplies two warming-level endpoints, not an annual response function along GIVE trajectories. Dividing CHF 16 million by 3 °C would impose an unsupported linearity assumption. Scaling by European or global GDP/property values would impose unsupported hazard, exposure, vulnerability, adaptation, and insurance assumptions. The source's monetary price year is not pinned in this benchmark, so even conversion to GIVE consumption units is blocked. A marginal CO2 pulse also requires annual base-versus-pulse damages and consistent discounting.

No SCC or additive GIVE result should be reported until every gate in `contracts/hail_property_contract.json` passes.

## Overlap boundary

The promoted endpoint is direct physical building damage from hail. It excludes crop/livestock hail loss, vehicles, wind/tornado/lightning, precipitation-driven flooding, coastal/tropical-cyclone loss, wildfire, transport and grid infrastructure, and indirect business interruption. Before addition to GIVE, a future implementation must audit whether any general property or adaptation module already absorbs hail repair costs.

## Uncertainty

The climate literature does not justify a single global hail multiplier. IPCC AR6 reports low confidence in historical hail/severe-wind trends and substantial regional projection uncertainty. The benchmark therefore preserves its experimental and geographic bounds. It does not attach the paper's damaged-building-count interval to monetary losses; these are distinct outcomes.

## Reproducibility and provenance

Primary records:

- Schmid, Gebhart, and Bresch (2026), *Climate Services* 41, 100630. DOI: `10.1016/j.cliser.2025.100630`.
- Schmid et al. (2024), *Natural Hazards and Earth System Sciences* 24, 847–872. DOI: `10.5194/nhess-24-847-2024`.
- Brennan et al. (2025), *Natural Hazards and Earth System Sciences* 25, 3693–3720. DOI: `10.5194/nhess-25-3693-2025`.
- Trapp et al. (2019), *Journal of Climate*. DOI: `10.1175/JCLI-D-18-0740.1`.
- IPCC AR6 WGI, Chapters 11 and 12.
- Public 330-year European hail event set: Zenodo record `17860440` (not downloaded; approximately 19.9 GB).

The local builder uses only source-pinned published values, emits a transparent arithmetic check, and writes a machine-readable readiness failure. Raw data and PDFs are ignored.

## Exact next research steps

1. Obtain or reproduce annual loss outputs at multiple warming levels and across multiple driving climate models; do not infer intermediate points from the two published endpoints.
2. Establish a public country-level building exposure/value basis and region-specific vulnerability/adaptation assumptions.
3. Pin the monetary valuation year and convert to GIVE's consumption units.
4. Drive baseline and marginal-emissions-pulse temperature paths through the validated hazard/damage response.
5. Propagate climate, hail physics, exposure, vulnerability, and adaptation uncertainty.
6. Pass overlap and additivity tests against all other property/infrastructure modules.
