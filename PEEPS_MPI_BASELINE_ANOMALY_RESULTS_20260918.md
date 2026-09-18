# Direct-2015 baseline plus published monthly anomaly: physicality failure

The predeclared, source-matched baseline-anomaly test is complete. It uses
the [published PEEPS monthly patterns](https://doi.org/10.1371/journal.pclm.0000159)
from the [author release](https://doi.org/10.5281/zenodo.7557622) and the
same two-member MPI-ESM1-2-HR SSP5-8.5 2015/2100 direct source on 30,821
mapped MIRCA2000 rainfed-maize centers (108.086 million ha). The formula
is `direct_2015 + (PEEPS_2100 - PEEPS_2015)` for each calendar month and
center. This is a **same-source, in-sample** check with a perfect direct
2015 anchor, not a transferable climate emulator or GIVE forcing.

| Registered diagnostic | Anchored PEEPS | Direct-2015 no-change comparator |
|---|---:|---:|
| Area with at least one negative predicted month | **33.962%** | 0% |
| Negative month-center values | **29,529** | 0 |
| Minimum predicted month | **−89.507 mm** | nonnegative |
| Spatial annual-rainfall RMSE versus direct 2100 | 157.710 mm | 253.408 mm |
| Month-center rainfall RMSE versus direct 2100 | 46.820 mm | 57.712 mm |
| Monthly-share total-variation distance, only on common valid 66.038% area | 0.179111 | 0.207534 |

The anchored annual mean bias is +3.878 mm versus −43.452 mm for no
change. Both annual and month-center error metrics retain all area,
including physically invalid negative predictions. Monthly-share distance
uses only the 66.038% of area where anchored and direct-2100 months are
nonnegative with positive annual totals; it cannot be generalized to the
excluded area. Relative improvement over a naive no-change comparator
does **not** override the physicality failure. The greater negative-area
fraction than raw PEEPS levels demonstrates that a single-year direct
baseline plus the released linear slope is not an adequate repair.

The first implementation stopped with a Boolean-index shape error in the
restricted-support share score. Its failure receipt/log remain ignored;
a regression test was added, and the fresh v2 run passed. Independent
scalar recomputation passed all 14 saved numeric metrics; three synthetic
tests passed. Primary result SHA-256:
`d78b5c52b12348a77a42131be7b6c18118bd69c9827d75b48153794486e28db6`.
The audit sampled 54.10 MB peak RSS; the short primary process finished
before the 0.2-second sampler reliably saw its full peak. Both jobs
respected the disk-output and free-space checks.

**Decision:** reject this additive anchored route as a GIVE rainfall
forcing. Continue direct daily ISIMIP as the validated feature-input
route, and assess published positive monthly methods only when their
calibrated parameters/source compatibility and out-of-scenario validation
can be established. No crop yield, damage or SCC estimate follows.
