# U.S. terminal prediction by state: post-result composition check

This is the fixed-forecast composition diagnostic registered in
`US_COUNTY_AVERAGE_STATE_COMPOSITION_DIAGNOSTIC_20260916.md` **after** the
national 2020--2025 scores were inspected. The 2017 Census <=10% low-
irrigation-share selector and all-practice NASS yields are unchanged; these
are not directly observed rainfed yields. Historical 1981--2019 county-FE
fits reproduce the original 2020--2025 quantity/temperature and joint
rain-pattern RMSEs to `1e-12` before the state decomposition. Positive
differences below mean lower log-yield forecast RMSE after adding the joint
wet-day, dry-spell, Rx5day and stage-share group.

| Crop | States / terminal rows | States favoring pattern | States with >=30 rows and >=3 years favoring pattern | Pooled quantity-minus-pattern RMSE | Equal-state difference | Range after omitting one state, fixed forecasts |
|---|---:|---:|---:|---:|---:|---:|
| Corn grain | 26 / 2,086 | 13 / 26 | 11 / 19 | +0.000670 | +0.000063 | −0.000177 to +0.001347 |
| Soybeans | 28 / 1,989 | 18 / 28 | 14 / 18 | +0.007659 | +0.008119 | +0.005893 to +0.009086 |

The soybean pooled gain is **not driven by any one state** on this fixed-
forecast omission measure; even its smallest leave-one-state-out gain is
positive. It is nonetheless heterogeneous: North Dakota (99 rows across
six years) worsens by 0.01723 RMSE points, and ten of 28 soybean states
do not favor the pattern group. Ten soybean and seven corn states have
fewer than 30 terminal rows or fewer than three represented years; their
individual signs are descriptive only. Corn's tiny pooled gain becomes
negative after at least one single-state omission and its equal-state
gain is effectively zero. Neither crop supports a universal state-level
timing benefit.

The omission calculation does **not** refit models or hold a state out of
training: it only removes that state's terminal forecast errors from the
pooled score. It is therefore a sensitivity to score composition, not a
geographic transfer validation. All states, including adverse and small
states, remain in the ignored full result ledger. No new predictor, sample
screen or uncertainty interval was chosen after seeing this decomposition.
The earlier conditional state bootstrap still omits time-block and model-
selection uncertainty. Forecast rankings do not isolate precipitation
causally from heat, irrigation, CO2, adaptation or management; these results
cannot be transported into global crop welfare or GIVE's SCC.

Reproduction: `scripts/evaluate_us_county_average_state_composition.py`
and independent grouped-normal-equation reconstruction
`scripts/validate_us_county_average_state_composition.py`. The validator
passes **498** count, state-partition, sum-of-squared-error, RMSE,
equal-state and leave-one-out checks against the exact source panel. The
small fixed-effect matrix products now use explicit finite-checked row sums
to avoid spurious floating-point status warnings from the local BLAS build.
The full chain was rerun with pandas future warnings promoted to errors;
exact original aggregate parity and the independently coded normal-equation
check both pass without warnings. Workers sampled 151.8/145.5 MiB group RSS
and remained under 512 MiB memory, 64 MiB owned-output and 130 GiB free-disk
guards. Raw panel and row-level forecasts remain ignored.

SHA-256 of ignored result JSON:
`bfb3477d9ff7403c69b961b572d329d73216567634f9b44105e5318656850e3b`.
SHA-256 of ignored independent validation JSON:
`9551b415b29bea2d69848abe75759125483d3e69a8e3542d6c4974ff2f7fc4eb`.
