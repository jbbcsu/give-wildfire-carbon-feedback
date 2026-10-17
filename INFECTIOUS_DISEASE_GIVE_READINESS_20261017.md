# Infectious-disease damages in GIVE: coverage and readiness audit

Date: 2026-10-17

## Decision

Develop dengue morbidity as the leading global infectious-disease bridge, using the published response model in Childs et al. (2025). Do not yet add an infectious-disease SCC to GIVE. The response function is credible and open, but the public workflow is not a one-ton pulse damage model and does not supply a compatible morbidity valuation layer.

## Exact existing GIVE health coverage

The target GIVE implementation contains:

1. `MimiGIVE/src/components/cromar_mortality_damages.jl`: country-level excess deaths from global mean temperature, combining heat and cold effects, monetized with VSL.
2. `MimiGIVE/src/components/DamageAggregator.jl`: aggregates Cromar mortality with agriculture and energy damages.
3. CIAM: coastal-storm mortality is separately valued.

No explicit vector-borne infectious-disease or general morbidity component was found. This creates a plausible missing morbidity channel, but not an automatically additive mortality channel: a temperature-driven all-cause mortality coefficient can already embody some disease deaths.

This conclusion is tied to exact file hashes in `provenance/source_manifest_v1.json`, rather than a generic description of GIVE. The audited target files are `cromar_mortality_damages.jl` and `DamageAggregator.jl` in the archived MimiGIVE package.

## Primary published bridge

Childs et al., “Climate warming is expanding dengue burden in the Americas and Asia,” *PNAS* (2025), DOI [10.1073/pnas.2512350122](https://doi.org/10.1073/pnas.2512350122), estimates a nonlinear temperature–dengue incidence response from approximately 1.5 million incidence records in 21 countries. The authors' fixed-effects PPML estimator includes cubic temperature lags, precipitation controls, population weights, and unit/year/month fixed effects. Their code projects changes in cases under climate scenarios.

The analysis code is MIT-licensed and pinned here at Git commit `cd8e354df0291a930d489ef1171b448112476c7b`. The associated Zenodo data archive is DOI [10.5281/zenodo.16883976](https://doi.org/10.5281/zenodo.16883976). Some upstream inputs require separate Earth Engine or Copernicus access, so code availability is stronger than unrestricted end-to-end data availability.

### Strengths

- Direct climate-to-observed-incidence estimation rather than a suitability-only proxy.
- Large subnational panel spanning the Americas and Asia.
- Nonlinear response and uncertainty propagation through bootstrap draws.
- Open, inspectable estimator and projection code.

### Limits for GIVE

- The evidence domain is 21 countries, not the globe. Extrapolation beyond that domain is prohibited by the initial contract.
- Published projections compare climate scenarios; they do not evaluate GIVE's matched baseline and one-ton CO2 pulse trajectories.
- The paper projects cases, not monetized welfare damages.
- The projection requires local monthly climate fields, population, baseline incidence, and unit covariates. GMT alone is insufficient.
- Full upstream projection is computationally large: the authors note about 75 GB memory for 25 bootstrap projections. It must be chunked on the server and cannot run under the present 1 GB audit cap.
- Precipitation enters the historical specification as a control; the published projection bridge should not be described as an independently identified precipitation-driven disease projection without further verification.

## Overlap boundary

The first allowed target is **nonfatal symptomatic dengue morbidity**:

- allow direct medical resource cost if a primary, geographically resolved valuation source is pinned;
- allow nonfatal health burden only under a predeclared welfare-valuation convention;
- exclude dengue mortality until the Cromar all-cause mortality target is made cause-exclusive or the two are estimated jointly;
- exclude lost wages initially because the labor-productivity extension may already value the same absent workdays;
- exclude any air-pollution and coastal-storm health outcomes already assigned elsewhere.

Medical cost is not automatically equivalent to welfare loss. Any later valuation must distinguish treatment resource cost, household expenditures, nonfatal utility loss, and productivity loss, and must not sum overlapping measures.

## Why not use FrEDI as the global source?

EPA FrEDI v4.1.1 includes U.S. Valley Fever and Vibriosis damage categories with medical, work-loss, and mortality subchannels. Those are useful CONUS sentinels and target-contract examples, but transferring them globally would be unsupported. Suicide is specifically unsuitable here because FrEDI flags overlap and it is not an infectious-disease endpoint.

## Required path to a publishable partial SCC

1. Reproduce the published historical response and selected scenario projections from the pinned source, using only authorized data.
2. Build a monthly, location-matched GIVE baseline/pulse climate adapter. Verify that both temperature and precipitation treatments match the published model rather than using annual GMT directly.
3. Define the endemic/study-domain mask and a transparent non-extrapolation rule. Results should initially be labeled a 21-country partial SCC.
4. Pin a primary morbidity valuation source by country and year. Keep medical resource cost separate from welfare and productivity measures.
5. Generate base and pulse cases for every coefficient/GCM draw; difference them before monetization and discounting.
6. Independently reproduce at least one published projection result and validate monotonicity, zero-pulse, units, temporal alignment, and aggregation.
7. Pass mortality and labor overlap reviews. Only then change `additive_scc_allowed` to true.

## Deliverable achieved here

This repository provides immutable source provenance, an executable estimator/projection audit, a header-only GIVE pulse contract, overlap exclusions, and a release invariant. It deliberately contains no fabricated coefficients, observations, cases, damages, or SCC values.
