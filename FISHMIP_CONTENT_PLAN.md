# FishMIP `tc` acquisition and content-validation plan

Status: metadata pinned; all 12 historical/SSP1-2.6/SSP5-8.5 scenario-matrix
NetCDF files acquired and validated; no matched-pulse, welfare, or SCC use
authorized.

## Frozen acquisition stages

The exact 20-file catalogue is pinned in
`data/provenance/fishmip_isimip3b_tc_acquisition_plan.csv`. The first content
smoke is selected without inspecting outcomes: BOATS and EcoOcean, one common
climate forcing (GFDL-ESM4), and the historical plus SSP1-2.6 files for each
ecosystem model. This is four files and 513,826,771 catalogue bytes
(approximately 0.479 GiB). It tests both ecosystem-model conventions and one
historical/future join while bounding the initial transfer.

After the four-file smoke passed, eight additional historical/SSP1-2.6/
SSP5-8.5 files were acquired under the predeclared full-matrix stage. The 12
scenario files now cover both forcings and ecosystem models. The eight
preindustrial-control files remain deferred. This staging is an engineering
decision, not scenario or model selection for inference. Neither SSP is
treated as a marginal-CO2 counterfactual, and neither climate forcing or
ecosystem model is promoted above another.

The complete four-file check passed. Both BOATS files use contiguous monthly
indices under `360_day`; both EcoOcean files use exact month-start day offsets
under `365_day`. Within each model, historical and SSP1-2.6 fields have the
same 180 by 360 global grid and time-stable finite/missing mask and join
without a missing or duplicated month. All four local byte counts and SHA-512
values equal the plan, `tc` remains `g m-2`, and no negative value occurs.
EcoOcean has no genuine zeros in either file, whereas BOATS does; the validator
therefore preserves missing-versus-zero semantics rather than imposing a
shared convention.

The cross-model grids are identical but their finite masks are not. The
historical masks contain 41,029 common finite cells, 47 BOATS-only cells, and
2,303 EcoOcean-only cells. Cross-model summaries must carry model-specific and
common-support flags and must not fill unsupported cells with zero. This is a
validated content limitation, not a reason to select one ecosystem model.

The registered scenario benchmark now exercises that rule over the complete
1950--2100 historical/SSP1-2.6 paths. Relative to each model's own 2005--2014
common-support reference, 2081--2090 mean `tc` density is 35.62% lower for
BOATS and 24.40% lower for EcoOcean. Their 2021--2030 changes are -26.04% and
+0.27%, respectively, so neither a common short-run response nor a preferred
model is inferred. See `FISHMIP_SCENARIO_BENCHMARK.md`. These are scenario
diagnostics, not marginal-pulse or welfare effects.

Before any download, refresh the catalogue response and require an exact match:

```bash
python3 scripts/validate_fishmip_catalog.py catalogue.json \
  --plan data/provenance/fishmip_isimip3b_tc_acquisition_plan.csv
```

Any changed ID, version, URL, byte size, SHA-512, license, year range, matrix
member, or acquisition-stage membership stops acquisition for review. Raw
files belong under ignored `data/raw/`; the plan does not authorize committing
them.

## Required smoke-file checks

Each file must pass all of the following before any numeric summary is used:

1. Local byte size and SHA-512 exactly match the pinned catalogue record.
2. A standards-compliant NetCDF reader opens the complete file; a header or
   partial range is not accepted as a content check.
3. The data variable is `tc`; its dimensions, units, missing-value encoding,
   compression, chunking, coordinate names, calendar, and time units are
   recorded rather than assumed.
4. Decoded time is strictly increasing, unique, monthly with no gaps, and
   spans every month in the pinned filename interval (1950--2014 or
   2015--2100). Historical and future files must join without a gap or overlap.
5. Latitude and longitude coordinates are finite and unique, and their
   orientation, resolution, bounds, longitude convention, global coverage,
   and land/ocean mask are recorded. Grid equality is tested within each
   forcing and across ecosystem models; differing grids are reported and not
   silently coerced.
6. Fill/missing cells remain distinct from genuine zero catch. Counts of
   finite, missing, zero, and negative values and finite extrema are reported
   by file and year. Negative values are a review flag, not automatically
   clipped.
7. Shared historical and SSP1-2.6 months are checked for stable schema, grid,
   units, and missing-value conventions within each ecosystem model. No
   cross-model equality of values is expected.

The initial four-file smoke and the later eight-file scenario expansion have
machine-readable passes for every within-model file and historical/future join
check. The resulting historical/SSP1-2.6/SSP5-8.5 matrix is complete across
BOATS/EcoOcean and GFDL-ESM4/IPSL-CM6A-LR. The eight control files remain
deferred and are not needed for the bounded scenario diagnostic.

## Scientific boundary

This plan can validate a biophysical scenario benchmark only. The FishMIP
scenario files do not supply a same-realization baseline/one-ton-pulse pair,
and `tc` is total catch density rather than consumer or producer surplus.
Neither content validation nor scenario contrasts clear the welfare,
matched-pulse, overlap, GIVE-integration, or SCC gates in `MODEL_CONTRACT.md`.
