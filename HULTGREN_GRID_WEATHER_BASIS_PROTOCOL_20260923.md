# Protocol: bounded Hultgren maize weather-basis transport

Date frozen: 2026-09-23

## Purpose and claim boundary

This step constructs the published Hultgren et al. maize weather covariates on an alternative 0.5-degree daily climate product. It is an engineering and transformation step needed to transport the published response function to future climate scenarios. It is **not** a reproduction of the authors' historical GMFD/SAGE administrative-region inputs, an estimated future yield response, a monetary damage estimate, or an SCC result.

The unresolved reproduction inputs remain the primitive GMFD daily fields and the authors' within-region SAGE `anycrop` pixel weights. The public repository audit and author-data request record those gaps separately.

## Frozen transformation

For each grid cell, crop regime, and physical harvest year:

1. Use the GGCMI Phase 3 maize calendar for the matching rainfed or irrigated regime.
2. Convert planting and maturity day of year to the whole-month convention in the published replication code.
3. Retain positive MIRCA 2000 maize area cells whose inclusive crop season is 4–10 months. Report both excluded cell count and excluded crop area; fail if eligible support falls below 95% of calendar-matched positive area.
4. Stream daily precipitation, minimum temperature, and maximum temperature one day at a time. Require a complete daily chronology, fixed 360 by 720 grid, documented units, nonnegative precipitation, and maximum temperature not materially below minimum temperature.
5. Convert precipitation flux to millimetres per day and sum to calendar-month totals.
6. Apply the Snyder single-sine method to daily minimum and maximum temperature. Define GDD as degree-days from 8–31 °C and KDD as degree-days above 31 °C.
7. Construct the three published precipitation phases: month 1; months 2–4; and month 5 through harvest. For each phase retain the sum of monthly precipitation and the sum of squared monthly precipitation.
8. Complete every nonlinear transformation at the grid-cell and irrigation-regime level before later spatial aggregation. This order avoids the nonlinear aggregation error demonstrated in the Iroquois diagnostics.

Rainfed and irrigated outputs remain separate. No implicit mixing or adaptation assumption is made at this stage.

## Year convention

Outputs use the physical harvest year. A cross-year crop season therefore draws late months from the preceding calendar year and early months from the harvest year. This is coherent for gridded future projections but is distinct from the India-specific regression reporting-year rule in the historical replication package. No historical outcome panel is joined in this step.

The requested source period must contain every calendar month needed by each requested harvest year. In practice, a cross-year first harvest requires the preceding source year.

## Inputs and provenance

- Daily `pr`, `tasmin`, and `tasmax` from one internally consistent ISIMIP3b climate-model/scenario/window combination.
- GGCMI Phase 3 maize calendars: `mai_noirr` for rainfed and `mai_firr` for irrigated.
- MIRCA-OS v2 maize harvested-area rasters for matching rainfed and irrigated regimes.

The run receipt records byte size and SHA-512 for every daily climate file, SHA-256 for the support inputs and output, the exact source and harvest periods, support exclusions, missing daily triplets, minimum Tmax-minus-Tmin margin, output schema, implementation hash, and elapsed time. Raw data remain ignored by Git.

## Memory and disk safeguards

The implementation reads one global daily field at a time and immediately selects crop-support cells. It stores only monthly support-cell arrays. Output is written one harvest year per Parquet row group rather than assembling all years as Python dictionaries in memory. Runs remain subject to the project limits: one numerical worker, a 512 MiB worker target, 64 MiB captured-output ceiling, and at least 130 GiB free disk.

Future `tasmin` and `tasmax` pairs will be reacquired one model-scenario pair at a time using the frozen URLs, byte counts, and hashes in `data/provenance/isimip3b_five_esm_late_drought_extrema_20260921.json`. After a basis output passes independent validation, raw extrema may be removed only with a provenance receipt; precipitation files already used by other work are preserved.

## Validation gates

Before scientific use, each output must pass:

- scalar-versus-vectorized Snyder degree-day equality tests;
- same-year and cross-year crop-season arithmetic tests;
- complete expected row count and finite feature checks;
- source identity and chronology checks;
- an independent summary audit by regime, latitude band, and scenario;
- selected cell-level recomputation from raw daily inputs;
- comparison with the recovered Iroquois benchmark where periods/products permit;
- sensitivity to calendar and spatial weighting choices.

Only after those gates may the grid bases be aggregated to author impact regions, combined using explicit rainfed/irrigated weights, passed through the published response function, and compared across climate scenarios. Monetary damages and GIVE/SCC integration require additional separately documented validation gates.

## Initial execution order

1. Run one ESM under SSP1-2.6 and SSP5-8.5 for the same late-century window, separately for rainfed and irrigated maize.
2. Validate transformation arithmetic and generate a within-model scenario contrast.
3. Expand to the remaining pre-specified ESM/scenario matrix only after the first pair passes.
4. Build the impact-region aggregation and moderator join, preserving a grid-level audit trail.
5. Apply the published response only after the complete feature contract and aggregation order are independently verified.

The first scenario contrast is an alternative-product transport diagnostic, not a causal estimate of the precipitation effect of climate change and not an SCC result.
