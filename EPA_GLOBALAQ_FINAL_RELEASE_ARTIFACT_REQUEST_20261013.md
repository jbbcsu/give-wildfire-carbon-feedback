# EPA globalAQ final-release reconciliation and artifact request

## Decision

The shortest defensible route to the published ozone and non-wildfire PM2.5
benchmarks is a final-release reconciliation with the authors, not a new local
estimate. As of 2026-10-13, the official EPA repository still points only to
commit `1139e7aff1ca7806b6b542268e829f9759dd8808`, dated 2025-09-29. The
official GitHub API reports no release and no tag, and `git ls-remote` exposes
only `main` at that same commit. The commit message describes files for
publication submission; it predates the final 2026 article.

The code is MIT-licensed and the repository describes its data and figures as
CC-BY-4.0. Those terms do not establish redistribution rights for every
third-party RFF, MimiGIVE/FaIR, mortality, or IFs input that is absent from the
repository. Artifact-level source and license metadata are therefore still
needed.

No wildfire file was read, no missing value was imputed, and neither article
benchmark is promoted to a GIVE result.

## Source-version result

At the article's 2.0% Ramsey setting, equal weighting of the two checked-in
GCM rows gives:

| Checked-in output | Ozone | PM2.5 | Net or component sum |
|---|---:|---:|---:|
| 10,000-path RFF component summary | +16.67165 | -24.52905 | -7.85740 |
| Separate RFF net summary | — | — | -34.66762 |
| Mean-path component summary | +20.65854 | -21.90870 | -1.25015 |
| Final article benchmark | +23 | -38 | -15 |

All values are USD/tCO2 as labelled by the released workflow. Neither
checked-in component summary reproduces the article components. Moreover, the
checked-in RFF net is $26.81022/tCO2 below the sum of its component file,
whereas the article's +23 and -38 components sum exactly to its -15 net. This
is evidence that the checked-in component and net summaries are not a
same-run additive release; it is not a basis for choosing or adjusting either
file.

The official 33-entry tree contains no Parquet file and no dependency lock or
session manifest. Its `.gitignore` excludes the RFF population/income and
temperature inputs, reduced-form-tool outputs, and country/full-stream NPV
outputs needed to rerun the published path.

There is also a price-year conflict in the checked-in source. The input builder
converts GDP to 2024 dollars, records `dollar.year = 2024`, and the reduced-form
tool specifies a $13.90 million 2024-dollar VSL, while the NPV script header
states that all dollar values are 2020 dollars. The final delivery must identify
the actual price year and any conversion applied before the reported SCCs.

## Suggested author-facing request

**Subject:** Versioned reproduction artifacts for McDuffie et al. globalAQ results

We are reproducing the ozone and non-wildfire PM2.5 marginal-damage results in
McDuffie et al. (doi:10.1021/acs.est.5c14713) for comparison with the GIVE
integrated assessment model. We audited the official EPA `globalAQ_rft`
repository at commit `1139e7aff1ca7806b6b542268e829f9759dd8808`.

Could you provide a tagged archive or stable deposit for the exact source,
inputs, and outputs used for the final article? A manifest-only response is
useful where third-party licenses prohibit redistribution, provided it gives
stable source identifiers, hashes, access instructions, and the permitted
derived outputs.

### 1. Exact version and environment

- The article-generating commit or archive, including any changes after the
  2025-09-29 submission commit.
- `renv.lock` or an equivalent R package/version manifest, R version, platform,
  locale, and `sessionInfo()` output.
- A manifest containing each artifact's relative path, SHA-256, byte size,
  format, derivation/source, license identifier, rights holder, redistribution
  permission, and third-party restrictions.
- The final currency and price year, including a reconciliation of the 2024-
  dollar GDP/VSL inputs with the NPV script's 2020-dollar header.

### 2. Inputs referenced but not released

- `input/RFF/pop_income/rffsp_pop_income_run_<trial>.feather` for the exact
  socioeconomic trials used.
- `input/RFF/temperature/rffsp_fair_sequence.csv`.
- `input/RFF/temperature/CO2-2030-climate_variables_with_carbon_feedbacks/model_1/TempNorm_1850to1900_global_temperature_norm.csv`.
- `input/RFF/temperature/CO2-2030-climate_variables_with_carbon_feedbacks/model_2/TempNorm_1850to1900_global_temperature_norm.csv`.
- `input/IFs/mx_trajectories.csv` and `input/IFs/pop_trajectories.csv`.
- The derived inputs
  `input/RFF/rft_inputs/sampled_pop_trajectory_numbers.csv`,
  `global_mean_surface_temperature_baseline.parquet`,
  `global_mean_surface_temperature_perturbed_co2_2030.parquet`,
  `All Trajectories Baseline Mortality_Cause Specific.parquet`, and
  `rffsp_pop_gdp_all_trials.parquet`.

For restricted inputs, please provide the exact release/version, persistent
URL or DOI, retrieval date, checksum, filters, units, and a script that derives
the released intermediate without embedding restricted rows.

### 3. Matched pulse and annual damage streams

Please specify the 2030 perturbation's gas, pulse magnitude and mass unit,
carbon-to-CO2 conversion, FaIR/MimiGIVE version and configuration, baseline
run identifier, perturbed run identifier, and whether carbon-cycle feedbacks
are included. The checked-in NPV code applies `(12/44) * 1e-9`; the underlying
pulse convention must be stated explicitly rather than inferred from that
conversion.

Please provide either the complete `output/rft/damages_<trial>_rft.parquet`
set and downstream NPV chunks, or an equivalent compact export that preserves
the article calculation. The minimum annual long table may be CSV or Parquet
and must have the key
`trial, model, pollutant, country_id, year, damage_type`. Required fields are:

- `baseline_value`, `perturbed_value`, and `marginal_value`;
- `currency`, `price_year`, `value_unit`, and `time_basis`;
- `population`, `gdp`, baseline temperature, and perturbed temperature;
- `discount_schedule`, `discount_factor`, and pulse metadata; and
- an explicit missingness code, with no unavailable country-year treated as
  zero.

The component and net summaries must be regenerated from the same annual
streams and satisfy, within a declared tolerance:

1. ozone plus PM2.5 equals net for every trial/model before averaging;
2. country sums equal the global value for every year and pollutant;
3. the declared two-model and 10,000-path averaging rule reproduces the final
   article's +$23/tCO2 ozone, -$38/tCO2 PM2.5, and -$15/tCO2 net values at the
   2.0% Ramsey setting.

### 4. Non-wildfire PM2.5 boundary

Please supply a machine-readable pathway description naming all included PM2.5
species, source sectors, emissions inventories, dust/sea-salt treatment, and
the exact open-burning/wildfire exclusion. It should also identify whether any
ozone mortality, crop, wildfire-smoke, or carbon-cycle effects are present.
This boundary is required to keep non-wildfire PM2.5 separate from the wildfire
project and to avoid overlap with other GIVE mortality pathways.

## Minimum acceptance rule

The article benchmarks remain external comparison values until a single
versioned delivery passes all of the following: exact source identity,
artifact-level licensing, matched baseline/pulse metadata, complete annual
country support, component/net additivity, article-value reproduction, and a
machine-verifiable non-wildfire boundary. Partial files are not renormalized,
and the published rounded values are never used as calibration targets.

The machine-readable local audit contract and receipt are:

- `config/epa_globalaq_release_reconciliation_v1.json`
- `data/provenance/epa_globalaq_release_reconciliation_20261013.json`
