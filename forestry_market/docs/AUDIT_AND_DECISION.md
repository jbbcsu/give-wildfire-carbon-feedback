# Forestry/timber market sector audit and decision record

## Coverage and target

The audited GIVE damage aggregation contains Cromar mortality, agriculture,
and energy, plus CIAM coastal damages. The RFF/GIVE omission inventory marks
forestry/timber/pulp/paper as missing. The proposed endpoint is therefore the
change in **consumer plus producer surplus in timber and forest-product
markets**, not the physical value of forests.

The checked evidence and exact workspace locations are recorded in
`provenance/give_coverage_audit.csv`; this makes the coverage conclusion
auditable without importing or modifying files from other sector projects.

This boundary excludes agriculture, coastal and inland property, wildfire CO2,
smoke health, forest carbon, recreation, habitat, biodiversity, and other
nonmarket ecosystem services. A future disturbance model would need an explicit
overlap audit because the legacy ecological calibration may already reflect
broad changes in forest stocks and productivity.

## Evidence screen

Sohngen, Mendelsohn, and Sedjo (2001) connect a global ecological model to a
dynamic timber-market model and report global market-welfare effects. That is
the closest published endpoint, but the underlying climate/ecology scenarios
and market calibration are old and no complete, directly SCC-ready replication
package was identified.

Modern open global forest-sector models improve the implementation base:

- TiMBA is an open partial-equilibrium model covering production, consumption,
  trade, and social surplus in 180 countries. Its released baseline is not a
  ready climate-damage response function.
- FOROM is a global recursive dynamic partial-equilibrium model and has been
  used for extreme-weather disruptions. Some replication inputs are restricted,
  and the published application is not a marginal global-temperature/pulse
  forestry SCC.
- MimiFUND v3.13.0 contains an open, executable global forestry-market welfare
  component calibrated from older timber-market evidence. It is the only source
  found that supports an immediate source-pinned marginal-emissions benchmark.

Primary sources:

- Sohngen, B., Mendelsohn, R., and Sedjo, R. (2001), “A Global Model of Climate
  Change Impacts on Timber Markets,” *Journal of Agricultural and Resource
  Economics* 26(2), 326–343. https://ageconsearch.umn.edu/record/31044
- MimiFUND tagged source: https://github.com/fund-model/MimiFUND.jl/tree/v3.13.0
- TiMBA software paper: https://doi.org/10.21105/joss.08034
- FOROM technical documentation: https://research.fs.usda.gov/treesearch/62897
- Johnston (2024), extreme weather and wood-product markets:
  https://doi.org/10.1029/2024EF004742

## Executable benchmark

The source-pinned benchmark uses MimiFUND v3.13.0 at commit
`3f5fe29ffb753a49ff070d04b74ae42abd23576b`. A 10 million metric-tonne CO2
pulse is added in 2025; Mimi's marginal model normalizes the difference by the
pulse size. The forestry component returns changes in consumer and producer
surplus in billion 1995 USD. FUND subtracts positive forestry benefits from
aggregate loss, so this project multiplies the marginal forestry output by
`-1e9`. It then discounts annual regional values and converts 1995 to 2020 USD
using the BEA GDP implicit price deflator (NIPA Table 1.1.9; annual index 66.939
in 1995 and 105.377 in 2020).

The primary comparison uses a constant 2% rate through 2300. Sensitivities use
2.5%, 3%, FUND's Ramsey schedule, a 2100/3000 horizon, a tenfold-smaller pulse,
and a channel diagnostic that switches off the explicit CO2-fertilization term.
The script also varies, one at a time, the regional response coefficients, CO2
coefficient, income elasticity, and temperature nonlinearity by one source
standard deviation. These are diagnostics, not a probabilistic uncertainty
interval. The regional coefficients and forestry response parameters have
distributions in FUND, but a credible paper should not interpret that legacy
parameter distribution as current scientific uncertainty.

### Reproduced values

The central legacy benchmark is **-$0.076953/tCO2** in 2020 USD at a fixed 2%
rate (a market benefit, not a damage). The corresponding values are -$0.058622
at 2.5% and -$0.046360 at 3%. Switching off the explicit CO2 term leaves
-$0.043658/tCO2, while the residual CO2 channel is -$0.033295/tCO2. The
one-at-a-time ±1 source-standard-deviation diagnostics range from -$0.037065 to
-$0.154557/tCO2. They do not form a probability interval.

Most of the source calibration implies benefits, but effects are heterogeneous:
Australia/New Zealand (+$0.003574/tCO2) and the former Soviet region
(+$0.001073/tCO2) have damages under the central run. A tenfold change in pulse
size changes the normalized estimate by only `7.93e-7` in relative terms. The
3000 rather than 2300 horizon changes the fixed-2% estimate by about 0.23%.

## Claim gates

The benchmark is **not additive to GIVE**. The following gates are closed:

1. **Documentation/code conflict.** The v3.13.0 science page describes income
   elasticity `+0.31` and CO2 coefficient `0.44`; executable defaults use
   `forel=-0.31` and `forco2=2.2972`. The repository's Monte Carlo definitions
   agree with the executable defaults, but the discrepancy prevents an
   unqualified central claim.
2. **Legacy calibration.** Ecological and market response evidence predates
   current climate projections, disturbance science, adaptation, and current
   forest-product markets.
3. **Scenario mismatch.** The benchmark uses FUND's 16-region socioeconomic and
   climate paths, not GIVE's SSP/climate ensemble.
4. **Overlap uncertainty.** Adding a separate fire, pest, storm, carbon, or
   nonmarket forest module could double count physical forest changes.
5. **Uncertainty.** The source distributions are reproducible but not a modern
   calibrated posterior and therefore are not promoted as one.

## Shortest defensible path to integration

1. Ask the MimiFUND maintainers to resolve the documented/executable coefficient
   discrepancy and archive the response.
2. Treat the reproduced value as an external magnitude/sign benchmark only.
3. Build a new climate-to-forest-supply shock layer from a current multi-model
   vegetation/forest ensemble, explicitly separating gradual productivity from
   wildfire, storms, pests, and carbon values.
4. Feed those physical supply shocks into TiMBA (preferred open global market
   engine) and compute changes in consumer plus producer surplus under matched
   baseline and pulse trajectories.
5. Rebase to GIVE socioeconomic paths, run common climate/pulse draws, and pass
   overlap, currency, horizon, pulse-linearity, and component-add-up tests.
6. Only then change `additive_to_GIVE` in the target contract.
