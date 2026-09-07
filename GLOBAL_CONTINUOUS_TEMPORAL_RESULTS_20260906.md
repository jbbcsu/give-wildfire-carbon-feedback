# Continuous historical global-crop benchmark — September 6, 2026

This exploratory retrospective temporal benchmark uses the retained
1982–2016 inputs rather than only early and late episodes. Training
first differences end in 1983–2010; test differences end in 2012–2016.
Differences ending in 2011 are excluded to avoid shared level endpoints.
Test grid cells must occur in training. Every model uses identical crop-specific
common support and stage mean-temperature and daily Tmax degree-day controls.

## Results

RMSE of changes in log yield (lower is better):

| Model | Maize | Soybeans |
|---|---:|---:|
| Common controls only | .293360 | .179073 |
| Seasonal rainfall quantity | **.292338** | .178067 |
| Quantity plus distribution | .292614 | **.177279** |
| Seasonal scPDSI mean | .292588 | .180311 |
| Stage scPDSI means | .292499 | .180058 |

Maize: 404,671 training and 57,767 test pairs. Soybeans: 166,870 training
and 26,004 test pairs. These are crop-grid-year pairs, NOT independent
observations. Quantity reduces maize RMSE by about 0.35% versus controls;
adding distribution worsens it slightly. For soybeans, distribution improves
RMSE about 0.44% beyond quantity. Neither scPDSI model beats quantity for
either crop; both soybean scPDSI models are worse than controls-only.

The best model's test R2 relative to training-mean prediction is only 0.0224
for maize and 0.0166 for soybeans. Small predictive gains should not be
represented as large explained yield effects or damages. No model is promoted
by this one exploratory temporal split. Geographic validation and uncertainty
are unfinished. The U.S. PDSI ranking does not transfer automatically here.

## Interpretation and remaining limits

- Global gridded coverage is not a globally representative causal response.
  GDHY source construction can induce dependence among cells. Equal pair
  weights are not crop-area, production or welfare weights.
- scPDSI uses full-record calibration, making this retrospective comparison
  unsuitable as evidence of truly prospective drought forecasting.
- The fixed calendars and existing irrigation exposure allocation are retained.
  These are not separate observed rainfed and irrigated yield panels.
- The distribution extension includes stage shares, longest dry spell,
  five-day precipitation extreme and precipitation concentration. Its soybean
  improvement cannot be attributed to timing alone.
- No coefficient export, climate-change projection, welfare or SCC calculation
  occurs. The next scientific step is geographically separated validation and
  source-appropriate uncertainty, not converting these RMSE gains to damages.

## Reproduction and machine safety

Run `scripts/global_continuous_temporal_benchmark.py --out NEW.json` through
`scripts/run_bounded_job.py`. The canonical artifact is
`data/provenance/global_continuous_temporal_benchmark_20260906.json`, binding
all six candidate hashes, assembly-receipt hashes, code and protocol.
`scripts/test_global_continuous_temporal_benchmark.py` compares partitioned
moments with direct least squares on explicitly synthetic fixtures, rejects
singular designs and tests band boundaries/positive-yield filtering.
The scaled empirical Gram condition numbers are 14–46, below the failure
threshold. This is computational checking, not an independent empirical audit.

The first filtered-read attempt was terminated by the monitor at 1,111,146,496
bytes sampled RSS. It produced no result. The revised implementation scans
8,192-row Parquet batches and retains ten-degree bands, completing in 13.23
seconds with 433,061,888 bytes (413.0 MiB) sampled process-group RSS. No new
downloads or large derived datasets were written. The 1 GiB budget was not
raised. The monitor is sampled, not a kernel-enforced allocation limit.
