# Frozen protocol: published PEEPS monthly precipitation benchmark

## Purpose and claim boundary

Estimate a one-model, published-pattern benchmark for the marginal effect of a CO2 pulse through monthly precipitation timing and quantity. This benchmark is not a global probabilistic precipitation SCC, does not cover daily dry spells or extremes, and does not replace the multi-model quantity result.

## Frozen inputs

- PEEPS author-provided MPI-ESM1-2-HR SSP5-8.5 monthly precipitation slopes, one field per calendar month, in kg m-2 s-1 K-1.
- FAIR paired baseline and marginal-pulse global-mean temperature paths already used by the validated quantity bridge.
- GSWP3-W5E5 1981-2010 observed-climate monthly precipitation climatology on the existing Hultgren/GGCMI/MIRCA maize support.
- Published Hultgren et al. precipitation coefficients and the existing common-price maize value weights.

## Construction

1. Preserve rainfed and irrigated crop calendars separately. Build 29-harvest-year means of rainfall and rainfall squared for each crop-season month. Both moments are required because Hultgren's response contains monthly precipitation squared; squaring a climatological mean would be incorrect.
2. Map each crop cell to the nearest native PEEPS MPI grid cell, with circular longitude distance and explicit area-conservation and sentinel checks.
3. Convert each monthly PEEPS slope to mm K-1 using the number of days in the target year. Multiply it by the paired FAIR pulse-minus-baseline temperature path. Do not use PEEPS intercepts or extrapolated absolute rainfall levels.
4. Add the marginal monthly anomaly to the positive resident historical baseline. Recompute Hultgren's three phase precipitation sums and monthly-square sums exactly, then apply the published cell-specific effective coefficients.
5. Carry the resulting yield response through the same common-price market and GIVE agriculture-replacement machinery used by the quantity benchmark. Report the joint monthly-pattern response and, where algebraically possible, decompose it into annual-quantity and within-season redistribution components without adding overlapping effects.

## Pre-specified gates

- All source hashes, variable units, grids, and month identities must match frozen receipts.
- Historical monthly first and second moments must reproduce the existing phase totals and sums of squared-month totals to numerical tolerance before any response calculation.
- A shrinking-pulse check must show convergence of damages per pulse unit across at least three pulse sizes.
- All perturbed monthly rainfall levels must remain nonnegative on retained support; otherwise report the affected value/area and do not silently clip.
- Mapping sentinels and crop-area conservation must pass independently.
- The result remains a one-ESM structural benchmark. It may enter sensitivity analysis but not the central probabilistic SCC without multi-model validation.

## Interpretation

The benchmark answers whether published monthly climate-change patterns materially change the transported Hultgren maize response relative to proportional annual-rain scaling. It does not identify drought, daily sequencing, causal adaptation, or other crops. Null or unstable incremental timing effects will be reported rather than promoted.
