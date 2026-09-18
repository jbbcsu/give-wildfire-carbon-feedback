# Frozen direct-baseline plus published-anomaly physicality check

Registered September 18, 2026 before calculating any anchored scores. This
is a post-result, **same-source in-sample** diagnostic. It asks whether the
published monthly PEEPS *changes* can be added to a nonnegative direct-MPI
2015 monthly baseline without invalid negative rainfall in 2100. It does
not create a globally applicable published emulator, because an observed
2015 realization is supplied as a perfect local anchor here.

Use the SHA-256-bound arrays and same 30,821 positive-area MIRCA2000
rainfed-maize nearest centers specified in
`PEEPS_MPI_CHANGE_DECOMPOSITION_PROTOCOL_20260918.md`. For each month and
center define `anchored_2100 = direct_2015 + (PEEPS_2100 - PEEPS_2015)`.
Do not clip, floor, impute, smooth, change the baseline year, rescale slopes,
or remove a location because a predicted value is negative. The naive
no-change comparator is `direct_2015`. The target is direct two-member
mean `direct_2100` at identical month/center keys.

Report area fraction with at least one negative anchored month, count of
negative month-center values, minimum anchored rainfall, area-weighted
annual bias and spatial annual RMSE for anchored and no-change predictors,
and a 12-month-by-center RMSE for each predictor. On the common subset where
anchored and direct 2100 have nonnegative months and strictly positive
annual totals, report area coverage and weighted mean monthly-share
total-variation distance for anchored and no-change; never treat a
restricted-support score as an all-area result. All-area annual and monthly
errors retain negative predictions. No parameter fitting or model selection.

Use independent scalar arithmetic to reconstruct primary metrics. A
negative anchored monthly value blocks forcing promotion, regardless of
whether its aggregate error improves. Even if all values are positive,
this in-sample source-matched comparison cannot establish scenario/model
holdout performance, crop-calendar timing, daily extremes, yields, damages,
or SCC. Run under 512 MiB sampled RSS, 64 MiB owned output and 130 GiB
free-disk gates; preserve failed attempts and audit receipts.
