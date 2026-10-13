# U.S. rainfed-maize future SPEI exposure, 2092--2099

## Result

The outcome-blind U.S. subset of the validated five-ESM by three-SSP drought
matrix passes independent aggregation validation. The fixed support contains
1,897 uniquely U.S.-assigned half-degree rainfed maize cells and 24,772,462.73
ha. All 15 model--scenario cases, 1,800 annual window/scale summaries, 150
named-model contrasts, and 30 ensemble summaries are complete.

For the prespecified primary exposure, rainfed crop-season SPEI-3, every named
model is drier under each higher-forcing scenario than under the same model's
SSP1-2.6 path:

| Contrast | GFDL | IPSL | MPI | MRI | UKESM | Equal-model mean | Median | Model range | SD | Negative |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| SSP3-7.0 minus SSP1-2.6 | -0.700 | -0.228 | -0.632 | -0.222 | -0.424 | -0.441 | -0.424 | [-0.700, -0.222] | 0.199 | 5/5 |
| SSP5-8.5 minus SSP1-2.6 | -1.175 | -1.493 | -1.055 | -0.187 | -0.421 | -0.866 | -1.055 | [-1.493, -0.187] | 0.486 | 5/5 |

Negative values mean lower standardized precipitation-minus-reference-ET0
balance. The named-model spread is material and is retained rather than hidden
behind the mean. It is neither a confidence interval nor a probability
distribution. These SSP contrasts combine forcing differences and internal
variability and are scenario exposures, not anthropogenic attribution.

## Scientific boundary

This completes a U.S.-focused future **SPEI exposure benchmark**, not the
climate-to-NASS-yield chain. The existing validated non-irrigated corn response
is a county-level NOAA PDSI coefficient, whereas this exposure uses
half-degree, crop-area-weighted SPEI and a global GGCMI calendar. Multiplying
the two would change index, scale, spatial support, calendar, and weather
source at once.

Accordingly, the bridge to the NASS response, future yield projection, causal
attribution, damage, and SCC gates remain closed. The missing bridge is a
historical source-consistent SPEI panel on the exact NASS county/calendar
support that passes the already frozen geographic and terminal validation,
followed by a future aggregation to those same counties. Direct rainfall and
SPEI remain competing alternatives and cannot be added.

## Validation and resources

Independent code recomputed all 1,800 annual records and every named-model and
ensemble contrast in 9,360 checks. The maximum numerical discrepancy was
`1.15e-14`. The builder peaked at 372,375,552 bytes (355.13 MiB) sampled
process-group RSS; validation peaked at 256,688,128 bytes (244.80 MiB). Both
completed under the 512 MiB cap.

The executable contract, builder, independent validator, synthetic tests, and
machine-readable evidence are recorded in
`data/provenance/us_future_spei_exposure_20261013.json`. The ignored detailed
result and validation artifacts are under
`data/interim/us_future_spei_exposure_v2_20261013/`.
