# Conditional paired-loss sensitivity for the U.S. moisture diagnostic

## Status and boundary

This is a separate, validated sensitivity for the independently audited U.S.
corn/soy competing-moisture predictive diagnostic. It leaves the frozen point-
estimate protocol, its 120 aggregate metrics, and its distribution-promotion
rule and outcomes unchanged.

The interval is a paired empirical county-resampling sensitivity conditional
on the observed test support, the registered fitted models, and the registered
endpoint-purged splits. It is **not** refit or training-sample uncertainty,
model-selection uncertainty, a target-population confidence interval, or
causal, damage, welfare, or SCC uncertainty. It provides no p-value or
significance test.

The executable contract is
[`us_competing_moisture_paired_loss_uncertainty_v1.toml`](us_competing_moisture_paired_loss_uncertainty_v1.toml).
It SHA-256-binds the original protocol, builder, evaluator, validator, three
analysis tables, raw inputs and source receipts, point result, exact-validation
receipt, and independent-audit receipt. Any missing or changed artifact fails
closed before a sensitivity fit is used.

## Refit and bootstrap design

All 120 original crop/practice/model/split fits are recomputed in memory with
the hash-bound registered `numpy.linalg.lstsq` solver, relative SVD cutoff,
training-only scaling, year terms, and identical first-difference endpoint
purges. Every reconstructed aggregate metric must equal the frozen point result
exactly. Direct precipitation and PDSI remain mutually exclusive. Coefficients,
row predictions, row losses, and bootstrap draws are never serialized.

For each crop/practice stratum separately, the sensitivity reports:

1. pooled development OOF loss, where each row from an eligible leave-state-
   out test appears once with the score from its state-holdout fit;
2. the registered terminal same-county test;
3. the registered development precipitation-extreme test; and
4. state-specific development distribution-versus-quantity loss only when the
   state test has at least 30 occupied counties.

Each of 5,000 deterministic draws samples occupied counties uniformly with
replacement. Every relevant test row for a sampled county moves together, and
the same county multiplicities are applied to both models in a comparison.
The point loss remains equally weighted across test rows. The bounds are the
2.5th and 97.5th percentiles of candidate-minus-reference RMSE or MAE. Negative
differences favor the candidate. Every reported scope requires at least 30
counties and rejects a county holding more than 10% of test rows. Dependence
between counties is not modeled.

The four registered comparisons are quantity minus controls, distribution
minus quantity, seasonal PDSI minus quantity, and stage PDSI minus quantity.
No comparison changes or reapplies the frozen promotion gate. In particular,
the original development rule still fails for both corn practices and passes
for both soybean practices.

## Pooled conditional intervals

### Development leave-state-out OOF pool

| Crop/practice | Comparison | RMSE difference [interval] | MAE difference [interval] |
|---|---|---:|---:|
| corn, irrigated | quantity - controls | +0.001160 [+0.000809, +0.001488] | +0.000838 [+0.000603, +0.001085] |
| corn, irrigated | distribution - quantity | +0.000015 [-0.000908, +0.000960] | +0.001072 [+0.000213, +0.001884] |
| corn, irrigated | PDSI season - quantity | -0.000763 [-0.001089, -0.000433] | -0.000580 [-0.000818, -0.000342] |
| corn, irrigated | PDSI stage - quantity | +0.001124 [+0.000673, +0.001583] | +0.000909 [+0.000560, +0.001258] |
| corn, non-irrigated | quantity - controls | -0.020949 [-0.024336, -0.017408] | -0.015405 [-0.018620, -0.012190] |
| corn, non-irrigated | distribution - quantity | -0.006328 [-0.009102, -0.003455] | -0.003556 [-0.006074, -0.001099] |
| corn, non-irrigated | PDSI season - quantity | -0.016327 [-0.019492, -0.013270] | -0.008213 [-0.011070, -0.005418] |
| corn, non-irrigated | PDSI stage - quantity | -0.019492 [-0.023184, -0.016027] | -0.010426 [-0.013784, -0.007214] |
| soybeans, irrigated | quantity - controls | +0.000807 [-0.000124, +0.001765] | +0.001727 [+0.000957, +0.002487] |
| soybeans, irrigated | distribution - quantity | -0.003794 [-0.004947, -0.002646] | -0.003751 [-0.004822, -0.002679] |
| soybeans, irrigated | PDSI season - quantity | +0.000410 [-0.000261, +0.001085] | -0.000096 [-0.000683, +0.000484] |
| soybeans, irrigated | PDSI stage - quantity | +0.002204 [+0.001510, +0.002857] | +0.002360 [+0.001785, +0.002915] |
| soybeans, non-irrigated | quantity - controls | -0.016039 [-0.018476, -0.013551] | -0.012984 [-0.015640, -0.010291] |
| soybeans, non-irrigated | distribution - quantity | -0.011147 [-0.014591, -0.007869] | -0.009423 [-0.012412, -0.006696] |
| soybeans, non-irrigated | PDSI season - quantity | -0.006102 [-0.009232, -0.003052] | -0.003653 [-0.006354, -0.001008] |
| soybeans, non-irrigated | PDSI stage - quantity | -0.005534 [-0.008524, -0.002452] | -0.004028 [-0.006595, -0.001546] |

### Terminal same-county test

| Crop/practice | Comparison | RMSE difference [interval] | MAE difference [interval] |
|---|---|---:|---:|
| corn, irrigated | quantity - controls | +0.000607 [-0.000086, +0.001269] | +0.000511 [-0.000199, +0.001211] |
| corn, irrigated | distribution - quantity | +0.002852 [-0.001879, +0.008043] | +0.003822 [+0.000182, +0.007561] |
| corn, irrigated | PDSI season - quantity | -0.000690 [-0.001439, +0.000086] | -0.000526 [-0.001290, +0.000247] |
| corn, irrigated | PDSI stage - quantity | -0.000140 [-0.000808, +0.000524] | +0.000313 [-0.000434, +0.001049] |
| corn, non-irrigated | quantity - controls | -0.096797 [-0.105897, -0.087204] | -0.058832 [-0.069040, -0.048805] |
| corn, non-irrigated | distribution - quantity | -0.060342 [-0.086273, -0.029605] | -0.045244 [-0.059642, -0.030209] |
| corn, non-irrigated | PDSI season - quantity | -0.049216 [-0.062748, -0.036303] | -0.037456 [-0.048636, -0.026698] |
| corn, non-irrigated | PDSI stage - quantity | -0.045035 [-0.058736, -0.032168] | -0.030694 [-0.042524, -0.019147] |
| soybeans, irrigated | quantity - controls | +0.001998 [-0.000047, +0.004301] | +0.001932 [-0.000162, +0.004064] |
| soybeans, irrigated | distribution - quantity | +0.012312 [+0.008478, +0.016308] | +0.010224 [+0.006801, +0.013788] |
| soybeans, irrigated | PDSI season - quantity | -0.002253 [-0.004130, -0.000605] | -0.001779 [-0.003566, -0.000066] |
| soybeans, irrigated | PDSI stage - quantity | +0.000168 [-0.001311, +0.001705] | +0.000014 [-0.001477, +0.001519] |
| soybeans, non-irrigated | quantity - controls | -0.053950 [-0.068184, -0.037458] | -0.029799 [-0.040506, -0.019162] |
| soybeans, non-irrigated | distribution - quantity | -0.058268 [-0.074399, -0.042377] | -0.045819 [-0.059489, -0.032604] |
| soybeans, non-irrigated | PDSI season - quantity | -0.025360 [-0.035279, -0.015439] | -0.019944 [-0.029333, -0.010462] |
| soybeans, non-irrigated | PDSI stage - quantity | -0.035792 [-0.045732, -0.025952] | -0.024119 [-0.033570, -0.014759] |

### Development precipitation-extreme test

| Crop/practice | Comparison | RMSE difference [interval] | MAE difference [interval] |
|---|---|---:|---:|
| corn, irrigated | quantity - controls | +0.005948 [+0.003845, +0.008101] | +0.003709 [+0.001924, +0.005552] |
| corn, irrigated | distribution - quantity | +0.002046 [+0.000304, +0.003746] | +0.000985 [-0.000529, +0.002446] |
| corn, irrigated | PDSI season - quantity | -0.005340 [-0.006880, -0.003826] | -0.003917 [-0.005300, -0.002543] |
| corn, irrigated | PDSI stage - quantity | -0.003895 [-0.005883, -0.001993] | -0.002277 [-0.003977, -0.000595] |
| corn, non-irrigated | quantity - controls | -0.021508 [-0.033490, -0.008594] | -0.004415 [-0.015570, +0.007331] |
| corn, non-irrigated | distribution - quantity | -0.006075 [-0.011737, -0.000184] | -0.006088 [-0.011010, -0.001081] |
| corn, non-irrigated | PDSI season - quantity | -0.032397 [-0.040099, -0.024847] | -0.024740 [-0.032137, -0.017376] |
| corn, non-irrigated | PDSI stage - quantity | -0.039544 [-0.047682, -0.031617] | -0.030716 [-0.038587, -0.022910] |
| soybeans, irrigated | quantity - controls | +0.000493 [+0.000158, +0.000824] | +0.000112 [-0.000209, +0.000450] |
| soybeans, irrigated | distribution - quantity | -0.001760 [-0.004914, +0.001248] | -0.001900 [-0.004677, +0.000937] |
| soybeans, irrigated | PDSI season - quantity | +0.000930 [+0.000074, +0.001746] | +0.000198 [-0.000561, +0.000902] |
| soybeans, irrigated | PDSI stage - quantity | +0.001406 [+0.000152, +0.002654] | -0.000006 [-0.001232, +0.001266] |
| soybeans, non-irrigated | quantity - controls | -0.040030 [-0.047837, -0.031449] | -0.032013 [-0.040462, -0.023418] |
| soybeans, non-irrigated | distribution - quantity | -0.028115 [-0.033930, -0.022392] | -0.020628 [-0.025932, -0.015165] |
| soybeans, non-irrigated | PDSI season - quantity | +0.003682 [-0.002698, +0.009867] | +0.003337 [-0.002762, +0.009186] |
| soybeans, non-irrigated | PDSI stage - quantity | -0.006672 [-0.012974, -0.000550] | -0.004556 [-0.010800, +0.001375] |

## State-specific distribution-versus-quantity intervals

Colorado corn has 257 test rows but only 16 counties in each practice stratum,
so both Colorado intervals are omitted under the locked 30-county rule. It
remains in the pooled development OOF comparison. Every other eligible state
has adequate county support:

| Crop/practice | State | Counties | Rows | RMSE difference [interval] | MAE difference [interval] |
|---|---:|---:|---:|---:|---:|
| corn, irrigated | KS | 101 | 1,527 | -0.002176 [-0.003656, -0.000711] | -0.002597 [-0.004118, -0.001078] |
| corn, irrigated | ND | 36 | 498 | +0.003349 [+0.000939, +0.005636] | +0.005060 [+0.002356, +0.007701] |
| corn, irrigated | NE | 90 | 2,495 | -0.000674 [-0.002460, +0.000995] | +0.001774 [+0.000649, +0.002839] |
| corn, irrigated | SD | 41 | 646 | +0.001387 [-0.000954, +0.003688] | +0.002450 [+0.000080, +0.004575] |
| corn, non-irrigated | KS | 101 | 1,527 | -0.014494 [-0.018622, -0.010278] | -0.011522 [-0.015441, -0.007593] |
| corn, non-irrigated | ND | 36 | 498 | -0.013342 [-0.019849, -0.006944] | -0.011068 [-0.017429, -0.005366] |
| corn, non-irrigated | NE | 90 | 2,495 | -0.004456 [-0.008298, -0.000707] | -0.003539 [-0.006787, -0.000357] |
| corn, non-irrigated | SD | 41 | 646 | +0.017343 [+0.007799, +0.027193] | +0.020829 [+0.013356, +0.027523] |
| soybeans, irrigated | AR | 44 | 980 | -0.004389 [-0.006664, -0.001902] | -0.003218 [-0.005552, -0.000866] |
| soybeans, irrigated | KS | 97 | 994 | -0.002358 [-0.004712, -0.000028] | -0.003255 [-0.005547, -0.000850] |
| soybeans, irrigated | NE | 75 | 1,892 | -0.004840 [-0.006203, -0.003486] | -0.004288 [-0.005614, -0.002979] |
| soybeans, non-irrigated | AR | 44 | 980 | -0.010310 [-0.019303, -0.001436] | -0.011197 [-0.018548, -0.003937] |
| soybeans, non-irrigated | KS | 97 | 994 | -0.022924 [-0.028400, -0.017449] | -0.018135 [-0.022838, -0.013725] |
| soybeans, non-irrigated | NE | 75 | 1,892 | -0.003605 [-0.007112, -0.000208] | -0.003928 [-0.007114, -0.000933] |

The intervals reinforce the original reasons for the frozen promotion
outcomes without becoming a new gate. Non-irrigated corn still reverses in
South Dakota. All six adequate-state soybean distribution-versus-quantity
RMSE and MAE intervals are below zero, but irrigated soybean reverses clearly
in the terminal test and remains inconclusive in the extreme test.

## Post hoc reporting-support checks

These point-only checks were requested after the primary protocol and
bootstrap were frozen. They use fitted terminal scores and support rules that
do not inspect outcome values. They do not alter the primary result or
promotion decision.

First, excluding 2019 endpoints is an exact support no-op: the primary terminal
test already requires a county to have appeared in development, and none of
the sparse 2019 difference rows survives that rule. The test remains 434 rows
and 125 counties per corn practice and 262 rows and 77 counties per soybean
practice, all from 2012--2018. Recomputed differences match the primary values
to floating reduction precision (maximum `2.22e-16` for RMSE and `1.67e-16`
for MAE), with no ranking flip.

Second, a fixed-county window retains only counties with one terminal test row
in every endpoint year from 2012 through 2018. It is feasible under the
registered 50-row floor—13 corn counties/91 rows and 8 soybean counties/56
rows—but falls far below the 30-county bootstrap floor. It therefore receives
point metrics only. Distribution-versus-quantity does not flip on RMSE or MAE
in any stratum. Four other metric-level signs flip:

- irrigated-corn seasonal-PDSI-minus-quantity MAE: `-0.000526` to `+0.000066`;
- irrigated-corn stage-PDSI-minus-quantity RMSE: `-0.000140` to `+0.000328`;
- irrigated-soy stage-PDSI-minus-quantity RMSE: `+0.000168` to `-0.000898`; and
- irrigated-soy stage-PDSI-minus-quantity MAE: `+0.000014` to `-0.000489`.

These small, post hoc reversals on 13 and 8 counties underscore the reporting-
support limitation; they are not selection evidence.

## Validated artifacts and reproduction

The tracked aggregate receipt is
[`../data/provenance/us_competing_moisture_paired_loss_uncertainty_20260826.json`](../data/provenance/us_competing_moisture_paired_loss_uncertainty_20260826.json).
It contains only aggregate comparisons, cluster diagnostics, relative paths,
and hashes. Its SHA-256 is
`192655a3a27e349ce69c8328fc0fd54f9e24fa8886b955af4a4ca197142c457e`.
The other artifact hashes are:

- config: `303315204c2eba2b7e1eed7946b74c5c745d2e01c089045b8fea8762adf538d9`;
- ignored result: `368052c9d6b2abf69b1f5c4c1a074a3f9985bc78060354ef24a66eee610a15d9`;
- unchanged point result: `12d32bec7b9ff6a74339123f95b9282263fdc7675280d9a019c1710dcaaf0b66`;
  and
- unchanged point validation: `778e2fbc2f1dd2351eb0ad91bd1565a7bb7582d68c42b88434ab0c67f697d28c`.

Reproduce and validate with:

```bash
./.venv/bin/python \
  us_county_validation/scripts/evaluate_us_competing_moisture_paired_loss_uncertainty.py \
  --config us_county_validation/us_competing_moisture_paired_loss_uncertainty_v1.toml \
  --result-out outputs/us_county/competing_moisture_paired_loss_uncertainty_v1/result.json

./.venv/bin/python \
  us_county_validation/scripts/validate_us_competing_moisture_paired_loss_uncertainty.py \
  --config us_county_validation/us_competing_moisture_paired_loss_uncertainty_v1.toml \
  --result outputs/us_county/competing_moisture_paired_loss_uncertainty_v1/result.json \
  --out data/provenance/us_competing_moisture_paired_loss_uncertainty_20260826.json

./.venv/bin/python \
  us_county_validation/scripts/test_us_competing_moisture_paired_loss_uncertainty.py
```

The exact validator reruns the bound base validation, refits every registered
split, reconstructs every held-out score in memory, reruns all 5,000-draw
county bootstraps, checks the post hoc point arithmetic, and requires byte-for-
value equality with the candidate JSON. The synthetic test independently
checks a constant-loss case whose bootstrap endpoints are known exactly and
exercises hash, false-gate, family-stacking, shared-support, nonfinite,
minimum-cluster, and dominant-cluster failures.
