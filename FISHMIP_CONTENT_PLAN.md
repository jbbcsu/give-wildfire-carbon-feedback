# FishMIP `tc` acquisition and content-validation plan

Status: metadata pinned; one of four smoke NetCDF files acquired and validated;
no empirical welfare or SCC use authorized.

## Frozen acquisition stages

The exact 20-file catalogue is pinned in
`data/provenance/fishmip_isimip3b_tc_acquisition_plan.csv`. The first content
smoke is selected without inspecting outcomes: BOATS and EcoOcean, one common
climate forcing (GFDL-ESM4), and the historical plus SSP1-2.6 files for each
ecosystem model. This is four files and 513,826,771 catalogue bytes
(approximately 0.479 GiB). It tests both ecosystem-model conventions and one
historical/future join while bounding the initial transfer.

The other 16 files (2,071,639,668 catalogue bytes) remain
`deferred_full_matrix`. They are not acquired until every smoke file passes
checksum and content validation. This staging is an engineering decision, not
scenario or model selection for inference. SSP1-2.6 is not treated as a
marginal-CO2 counterfactual, and GFDL-ESM4 is not promoted above IPSL-CM6A-LR.

The first complete-file check passed for BOATS/GFDL-ESM4 historical
(`1950--2014`, 90,012,681 bytes). The local SHA-512 equals the plan; the file
has 780 contiguous `360_day` monthly indices, a 180 by 360 global 1-degree
grid, `tc` units `g m-2`, a stable missing mask, no negative values, and
separate finite/missing/zero counts. The remaining BOATS future and both
EcoOcean files are still required before the four-file smoke or any
historical/future join is considered passed.

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

The four-file smoke is promoted only on a machine-readable pass for every
check. Failure leaves the other 16 files unacquired and records the exact file,
field, and reason. After a pass, the full matrix repeats the same checks and
also requires complete BOATS/EcoOcean by GFDL-ESM4/IPSL-CM6A-LR by registered
experiment coverage.

## Scientific boundary

This plan can validate a biophysical scenario benchmark only. The FishMIP
scenario files do not supply a same-realization baseline/one-ton-pulse pair,
and `tc` is total catch density rather than consumer or producer surplus.
Neither content validation nor scenario contrasts clear the welfare,
matched-pulse, overlap, GIVE-integration, or SCC gates in `MODEL_CONTRACT.md`.
