# September 19 precipitation-SCC reproducibility index

This index binds the reviewed September 19 evidence package to its Git commits,
protocols, results, code, and machine-readable receipts. It does not supersede
the interpretation gates in the individual artifacts.

## Climate-to-drought engineering

Commit `d0f6873` maps the validated GFDL monthly SPEI boundary pilot to fixed
maize and soybean crop windows.

- Protocol: `GFDL_FUTURE_SPEI_CROP_WINDOW_PROTOCOL_20260919.md`
- Results: `GFDL_FUTURE_SPEI_CROP_WINDOW_RESULTS_20260919.md`
- Builder/validator: `scripts/build_gfdl_future_spei_crop_windows.py` and
  `scripts/validate_gfdl_future_spei_crop_windows.py`
- Receipt: `data/provenance/gfdl_future_spei_crop_windows_20260919.json`
- Validation: 1,066,451 checks; 163,350 regime rows and 150,390 combined rows.
- Interpretation: exposure engineering only; no yield, damage, adaptation, or
  SCC result.

Commit `9ea1f47` audits the published Araujo global SPI/SPEI archive without
downloading payload data.

- Audit: `PUBLISHED_DROUGHT_PRODUCT_ACCESS_AUDIT_20260919.md`
- Receipt: `data/provenance/published_drought_product_access_20260919.json`
- Finding: the five overlapping GIVE climate-model archives total 149.18 GiB;
  acquisition remains deferred pending a provider subset or safe external
  storage route.

## Structural crop-and-welfare benchmark

Commit `a38b549` constructs the country-market structural maize benchmark.

- Protocol/results: `STRUCTURAL_WELFARE_BENCHMARK_PROTOCOL_20260919.md` and
  `STRUCTURAL_WELFARE_BENCHMARK_RESULTS_20260919.md`
- Builder/validator: `scripts/build_structural_welfare_benchmark.py` and
  `scripts/validate_structural_welfare_benchmark.py`
- Receipt: `data/provenance/structural_welfare_benchmark_20260919.json`

Commit `5ca6b67` compares country and global maize markets.

- Protocol/results: `GLOBAL_MARKET_WELFARE_SENSITIVITY_PROTOCOL_20260919.md`
  and `GLOBAL_MARKET_WELFARE_SENSITIVITY_RESULTS_20260919.md`
- Builder/validator: `scripts/build_global_market_welfare_sensitivity.py` and
  `scripts/validate_global_market_welfare_sensitivity.py`
- Receipt: `data/provenance/global_market_welfare_sensitivity_20260919.json`
- Interpretation: market geography is material when an inelastic country
  market interacts with an extreme local crop-model response.

Commit `8fcd60c` performs the preferred four-corner welfare attribution.

- Protocol/results: `FOUR_CORNER_WELFARE_ATTRIBUTION_PROTOCOL_20260919.md` and
  `FOUR_CORNER_WELFARE_ATTRIBUTION_RESULTS_20260919.md`
- Builder/validator: `scripts/build_four_corner_welfare_attribution.py` and
  `scripts/validate_four_corner_welfare_attribution.py`
- Receipt: `data/provenance/four_corner_welfare_attribution_20260919.json`
- Validation: 96 registered cases, 84 mechanically admissible cases, and 3,081
  checks.
- Interpretation: quantity-only structural sensitivity; temperature dominates
  the joint maize loss, while precipitation is beneficial in admissible
  SSP1-2.6 cases and a small loss in admissible SSP5-8.5 cases. This is not the
  distribution-aware agriculture replacement.

## Support sensitivity

Commit `ade68f7` registers one fixed all-case positive crop-support mask.

- Protocol/results: `FIXED_POSITIVE_CROP_SUPPORT_PROTOCOL_20260919.md` and
  `FIXED_POSITIVE_CROP_SUPPORT_RESULTS_20260919.md`
- Builder/validator: `scripts/audit_fixed_positive_crop_support.py` and
  `scripts/validate_fixed_positive_crop_support.py`
- Receipt: `data/provenance/fixed_positive_crop_support_20260919.json`
- Coverage: excludes 186 cell/regime locations but only 0.01751% of common
  production and 0.02254% of covered value.

Commit `42cb375` repeats four-corner attribution on that fixed partial support.

- Protocol/results: `FIXED_POSITIVE_WELFARE_SENSITIVITY_PROTOCOL_20260919.md`
  and `FIXED_POSITIVE_WELFARE_SENSITIVITY_RESULTS_20260919.md`
- Builder/validator: `scripts/build_fixed_positive_welfare_sensitivity.py` and
  `scripts/validate_fixed_positive_welfare_sensitivity.py`
- Receipt: `data/provenance/fixed_positive_welfare_sensitivity_20260919.json`
- Validation: 96 cases and 1,929 checks.
- Interpretation: fixed partial-support sensitivity only; it neither repairs
  the crop model nor authorizes a formerly inadmissible case.

## Evidence synthesis and manuscript text

Commit `340ca10` supplies the evidence hierarchy in
`PRECIPITATION_DAMAGE_EVIDENCE_SYNTHESIS_20260919.md`: direct daily climate
evidence, U.S. outcome validation, global outcome validation, and the structural
benchmark remain distinct.

Commit `08d4fc7` adds
`manuscript/SEPTEMBER19_STRUCTURAL_BENCHMARK_INSERT.md`. Commit `dad4caa` adds
`manuscript/SEPTEMBER19_METHODS_SI_INSERT.md`. These are clean merge candidates
because the pre-existing main manuscript and Methods SI working files contain
unrelated uncommitted edits.

## Release status

No artifact in this index authorizes an empirical damage function, replacement
of GIVE agriculture, a GIVE damage export, or an SCC result. The open critical
path is a global precipitation-response family that passes untouched validation
and preserves total-rainfall, timing/extremes, drought, temperature, irrigation,
adaptation, and double-counting boundaries. Matched baseline and emissions-pulse
annual climate paths are then required before SCC integration.
