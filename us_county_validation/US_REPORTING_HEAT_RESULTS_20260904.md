# U.S. rainfall robustness results — September 4, 2026

All 24 exploratory fits completed: two crops, two reported irrigation
practices, two rainfall specifications and three sensitivity variants.
These are regional historical associations, not national causal estimates,
climate-attributable losses, welfare damages or SCC estimates.

## Non-irrigated crop highlights

Fitted yield difference for an additional 100 mm at the respective sample's
median growing-season rainfall; county-clustered normal 95% intervals in
parentheses. Corn uses quantity; soybeans uses quantity plus stage shares,
following the previously selected baseline forms, not a new selection here.

| Specification | Corn | Soybeans |
|---|---:|---:|
| Original 1981–2018 | 7.72% (6.78–8.67) | 4.46% (3.44–5.50) |
| Additional stage maximum-temperature controls | 6.91% (5.87–7.95) | 3.99% (2.80–5.20) |
| Restricted to 2000–2018 | 9.98% (8.33–11.67) | 5.19% (3.60–6.81) |

The original samples have 7,013 corn county-years across 361 counties in
10 states, and 4,844 soybean county-years across 255 counties in five states.
The later-period samples shrink to 2,698 and 1,777 county-years. Changing
sample composition and reference rainfall prevents an adaptation interpretation.

For soybeans, shifting ten percentage points of total rainfall from stage 3
to stage 2, holding total rainfall and other included regressors fixed, has
a fitted association of 4.73% (3.63–5.84) originally, 4.14% (3.12–5.16) with
additional maximum-temperature controls, and 9.49% (7.26–11.77) in the later
period. This sensitivity in magnitude is important: these fits do not establish
a stable transferable timing response. All irrigated and alternative-form
results are retained in the machine-readable artifact, not discarded.

Adding maximum-temperature controls attenuates the reported rainfall
associations without reversing them. Stage-average daily maximum temperature
is NOT daily threshold heat exposure. This exercise does not validate
out-of-sample incremental skill, handle all spatial dependence, or separate
precipitation from every correlated climate driver. Those checks remain open.

## Numerical and resource verification

The original covariance multiplication emitted runtime overflow/invalid
warnings despite finite results. Rather than suppressing this unexamined,
an independent QR/triangular-solve calculation checked coefficients and the
full county-cluster covariance for all 24 fits. Every check passed; the largest
relative covariance Frobenius error was 9.36e-12. A rerun exactly reproduced
the saved JSON. This resolves numerical agreement for these fits, not the
underlying warning's software cause or the statistical identification.

The primary run took 3.56 seconds and sampled peak process-group RSS was
216,711,168 bytes (206.7 MiB). The numerical audit took 1.99 seconds and peaked
at 215,613,440 bytes (205.6 MiB). Both used one numerical thread under a
1 GiB sampled monitor, existing data only, and small JSON outputs. These are
analysis-process measurements, not total Codex application memory.

Reproduction: `scripts/run_bounded_job.py` wraps
`us_county_validation/scripts/run_reporting_heat_sensitivity.py --out NEW.json`.
The checked canonical result is
`data/provenance/us_reporting_heat_sensitivity_20260904.json`; its numerical
audit is `data/provenance/us_reporting_heat_numerical_audit_20260904.json`.
Run the audit script with a new `--out` filename; it also retains its rerun.
The audit reuses sample construction and fixed-effect residualization, so it
is not an independent end-to-end replication.
