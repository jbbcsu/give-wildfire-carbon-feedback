# Blue-SCC fisheries artifact request

## Suggested author-facing message

**Subject:** Reproducibility artifacts for the Blue-SCC fisheries market component

We are evaluating whether the fisheries market component in Bastien-Olvera et
al. (doi:10.1038/s41558-025-02533-5) can be reproduced as annual,
country-resolved marginal damages and compared with the GIVE integrated
assessment model. We audited the public `blue-scc` repository at commit
`dbc0d8cb21c81f1508abfaf9e5c0f5671ccdd83f`. We are not requesting permission
to reinterpret missing values or to treat the released country SCC file as an
additive decomposition.

Could you provide, or point us to a versioned archive containing, the items
below? If third-party restrictions prevent redistribution, a manifest with
stable source identifiers, checksums, access instructions, and the permitted
derivative outputs would still resolve much of the provenance gap.

## Requested artifacts

### 1. Rights and environment

- A code license and data license, or artifact-level terms identifying the
  rights holder, redistribution and derivative-use permissions, attribution,
  and third-party restrictions. No root license was present at the audited
  commit.
- Exact R, Python, GAMS, and package versions. In particular, please preserve
  the `countrycode` version used for continent/region assignment.
- The exact RICE50x commit, any Blue-SCC patches or input-translation changes,
  and the commands/configuration used for the baseline run.

### 2. Market-response source chain

The audited code references these files, which are absent from the repository:

- `External_Data/input_modules/fish/Statistical/total_catch_profit_timeseries.Rds`
- `External_Data/output_modules/fish/fisheries_Free_EtAl.csv`
- `External_Data/SSPs/SspDb_country_data_2013-06-12.csv`
- `External_Data/SSPs/ssp_gdp.csv`
- `External_Data/SSPs/ssp_pop.csv`
- `External_Data/other/scenarios/SSP245_magicc_202303021423.csv`
- `External_Data/other/scenarios/SSP585_magicc_202303221353.csv`
- `External_Data/other/scenarios/SSP126_magicc_202308040902.csv`
- `External_Data/other/scenarios/SSP460_magicc_202402051249.csv`

Please also provide snapshots of the WDI queries used for
`NY.GDP.MKTP.PP.KD` (all countries, 2012–2021) and `NY.GDP.DEFL.ZS` (USA,
2000–2021), rather than requiring a live API response.

The requested country/multiplier crosswalk should identify ISO3, the exact
`countrycode` version, assigned region, direct, indirect, induced, and total
multipliers, the unmatched/default rule, and the source citation. A
multiplier-free direct-effect series is needed separately from the expanded
output-effect series. Please state whether `profits_usd` represents producer
surplus, accounting profit, or another welfare concept, and whether consumer
surplus is available.

### 3. Matched RICE50x runs and annual output

The released SCC code expects the following exact runtime outputs for
`scc_mc("BASELINE", "baseline")`, none of which is in the audited repository:

- `bluerice/baseline/results/results_ocean_today_BASELINE.gdx`
- `bluerice/baseline/results/results_ocean_damage_BASELINE.gdx`
- `bluerice/baseline/results/results_ocean_damage_pulse_BASELINE.gdx`

Please supply those GDX files together with pulse gas, mass, mass unit, pulse
year, socioeconomic scenario, climate configuration, discounting parameters,
and baseline/pulse run identifiers. The source comments describe a one-million-
ton pulse; the delivery should state unambiguously whether this is CO2 or C and
the conversion applied.

For a tool-independent check, please also export annual country fisheries
market flows as CSV or Parquet. The minimum primary key is
`run_id, pulse_id, country_iso3, year, valuation`. Required columns are
`welfare_concept, baseline_value, pulse_value, currency, price_year,
time_basis, missingness_status`. Baseline and pulse values must come from the
same run configuration, unavailable values must remain explicitly missing,
and no country may be silently added, zero-filled, or renormalized.

### 4. Country support and decomposition

Please provide a country-key crosswalk with
`source_country_key, country_iso3, coefficient_available,
country_scc_available, missingness_status, missingness_reason`. This is needed
because the released files contain 143 temperature-coefficient keys and 155
country-SCC keys, with only 120 common keys: 23 are coefficient-only and 35 are
country-SCC-only.

For the same global run, please provide additive country contributions using
the global run's weights, with these identities and declared numerical
tolerances:

1. annual global market change equals the sum of country market changes;
2. global market SCC equals the sum of additive country contributions; and
3. the reproduced global market SCC equals the Figure 4 value of
   $0.05704041587845721 per tCO2 in 2020 USD.

The current `country_level=True` routine changes the aggregation key and
constructs country-specific population-weighted consumption and discount
factors. Its 155 market rows sum to $0.05266463482912126/tCO2, 7.67% below the
Figure 4 value, so they cannot presently serve as additive country shares.

### 5. Reconciliation questions

Please clarify:

- why the released market country rows sum to $0.05266463482912126/tCO2 while
  Figure 4 reports $0.05704041587845721/tCO2;
- why the released non-market country rows sum to $23.132225131011346/tCO2
  while Figure 4 reports $22.04050947136718/tCO2;
- whether `country_level=True` was intended to report standalone country SCCs
  rather than contributions to the global SCC;
- the exact rule mapping the 143 coefficient keys to the 155 SCC keys;
- which indirect/induced multiplier effects or other market-damage categories
  must be excluded to avoid overlap with an economy-wide IAM; and
- whether a direct consumer-plus-producer-surplus output can be released.

## Minimum delivery manifest

Each supplied file should have one machine-readable manifest row containing
`artifact_id, relative_path, sha256, byte_size, format,
source_or_derivation, license_id, software_versions`. The full requested
contract, table keys, and acceptance gates are in
`config/blue_scc_author_artifact_request_v1.json`.

Receiving files is not itself sufficient to open the GIVE transfer gate. The
license, matched-run, additivity, welfare, missingness, and overlap checks must
all pass independently.

## Manuscript-safe external benchmark

The following is defensible as a literature comparison and should not be
added to GIVE or described as a local result:

> As an external benchmark, the released Figure 4 source data for
> Bastien-Olvera et al. report a 2020 baseline fisheries SCC of $22.09755 per
> tCO2 (2020 USD), comprising $0.05704/tCO2 in market value and
> $22.04051/tCO2 in non-market-use value. We report this published result for
> scale only; differing welfare definitions, country support, mortality
> overlap, and global-versus-country discounting prevent its addition to the
> GIVE SCC.

Suggested table:

| Published external benchmark | 2020 USD/tCO2 | Treatment in GIVE |
|---|---:|---|
| Fisheries market value | 0.057040 | Context only; not added |
| Fisheries non-market use value | 22.040509 | Context only; not added |
| Fisheries total | 22.097550 | Context only; not added |

Source: Bastien-Olvera et al., doi:10.1038/s41558-025-02533-5, released Figure
4 workbook. Values are externally published outputs, not estimates from this
repository. The table must retain the market/non-market split and the
non-addition note; presenting only the total would conceal the dominant
nutrition/mortality pathway and its overlap risk.
