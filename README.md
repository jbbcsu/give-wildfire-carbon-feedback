# GIVE ocean-fisheries damages extension

This is a standalone, future GIVE damage-sector track. It is separate from
the precipitation-agriculture and wildfire projects and must never import,
modify, or overwrite their code, data, results, or manuscripts.

## Proposed scope

Estimate the marginal welfare consequences of CO2-driven changes to marine
capture fisheries. The candidate chain is:

`CO2 pulse -> ocean temperature / acidification / oxygen and productivity ->
species abundance and distribution -> potential catch / harvest -> consumer
and producer welfare -> SCC`.

The initial deliverable is a literature, data, overlap, and feasibility audit;
it is not an SCC estimate. The research track follows RFF's ocean-systems
agenda and prioritizes fisheries because commercial harvest has a potentially
global market-valued pathway. It does not assert that fisheries exceed every
other omitted climate-damage sector in expected SCC magnitude.

## Accounting boundary

- Include: climate-caused changes in marine capture-fisheries welfare,
  including food/protein and producer/consumer surplus where estimable.
- Exclude: terrestrial agriculture; aquaculture unless separately identified;
  direct coastal property/storm protection losses already represented in
  CIAM; coral-reef nonmarket/tourism services unless a separate component
  prevents overlap; nonclimate overfishing/pollution effects except as
  baseline controls or interactions.
- Do not use revenue alone as welfare. Do not double-count fish-food losses
  with a terrestrial food-price/agriculture welfare module.

## Sources guiding the audit

- RFF, *Challenges and Opportunities for Incorporating Climate Change's
  Impacts on Ocean Systems into the Social Cost of Greenhouse Gases* (2024):
  https://www.rff.org/publications/reports/challenges-and-opportunities-for-incorporating-climate-changes-impacts-on-ocean-systems-into-the-social-cost-of-greenhouse-gases/
- RFF identifies fisheries and coral reefs as prospective ocean-system
  additions, while warning that global fisheries dynamics, producer welfare,
  adaptation, and data coverage remain unresolved.

See [PLAN.md](PLAN.md) for staged gates. No raw data are stored in Git.
The cross-sector RFF coverage review and bounded next-sector recommendation are
in [GIVE_SECTOR_COVERAGE_SCREEN.md](GIVE_SECTOR_COVERAGE_SCREEN.md); they do not
authorize cross-sector code or data inside this repository.

## Reviewed FishMIP catalogue snapshot

The ISIMIP3b public catalogue currently exposes 20 global monthly total-catch
density (`tc`) datasets in a balanced grid of BOATS and EcoOcean, forced by
GFDL-ESM4 and IPSL-CM6A-LR, with historical, preindustrial-control, SSP1-2.6,
and SSP5-8.5 experiments. The versioned, machine-readable audit is
[`data/provenance/fishmip_isimip3b_tc_catalog.toml`](data/provenance/fishmip_isimip3b_tc_catalog.toml),
and `scripts/validate_fishmip_catalog.py` validates an API response before any
download. The exact 20-file, checksum-bearing acquisition plan and bounded
four-file content smoke are documented in
[`FISHMIP_CONTENT_PLAN.md`](FISHMIP_CONTENT_PLAN.md). The plan pins 2,585,466,439
catalogue bytes overall but initially permits only 513,826,771 bytes: BOATS and
EcoOcean historical plus SSP1-2.6 under the same GFDL-ESM4 forcing. All four
files are now acquired and fully validated. The 90,012,681-byte BOATS
historical file has 780 contiguous `360_day` months from 1950 through 2014;
the 153,855,617-byte SSP1-2.6 file has 1,032 months from 2015 through 2100.
Both match their SHA-512 values, use the same global 1-degree grid and exact
finite/missing mask, and join at consecutive month indices 4967/4968. The
future file contains 42,390,432 finite values, 1,176,480 genuine zeros, no
negative values, and 24,483,168 time-stable missing values. The corresponding
116,279,679-byte and 153,678,794-byte EcoOcean files use exact month-start
offsets under a `365_day` calendar, match their checksums, and join from day
151079 to 151110 without a missing month. They contain 33,798,960 and
44,718,624 finite values, respectively, no negatives, no genuine zeros, and
time-stable masks. The model masks are not identical: 41,029 grid cells are
common, 47 are BOATS-only, and 2,303 are EcoOcean-only. Any cross-model
comparison must carry an explicit common-support flag and may not turn
unsupported cells into zeros. These outputs are
scenario total catch, not a matched marginal-CO2 response and not welfare, so
no fisheries damage coefficient or SCC is inferred from them.

The first support-matched scenario diagnostics are documented in
[`FISHMIP_SCENARIO_BENCHMARK.md`](FISHMIP_SCENARIO_BENCHMARK.md). On the 41,029
cells jointly supported by BOATS and EcoOcean, the cosine-latitude-weighted
annual mean `tc` density in 2081--2090 under SSP1-2.6 is 35.62% below BOATS's
own 2005--2014 reference and 24.40% below EcoOcean's own reference. Under
SSP5-8.5 the corresponding late-century changes are -42.91% and -31.90%.
The independently validated IPSL-CM6A-LR matrix retains 40,399 common cells;
its late-century changes are -29.31%/-21.17% under SSP1-2.6 and
-36.94%/-27.42% under SSP5-8.5 for BOATS/EcoOcean.
Earlier periods disagree more: under SSP1-2.6 BOATS is 26.04% below its
reference in 2021--2030 while EcoOcean is 0.27% above its reference. The
diagnostic does not average model levels, because their absolute scales differ
greatly, and it remains a scenario benchmark rather than a pulse, welfare,
damage, or SCC result.

An executable cross-matrix audit now verifies the complete two-forcing,
two-scenario, two-ecosystem-model factorial, identical historical references
and common support across scenarios, and finite period changes. It finds
negative changes in 7/8 near-, 8/8 mid-, and 8/8 late-century trajectories;
SSP5-8.5 is more negative than SSP1-2.6 in 2/4 near- and 4/4 mid- and
late-century within-forcing/model comparisons. These are descriptive sign
counts, not probabilities or welfare evidence.

The bounded spatial-distribution audit in
[`FISHMIP_SPATIAL_CHANGE_DISTRIBUTION.md`](FISHMIP_SPATIAL_CHANGE_DISTRIBUTION.md)
shows that each of the eight late-century trajectories has lower catch density
over a majority of its forcing-specific common-support ocean area. The
cosine-latitude-weighted lower-cell shares range from 68.21% to 97.70%, while
unweighted lower-cell shares range from 64.95% to 94.24%. Every trajectory
also retains cells with increases, so the global declines are spatially broad
but not universal. This remains a modelled scenario-density diagnostic, not
observed catch, a marginal pulse, welfare, damages, or SCC evidence.

The annual within-model comparison in
[`FISHMIP_SCENARIO_SEPARATION.md`](FISHMIP_SCENARIO_SEPARATION.md) adds a
persistence check. SSP5-8.5 is below SSP1-2.6 in 64--82 of 86 annual values
across the four forcing/model pairs, but the first persistent ten-year lower
run ranges from 2021 to 2052 and near-century differences have mixed signs.
All four late-century differences are negative. This is still scenario
separation, not a matched pulse or welfare response.

## Executable accounting scaffolding

The repository currently provides two coefficient-free checks:

- `scripts/validate_welfare_interface.py` validates matched baseline/pulse
  inputs and country-year welfare outputs, including missing-versus-zero
  semantics and a fail-closed, machine-readable overlap review. Reusing one
  accounting-boundary identifier with different locked exclusions anywhere in
  an output file is rejected.
- `scripts/aggregate_welfare_to_regions.py` aggregates already eligible
  country-year welfare changes through an explicit country-to-GIVE-region
  crosswalk. It fails each region closed if a declared country is absent,
  incomplete, or not additive eligible, and emits no partial numeric total.

Run the synthetic checks with:

```bash
python3 test/test_welfare_interface.py
python3 test/test_region_aggregation.py
python3 test/test_fishmip_catalog.py
python3 test/test_fishmip_content.py  # in an environment with xarray and h5netcdf
python3 test/test_fishmip_scenario_benchmark.py  # same environment requirement
python3 test/test_fishmip_scenario_matrix.py
python3 test/test_fishmip_scenario_separation.py  # same environment requirement
```

These scripts do not choose ecological or economic parameters, certify that a
crosswalk is globally exhaustive, discount damages, or calculate an SCC.
Passing the overlap schema also does not substitute for evidence that the
declared exclusions were applied; it prevents an unresolved or contradictory
boundary from being marked additive eligible.

## Published fisheries-SCC benchmark

The project now includes a hash- and commit-pinned audit of Bastien-Olvera et
al., *Accounting for ocean impacts nearly doubles the social cost of carbon*
(doi:10.1038/s41558-025-02533-5) and its public Blue-SCC repository. The
audited Figure 4 source data report $22.09755/tCO2 for fisheries under the
paper's baseline settings: $0.05704 market value and $22.04051 non-market use
value. These are published external benchmarks, not estimates from this
repository.

The audit also records why the benchmark cannot be copied mechanically into
GIVE. The market route uses Free et al. country profit projections, regional
output multipliers, and temperature slopes rather than explicit consumer plus
producer surplus. The much larger nutrition route carries separate nutrient,
health, substitution, dependence, and VSL assumptions. The public repository
had no explicit root license file at the audited commit, so this project stores
only aggregate audit facts and hashes. See
[`BLUE_SCC_FISHERIES_BENCHMARK_AUDIT.md`](BLUE_SCC_FISHERIES_BENCHMARK_AUDIT.md).
