# Future SPEI maps cleanly to maize and soybean crop windows

## Result

The validated GFDL monthly drought pilot now has a complete crop-calendar
allocation for 557 fixed maize/soy crop-cell pairs, six harvest years, three
SSPs, five crop windows, three SPEI scales, and both positive-share irrigation
regimes. All 150,390 combined crop-window rows and all 163,350 regime rows are
complete. Independent validation passed 1,066,451 checks with zero allocation
or summary error, including 24 fixed samples traced directly to the monthly
cube and raw crop-calendar dates.

This removes a technical gap between projected drought indices and the
agricultural estimand. It does not estimate a future yield effect, damage, or
SCC.

## Construction

The allocator uses the 512-cell GFDL boundary cube validated in the preceding
stage and the 557 maize/soy pairs that occur in its frozen crop-support
partition (324 maize and 233 soybean). Harvest years 2015--2020 use unchanged
GGCMI Phase 3 `2015soc` rainfed and irrigated calendars. Each positive-share
regime is computed before aggregation with fixed MIRCA-OS v2 shares. No outcome,
future weather, or fitted response changes a calendar or irrigation weight.

The retained endpoints are full season, three proportional stages, and the 90
days before planting at 1-, 3-, and 6-month SPEI scales. Monthly values are
day-weighted over their exact overlap with each crop window; the month-end
sensitivity remains separate.

## Descriptive diagnostics only

The unweighted crop-season means below summarize the selected 512-cell pilot;
they are not global or production-weighted drought incidence:

| Crop | Scenario | SPEI-1 | SPEI-3 | SPEI-6 |
|---|---|---:|---:|---:|
| Maize | SSP1-2.6 | -0.246 | -0.348 | -0.282 |
| Maize | SSP3-7.0 | -0.267 | -0.346 | -0.218 |
| Maize | SSP5-8.5 | -0.131 | -0.093 | -0.120 |
| Soybean | SSP1-2.6 | -0.184 | -0.212 | -0.242 |
| Soybean | SSP3-7.0 | -0.197 | -0.246 | -0.187 |
| Soybean | SSP5-8.5 | -0.278 | -0.333 | -0.424 |

Maize and soybean do not share the same means because their crop cells,
calendars, stage dates, and irrigation weights differ. The scenarios also do
not rank consistently. That is evidence that the code is retaining realized
spatial and seasonal structure, not evidence that one forcing pathway causes a
specific drought response over this short period.

## Resource and integrity checks

The builder took 2.53 seconds, peaked at 353,173,504 bytes sampled process-group
RSS, and added 7,402,757 bytes. The validator took 4.55 seconds and peaked at
274,907,136 bytes. Both stayed below the 512 MiB RAM, 64 MiB output, and 130
GiB free-space safeguards. Raw climate and crop data were unchanged.

The validator checked unique keys, exact support, status completeness,
irrigation-share closure, regime-to-combined SPEI and day-count closure, tail
clip propagation, all 90 saved descriptive aggregates, and raw-calendar/cube
reconstruction for fixed samples. The machine-readable receipt is
`data/provenance/gfdl_future_spei_crop_windows_20260919.json`.

## Remaining scientific gates

The next substantive gate is not more feature engineering on this short
realization. It is extending the same construction to the full multi-ESM
later-century matrix, then applying only drought-response families that survive
the prespecified geographic and terminal yield tests. Direct precipitation and
drought-index response families remain competing alternatives, never additive
damage terms. A paired marginal climate path is still required for SCC.
