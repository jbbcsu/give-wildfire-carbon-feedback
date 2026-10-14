# U.S. SPEI bridge support extension

## Historical result

The 11 half-degree cells missing from the frozen 361-county non-irrigated corn
support audit were constructed from the resident, fully SHA-512-verified
ISIMIP3a GSWP3-W5E5 v1.3 archive. The build used daily precipitation and
Hargreaves--Samani reference evapotranspiration, calendar-month generalized
log-logistic unbiased-PWM fits calibrated only on 1982--2011, and frozen
SPEI-1/3/6 application through 2019.

The output contains 468 months for all 11 cells. All 396 cell-by-scale-by-month
fits are valid. Monthly precipitation, evapotranspiration, and water balance
have no missing values; there are no probability-tail clips, imputations,
post-2011 calibration values, or crop outcomes. The expected leading rolling
months account for 22 missing SPEI-3 values and 55 missing SPEI-6 values.

The bounded builder peaked at 157,843,456 bytes RSS. Independent validation
passed 42 checks, reconstructed every stored array with zero numerical
difference, and reproduced four raw-source month sentinels exactly. Its peak
RSS was 149,012,480 bytes.

## Future queue and completed cases

The future queue freezes 15 model-scenario cases and 30 exact `tasmin`/`tasmax`
objects from the existing CC0 ISIMIP3b registry. Total transfer volume is
62,129,453,968 bytes, but the protocol permits only one case resident at a
time. Each case must be reduced to the 11 cells, independently validated, and
only then may its two reacquirable extrema objects be evicted. Existing
precipitation and mean-temperature archives are retained.

Network access was available, so the first case, GFDL-ESM4 SSP1-2.6, was run.
Both extrema objects passed their registered byte counts and SHA-512 hashes.
The reduced output contains 120 months for all 11 cells, with no incomplete
cell-months, missing triplets, or global temperature-order violations. The
build peaked at 184,451,072 bytes RSS. Independent validation passed 1,206
checks; the maximum SPEI difference from the scalar frozen-parameter
reconstruction was 7.363518683689563e-09. The validator peaked at 132,775,936
bytes RSS.

After validation, the two extrema files (4,140,781,657 bytes) were deleted
under a receipt containing their URLs, byte counts, SHA-512 identities,
dataset/file IDs, DOI, and CC0 rights.

The second case, GFDL-ESM4 SSP3-7.0, also passed. Its `tasmin` acquisition was
interrupted after repeated DNS, timeout, and connection-reset errors; the
preserved partial was resumed under a fresh receipt and ultimately matched the
frozen 2,070,538,843-byte SHA-512 identity. The 2,062,753,985-byte `tasmax`
object matched independently on its first bounded acquisition. Both
acquisitions peaked at 30,654,464 bytes RSS.

The SSP3-7.0 reduced output contains 120 months for all 11 cells, again with no
incomplete cell-months, missing triplets, or global temperature-order
violations under the registered tolerance. The build peaked at 175,996,928
bytes RSS. Independent validation passed 1,206 checks; its maximum SPEI
difference was 7.363518683689563e-09, and its peak RSS was 119,980,032 bytes.
After validation and a final raw-hash check, the two reacquirable extrema files
(4,133,292,828 bytes) were deleted. Thirteen future cases remain; the next
frozen case is GFDL-ESM4 SSP5-8.5, which was not started in this run.

## Interpretation and gates

This closes the historical raw-cell construction step but not the full bridge.
Exact future support still requires the remaining 13 cases, followed by a
fresh county-coverage audit, common county weights, NASS-calendar aggregation,
and independent panel validation. No yield value was read and no response was
fit. County-panel, projection, causal, damage, and SCC gates remain closed.
Direct rainfall and SPEI remain competing moisture families and cannot be
stacked or added.

## Reproducibility files

- cell inventory: `config/us_spei_bridge_missing_cells_v1.csv`;
- historical builder/validator/tests:
  `scripts/build_us_spei_bridge_historical_cells.py`,
  `scripts/validate_us_spei_bridge_historical_cells.py`, and
  `scripts/test_build_us_spei_bridge_historical_cells.py`;
- deterministic future queue:
  `data/provenance/us_spei_bridge_future_11_cell_queue_20261013.json`;
- future queue/acquisition/build/validation code:
  `scripts/plan_us_spei_bridge_future_queue.py`,
  `scripts/acquire_us_spei_bridge_future_extrema.py`,
  `scripts/build_us_spei_bridge_future_case.py`, and
  `scripts/validate_us_spei_bridge_future_case.py`;
- future queue tests: `scripts/test_us_spei_bridge_future_queue.py`;
- consolidated provenance:
  `data/provenance/us_spei_bridge_extension_20261013.json`;
- completed-case eviction receipts:
  `data/provenance/gfdl-esm4_ssp126_us_spei_bridge_extrema_eviction_20261013.json`
  and
  `data/provenance/gfdl-esm4_ssp370_us_spei_bridge_extrema_eviction_20261014.json`.

Detailed climate outputs and resource receipts remain under ignored
`data/interim/us_county/us_spei_bridge_*` paths.
