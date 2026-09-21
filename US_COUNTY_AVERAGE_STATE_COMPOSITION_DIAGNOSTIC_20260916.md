# Post-result U.S. state-composition diagnostic: fixed forecasts only

This diagnostic is registered **after** the 2020--2025 scores and irrigation,
PDSI, trend and weather-source sensitivities were seen. It cannot provide a
fresh holdout or select the primary model. Its narrow question is whether
soybean's observed pooled timing/extreme-rain predictive gain is concentrated
in one or a few states, and whether corn's near-null result hides opposite
state signs.

Use the exact 2017 Census <=10% crop-specific irrigation-share panel and
unchanged 1981--2019 county-FE/common-trend quantity-plus-temperature and
joint-pattern model definitions from
`US_COUNTY_AVERAGE_RESPONSE_PREANALYSIS_20260916.md`. Refit on identical
historical rows only to recover 2020--2025 row forecasts; require exact
parity with the original published aggregate scores before examining state
breakdowns. Do not alter terms, counties, years, support, calendar, weather
estimator or outcome. The NASS target is all-practice yield, not observed
rainfed yield.

For every state with scored rows, publish crop-specific row count, number of
terminal years, quantity and pattern log-yield RMSE, and the difference
`quantity RMSE - pattern RMSE` (positive favors patterns). Do not suppress
small or unfavorable states; flag states with fewer than 30 rows or fewer
than three years as descriptive only. Also report pooled and equal-state
RMSE differences, and the pooled difference after omitting each state in
turn **without refitting**. These are fixed-forecast composition checks, not
cross-state transport experiments or state-level causal estimates. A state
bootstrap is already in the primary report and is not repeated here.

The implementation must verify full state partition of all terminal rows,
identical forecast and outcome keys for both models, source SHA-256 and
exact published pooled-score parity. A separately coded validator must
reconstruct all state and leave-one-state-out scores from the same panel
using independent pandas/least-squares arithmetic; the validation is a
numerical check, not independent scientific evidence. Keep raw and row-level
outputs in ignored `data/interim/`, aggregate report only in Git. No
climate-change, global response, welfare or SCC result is authorized.
