# Reproducing the preliminary quantity-channel SCC release

## Scope

This release reproduces and validates the paired annual-global-maize
rainfall-quantity SCC benchmark. It does not reproduce a complete
precipitation-agriculture SCC. Raw and intermediate climate/agriculture data
are intentionally excluded from Git; the commands below require the
checksum-bound ignored inputs named in the provenance receipts.

Use the project `.venv` and run one numerical job at a time. The coefficient
jobs peak near 225 MB sampled process-group RSS. The paired Julia ensemble has
already been run sequentially and peaked at 2.20 GB; do not rerun it alongside
another analysis on a memory-constrained machine.

## Coefficient uncertainty

Recreate the central 2% coefficient-only interval:

```bash
python3 scripts/run_bounded_job.py \
  --receipt data/interim/quantity_coefficient_delta_job.json \
  --log data/interim/quantity_coefficient_delta_job.log \
  --max-mib 768 --min-free-gib 149.8 -- \
  .venv/bin/python scripts/estimate_quantity_coefficient_delta_uncertainty.py \
  --panel-receipt data/provenance/hultgren_quantity_response_panel_20260924.json \
  --slopes data/interim/epa_annual_country_pattern_benchmark_20260921/country_model_slopes.csv \
  --fair data/interim/give_fair_temperature_path_smoke/temperature_paths.csv \
  --cpc data/interim/give_deterministic_discount_path_20260924.csv \
  --diagnostic-receipt data/provenance/epa_fair_hultgren_quantity_partial_scc_diagnostic_20260924.json \
  --output data/interim/quantity_coefficient_delta_result.json
```

Use a free-space floor appropriate to the current machine, never lower than a
freshly measured starting free space minus 64 MiB for these tiny-output,
existing-data jobs. Recreate the four-schedule grid by substituting
`scripts/estimate_quantity_coefficient_delta_uncertainty_grid.py` and adding
`--two-percent-receipt` for the preceding result. Recreate all 104
model-by-schedule intervals with
`scripts/estimate_quantity_coefficient_delta_by_model.py`, passing the grid as
`--grid-receipt`. Each script requires fresh outputs and fails closed on source
hash, schema, support, numerical-reconstruction, or finite-difference checks.

## Geographic and temporal accounting

Recreate the 106-country accounting decomposition sequentially under a 768 MiB
sampled-RSS budget:

```bash
.venv/bin/python scripts/run_bounded_job.py \
  --receipt data/interim/quantity_scc_country_job.json \
  --log data/interim/quantity_scc_country_job.log \
  --max-mib 768 --min-free-gib 100 -- \
  .venv/bin/python scripts/decompose_quantity_scc_by_country.py \
  --panel-receipt data/provenance/hultgren_quantity_response_panel_20260924.json \
  --slopes data/interim/epa_annual_country_pattern_benchmark_20260921/country_model_slopes.csv \
  --fair data/interim/give_fair_temperature_path_smoke/temperature_paths.csv \
  --cpc data/interim/give_deterministic_discount_path_20260924.csv \
  --diagnostic-receipt data/provenance/epa_fair_hultgren_quantity_partial_scc_diagnostic_20260924.json \
  --output-table data/interim/quantity_scc_country.csv \
  --output data/interim/quantity_scc_country_receipt.json
```

The fixed model denominator is important: a country without an eligible slope
in a model contributes zero rather than being averaged only over its supported
models. The dedicated unit test freezes that rule:

```bash
.venv/bin/python -m unittest -v tests/test_quantity_scc_country_decomposition.py
```

Recreate the annual model-year path and four period bins with the same bounded
wrapper, substituting `scripts/decompose_quantity_scc_by_period.py` and its
`--output-table`/`--output` paths. Then reweight the validated physical path
under all four GIVE discount schedules:

```bash
.venv/bin/python scripts/summarize_quantity_scc_period_discount_grid.py \
  --annual-receipt data/interim/quantity_scc_period_receipt.json \
  --cpc data/interim/give_deterministic_discount_path_20260924.csv \
  --diagnostic-receipt data/provenance/epa_fair_hultgren_quantity_partial_scc_diagnostic_20260924.json \
  --output data/interim/quantity_scc_period_discount_grid.json
```

The country and annual jobs peaked near 171 MiB. Each reconstructs every
climate model's independent central SCC before reporting a decomposition.

## Figure and manuscript checks

The model-specific interval figure requires only Python's standard library:

```bash
python3 scripts/plot_quantity_coefficient_intervals.py \
  data/provenance/quantity_coefficient_delta_by_model_20260925.json \
  data/interim/quantity_coefficient_intervals.svg \
  data/interim/quantity_coefficient_interval_figure.json
```

Recreate the two interpretation figures from the validated decomposition
receipts:

```bash
.venv/bin/python scripts/plot_quantity_scc_country_decomposition.py \
  data/interim/quantity_scc_country_receipt.json \
  data/interim/quantity_scc_country.svg \
  data/interim/quantity_scc_country_figure.json

.venv/bin/python scripts/plot_quantity_scc_period_discount_grid.py \
  data/interim/quantity_scc_period_discount_grid.json \
  data/interim/quantity_scc_period_discount_grid.svg \
  data/interim/quantity_scc_period_figure.json
```

Regenerate Table 3, including its geographic and temporal panels, only after
the four input receipts pass:

```bash
.venv/bin/python scripts/build_manuscript_scc_table.py \
  --structural data/provenance/quantity_structural_sensitivity_envelope_20260924.json \
  --coefficient-grid data/provenance/quantity_coefficient_delta_uncertainty_grid_20260925.json \
  --market-grid data/provenance/quantity_coefficient_delta_market_grid_20260925.json \
  --country data/provenance/quantity_scc_country_decomposition_20260925.json \
  --period-grid data/provenance/quantity_scc_period_discount_grid_20260925.json \
  --output data/interim/TABLE_3_SCC_RESULTS.md \
  --receipt data/interim/manuscript_scc_table.json
```

Validate that the manuscript's headline numbers and claim boundaries match the
receipts:

```bash
.venv/bin/python scripts/validate_manuscript_scc_claims.py \
  --manuscript manuscript/MAIN_MANUSCRIPT.md \
  --structural data/provenance/quantity_structural_sensitivity_envelope_20260924.json \
  --coefficient-grid data/provenance/quantity_coefficient_delta_uncertainty_grid_20260925.json \
  --by-model data/provenance/quantity_coefficient_delta_by_model_20260925.json \
  --output data/interim/manuscript_scc_claim_validation.json
```

Validate the DOI registry, the wildfire/agriculture DOI non-conflation rule,
and every local manuscript/README link:

```bash
.venv/bin/python scripts/validate_manuscript_references.py \
  --manuscript manuscript/MAIN_MANUSCRIPT.md \
  --registry data/provenance/manuscript_reference_registry_20260925.json \
  --output data/interim/manuscript_reference_validation.json

.venv/bin/python scripts/validate_manuscript_links.py \
  --document manuscript/MAIN_MANUSCRIPT.md \
  --document manuscript/METHODS_SUPPORTING_INFORMATION.md \
  --output data/interim/manuscript_link_validation.json

.venv/bin/python scripts/validate_manuscript_links.py \
  --document README.md \
  --output data/interim/readme_link_validation.json
```

Finally, run the release gate:

```bash
python3 scripts/validate_preliminary_scc_release.py \
  --output data/interim/preliminary_scc_release_validation.json
```

The release gate requires all 936 paired paths and 3,744 SCC values to have
passed their registered numerical/accounting checks; binds the manuscript,
Methods SI, Table 3, three figures, country/time decompositions, cross-track
brief, README, DOI registry, and link-audit hashes; verifies coefficient,
market, model, country and period support; and scans all tracked paths for
raw/intermediate data directories, credential files, credential-like
assignments, and wildfire-named artifacts. A passing gate keeps the total-SCC,
probabilistic-total-uncertainty, and causal drought/timing claim gates closed.
The registered release also requires 11 focused synthetic unit tests covering
quantity response, adaptation, national/global welfare algebra, and response-
panel construction; their bounded run peaked at 116,310,016 bytes.
