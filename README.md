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
EcoOcean historical plus SSP1-2.6 under the same GFDL-ESM4 forcing. The two
BOATS files are now acquired and fully validated. The 90,012,681-byte
historical file has 780 contiguous `360_day` months from 1950 through 2014;
the 153,855,617-byte SSP1-2.6 file has 1,032 months from 2015 through 2100.
Both match their SHA-512 values, use the same global 1-degree grid and exact
finite/missing mask, and join at consecutive month indices 4967/4968. The
future file contains 42,390,432 finite values, 1,176,480 genuine zeros, no
negative values, and 24,483,168 time-stable missing values. The two EcoOcean
smoke files and cross-model content gate remain open. These outputs are
scenario total catch, not a matched marginal-CO2 response and not welfare, so
no fisheries damage coefficient or SCC is inferred from them.

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
```

These scripts do not choose ecological or economic parameters, certify that a
crosswalk is globally exhaustive, discount damages, or calculate an SCC.
Passing the overlap schema also does not substitute for evidence that the
declared exclusions were applied; it prevents an unresolved or contradictory
boundary from being marked additive eligible.
