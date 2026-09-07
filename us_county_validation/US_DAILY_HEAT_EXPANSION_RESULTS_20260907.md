# National direct-practice daily heat expansion and sensitivity

The validated daily-Tmax basis covers all 11,861 corn/soybean county/crop/year
keys in the existing 1981--2019 direct-practice weather support: 7,016 corn
keys, 4,845 soybean keys, 419 counties and 39 years. All 149 deterministic
county-batch checkpoints reconcile source keys, calendars, stage sums, linear
Tmax means, monthly content identities and polygon weights. The original
Cuming County pilot reconciles across all 64 tested values.

The full-year implementation was not safe: 1983 approached the limit at
1,002,848,256 bytes sampled RSS and the monitor killed 1984 at 1,082,408,960
bytes. The frozen resource amendment limited checkpoints to 64 sorted
counties. All 149 amended checkpoints completed; the largest peak was
475,119,616 bytes (453.1 MiB). Total new storage remained below 64 MiB.

Median seasonal cell-first exposure for corn is 234.21 C-days above 29 C and
170.79 C-days above 30 C; corresponding above-threshold counts are 69.09 and
57.45 weighted days. Soybean medians are 282.87 and 208.59 C-days, with 78.21
and 67.03 weighted days. These selected-support summaries are not crop damage.

## Predictive sensitivity

The frozen comparison reproduces the original 120 aggregate metrics exactly,
then adds six common controls at one threshold at a time: three stage heat-
exceedance sums and three stage above-threshold counts. Both the 29 C and 30 C
variants remove the original diagnostic rainfall-distribution promotion for
irrigated and non-irrigated soybean. Corn continues to fail. With 29 C
controls, mean leave-state-out distribution improvements are 0.000783 for
irrigated soybean and 0.005615 for non-irrigated soybean; with 30 C controls
they are 0.000586 and 0.007463. At least one state is below its fixed
materiality floor in every crop/practice stratum.

For non-irrigated corn, the distribution extension still improves mean
leave-state-out RMSE (0.007217 at 29 C; 0.007502 at 30 C) and terminal RMSE
(0.030502; 0.029405), but the uniform-state rule fails. These are reused,
exploratory predictive splits, not causal response estimates or independent
confirmation. No coefficient, model promotion, projection, damage or SCC is
authorized.
