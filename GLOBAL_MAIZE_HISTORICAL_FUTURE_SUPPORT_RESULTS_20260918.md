# Global rainfed-maize historical/future weather-support diagnostic

## Question and interpretation

Can a response estimated on 1982--2016 crop weather be evaluated on the
2092--2099 direct-daily climate panels without extrapolating the weather
covariates? This is a same-cell domain-overlap diagnostic. It reads no yield
outcome, estimates no response, and produces no damage or SCC result.

The comparison is fixed to 30,654 MIRCA-2000 rainfed-maize cells covering
108,038,665.258 ha. Historical bounds use 35 harvest years of direct crop-year
weather from the observational ISIMIP3a GSWP3-W5E5 pathway. Future weather is
from three bias-adjusted ISIMIP3b ESMs and three SSPs. Therefore the fractions
below are evidence about transport support, not a clean estimate of forced
climate change; source-family differences can contribute.

## Results

Fractions are crop-area weighted and averaged equally over 2092--2099. The
first pair reports the fraction outside each cell's 35-year historical
minimum/maximum for season precipitation and mean temperature. The second
pair reports the corresponding fraction outside the empirical 5th--95th
percentile interval.

| ESM | SSP | Rain outside min/max | Tmean outside min/max | Rain outside 5--95% | Tmean outside 5--95% |
|---|---:|---:|---:|---:|---:|
| UKESM1-0-LL | 1-2.6 | 12.07% | 93.06% | 25.27% | 97.07% |
| UKESM1-0-LL | 3-7.0 | 17.84% | 100.00% | 32.38% | 100.00% |
| UKESM1-0-LL | 5-8.5 | 19.52% | 100.00% | 33.58% | 100.00% |
| IPSL-CM6A-LR | 1-2.6 | 7.60% | 70.06% | 18.15% | 81.82% |
| IPSL-CM6A-LR | 3-7.0 | 13.61% | 100.00% | 24.95% | 100.00% |
| IPSL-CM6A-LR | 5-8.5 | 19.00% | 100.00% | 32.74% | 100.00% |
| MPI-ESM1-2-HR | 1-2.6 | 9.95% | 37.03% | 20.99% | 50.15% |
| MPI-ESM1-2-HR | 3-7.0 | 15.04% | 99.11% | 28.10% | 99.77% |
| MPI-ESM1-2-HR | 5-8.5 | 16.47% | 99.46% | 31.25% | 99.86% |

Wet-day counts fall outside their historical cell-specific min/max on
18.31--33.46% of mapped area across the nine model-scenario combinations.
The corresponding ranges are 7.07--13.05% for longest dry spell,
5.34--21.00% for Rx1day, 5.86--20.32% for Rx5day, and 6.82--18.96% for each
of the three stage-rainfall totals considered individually. These results
show that distributional moisture variables add material extrapolation risk
even where seasonal rain remains within range. They do not establish that a
distribution-rich yield model predicts better than the parsimonious total-rain
model; that remains an outcome-based held-out comparison.

## Gates and consequence

All 72 ESM--SSP--year panels, 19,416,960 raw future season/stage rows, every
tile/source hash, every weighted annual fraction, and all eight-year summary
means passed an independent second implementation. The historical stage sums
reconcile to seasonal rain with maximum absolute difference 0.000854492 mm,
within the pre-existing 0.001 mm pipeline tolerance. The construction peaked
at 439.72 MiB sampled group RSS and wrote 5.25 MiB; the independent audit
peaked at 135.78 MiB.

This closes a measurement gate but opens a substantive transport gate:
unrestricted historical-response projection to end-century climate is not
defensible, especially for temperature. Production damage estimates must use
a declared extrapolation/transport strategy and report support-conditioned
sensitivity. Clipping future weather to historical bounds is not allowed.

## Reproduction and provenance

- Frozen protocol: `GLOBAL_MAIZE_HISTORICAL_FUTURE_SUPPORT_PROTOCOL_20260918.md`
- Builder: `scripts/audit_global_maize_historical_future_support.py`
- Independent audit: `scripts/validate_global_maize_historical_future_support.py`
- Ignored result SHA-256: `994c8851a63b8b29f5d1e2b84efc022ba95ae064e9374146572050d55270248b`
- Ignored bounds SHA-256: `7710715088f32af3d25aea565024f4d0a2c06adad3a173a6b43be5510a710217`
- Independent audit receipt: `data/interim/global_maize_hist_future_support_audit_20260918.json`
