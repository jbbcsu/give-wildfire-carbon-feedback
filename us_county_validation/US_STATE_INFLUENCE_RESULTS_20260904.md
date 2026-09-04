# State influence results — September 4, 2026

All 34 fits completed: four full-sample references and 30 state omissions.
Non-irrigated corn covers ten states and soybeans five. Each quantity contrast
adds 100 mm at the **fixed full-sample median**, not the omitted sample median.
Ranges below are coefficient sensitivity ranges, NOT confidence intervals.

| Crop and contrast | Baseline omission range | With added stage Tmax controls |
|---|---:|---:|
| Corn quantity | 6.71–8.21% | 5.87–7.61% |
| Soybean quantity | 3.31–5.60% | 2.53–5.69% |
| Soybean stage-3-to-stage-2 rainfall share shift (10 percentage points) | 3.78–5.16% | 2.95–5.06% |

For both quantity responses, omitting Kansas gives the lowest estimate and
omitting Nebraska the highest. For soybean timing, omitting Nebraska gives
the lowest estimate and omitting Kansas the highest. No omission reverses
these point estimates. Magnitudes remain sensitive, especially for soybeans.
This checks geographic influence on historical fitted responses, not
out-of-state predictive accuracy, spatially robust inference, adaptation,
national representativeness, or causal climate attribution.

Numerical libraries still emit covariance multiplication warnings in the
underlying estimator. This output intentionally reports only coefficient-based
point contrasts, not covariance-derived intervals or significance. The
previous full-sample QR covariance audit does not validate uncertainty for
these new omission fits. New spatial uncertainty analysis remains required.

Run `us_county_validation/scripts/run_state_influence.py --out NEW.json`
through `scripts/run_bounded_job.py`. The output records source, configuration,
implementation and protocol hashes and all omitted-state results. The source
panel is unchanged. The resource monitor measured 227,049,472 bytes peak
process-group RSS (216.5 MiB), 4.86 seconds, and successful exit. No download
or daily-climate loading occurred. Canonical result:
`data/provenance/us_state_influence_20260904.json`.
