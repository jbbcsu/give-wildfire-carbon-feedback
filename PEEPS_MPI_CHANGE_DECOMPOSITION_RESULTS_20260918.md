# Source-matched annual-amount versus within-year rainfall-change diagnostic

This is a **post-level-result, in-sample climate-input diagnostic**, not an
out-of-scenario validation, yield response, damage, or SCC estimate. We
applied the [published PEEPS monthly rainfall patterns](https://doi.org/10.1371/journal.pclm.0000159)
from the [author release](https://doi.org/10.5281/zenodo.7557622) to their
own MPI-ESM1-2-HR SSP5-8.5 source comparison. The exact inputs are the
previously validated, saved 2015/2100 direct two-member monthly means and
published monthly levels at 30,821 MIRCA2000 rainfed-maize nearest centers
(108.086 million positive-weight hectares). The protocol was frozen before
this change calculation: `PEEPS_MPI_CHANGE_DECOMPOSITION_PROTOCOL_20260918.md`.

| Metric, 2100 minus 2015 | Direct MPI | Published PEEPS | Error |
|---|---:|---:|---:|
| Area-weighted mean annual rain change | +43.452 mm | +47.329 mm | +3.878 mm mean bias |
| Spatial annual-change comparison | — | — | 157.710 mm RMSE; 117.473 mm MAE |
| Annual-change sign agreement | — | — | 80.922% of mapped area |

The annual mean bias is small relative to the spatial annual-change RMSE:
spatial cancellation is material. The registered monthly-change error
decomposition gives 46.820 mm overall month-by-location RMSE, of which the
annual-amount error component is 13.143 mm per month and the *within-year
redistribution* component is 44.937 mm. Their squares add to the overall
squared error, within 4.55e-13 mm². This is a decomposition of **calendar-month
amount changes**, not crop-year stage responses or valid monthly-share
projections. The largest area-mean month differences include August
(direct −22.47 versus PEEPS −6.46 mm) and February (direct +0.89 versus
PEEPS +10.33 mm); all twelve monthly values are retained in the ignored
primary result JSON.

The comparison retains locations where the published raw *level* is
negative: 2.856% of area in 2015 and 9.879% in 2100 have at least one
negative published month. Differencing those levels is mathematically
defined but does **not** make them a physically valid future rainfall
forcing. Direct member internal variability, point-center spatial
approximation and same-source training limit interpretation. We have not
estimated a forced rainfall response or quantified out-of-scenario skill.

The primary script is `scripts/score_peeps_mpi_change_decomposition.py`;
`scripts/audit_peeps_mpi_change_decomposition.py` independently recomputed
72 numeric values with scalar `math.fsum`, including all 12 months and the
orthogonal error identity. Three synthetic tests passed. The primary saved
result SHA-256 is
`79ff386f7f429c67fc49732c77fd3bf84f8f0e0520b3ccca9433faa7b3c584e8`.
Both primary and audit outputs are ignored under `data/interim/`; their
resource receipts remain alongside them. The audit sampled 55.05 MB peak
RSS. The very short primary job's 0.2-second process sampling observed only
1.72 MB and may have missed its true peak; it completed without a guard
trigger. No output is promoted to GIVE forcing or SCC.

**Next scientific gate:** a nonnegative monthly climate-response formulation
must be validated against a held-out scenario/model and then against actual
crop-calendar and daily-extreme changes. This source-matched diagnostic by
itself cannot choose that formulation.
