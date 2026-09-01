# Preregistered structural feature-response candidate

The adverse affine GMST surface is not promoted. The next outcome-blind
candidate is a ridge-regularized continuous pathway model fitted separately to
each daily-derived crop feature within exact crop, irrigation, and grid cells.
Its global backbone uses same-realization GMST anomaly, one-year GMST change,
years since 2020, a quadratic GMST term, and GMST interactions with recent
change and time. ESM intercept, GMST, and recent-change deviations are
partially pooled. A held-out ESM receives the global backbone only.

Scenario identity is forbidden as a predictor. Pathway dependence must be
represented by continuous climate-state terms that are available on both ESM
training paths and matched GIVE/FAIR baseline and pulse paths. GMST changes
must use the previous year from the same realization and cannot bridge the
large gaps between the bounded early-, mid-, and end-century blocks.

The six ridge penalties are selected inside each training fold; outer
whole-ESM and whole-scenario holdouts cannot influence selection or
standardization. Promotion requires every feature family to pass both holdout
types, a maximum RMSE ratio no worse than the cell-mean benchmark, a median
ratio no greater than 0.995, complete actual-FAIR baseline/pulse support, exact
zero-pulse and pre-divergence identity, and decreasing-pulse convergence. A
human review remains mandatory.

The contract is `config/isimip3b_structural_feature_response_v1.toml`, its
validator is `scripts/validate_isimip3b_structural_feature_response_contract.py`,
and the receipt is
`data/provenance/isimip3b_structural_feature_response_contract_20260901.json`.
No real candidate fit has been run. The contract authorizes neither a climate
response, crop-yield response, damages, nor SCC use. MESMER-M-TP plus a
published daily generator remains the fallback only.
