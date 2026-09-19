# Same-realization GMST-normalized rainfed-maize weather benchmark

## Result

The audited 2092--2099 crop-area-weighted weather contrasts were divided by
the matching ESM realization's eight-year mean GMST contrast. Seasonal rainfall
has no common sign: the six SSP3-7.0/5-8.5 versus SSP1-2.6 endpoint ratios range
from **-9.41 to +4.66 mm K-1**. In contrast, all six ratios indicate fewer wet
days (**-1.14 to -0.07 days K-1**), longer maximum dry spells (**+0.11 to +0.64
days K-1**), and larger Rx1day (**+0.13 to +1.89 mm K-1**) and Rx5day (**+0.48
to +3.11 mm K-1**) on the fixed rainfed-maize footprint.

| ESM / contrast vs SSP1-2.6 | GMST difference (K) | Rain (mm/K) | Wet days (days/K) | Max dry spell (days/K) | Rx1day (mm/K) | Rx5day (mm/K) |
|---|---:|---:|---:|---:|---:|---:|
| UKESM / SSP3-7.0 | 3.227 | +1.987 | -0.139 | +0.253 | +1.420 | +3.006 |
| UKESM / SSP5-8.5 | 4.315 | +4.663 | -0.094 | +0.171 | +1.147 | +2.400 |
| IPSL / SSP3-7.0 | 2.947 | +3.723 | -0.069 | +0.110 | +1.887 | +3.113 |
| IPSL / SSP5-8.5 | 4.116 | +1.394 | -0.536 | +0.266 | +1.808 | +2.498 |
| MPI / SSP3-7.0 | 2.033 | -9.412 | -1.135 | +0.640 | +0.129 | +0.478 |
| MPI / SSP5-8.5 | 2.644 | -2.624 | -1.006 | +0.625 | +0.663 | +1.592 |

Stage-rainfall ratios are heterogeneous in both sign and location within the
season. Crop-season mean-temperature ratios are +1.24 to +1.40 C per K GMST;
they are preserved in the machine-readable result as a diagnostic, not treated
as an identity.

## Interpretation boundary

This is a descriptive endpoint normalization, not a fitted emulator, local
derivative, causal CO2 response, uncertainty interval, or marginal pulse. Each
contrast uses one realization, only eight terminal years, and scenarios that
differ in more than CO2. Ratios can therefore benchmark a future climate link
but cannot yet drive GIVE. The robust cross-model signal in frequency, dry
spells, and extremes supports retaining distributional features even though
seasonal quantity has no robust sign. Whether those features add agricultural
predictive value remains a separate yield-response question; the global
country-held-out results do not currently show robust incremental value.

## Reproduction and audit

The fixed protocol records that the already-audited weather result and the
GMST file schemas/first two rows were visible before normalization; no claim of
blinded validation is made. The builder hashes all nine resident GMST files,
checks exact ESM/member/scenario/year and Gregorian daily counts, and reads no
raw weather. An independent implementation re-reads each Parquet and
recalculates 114 means, differences, and ratios. All checks pass.

The first builder attempt failed because its guard incorrectly treated the
Gregorian year 2100 as a leap year. Its log and resource receipt are retained;
the corrected `v2` run changed only the calendar gate and completed at 79.08
MiB sampled RSS. The independent audit peaked at 90.80 MiB. Total outputs are
under 20 KiB and the 130 GiB disk floor was preserved.

- Protocol: `GLOBAL_MAIZE_GMST_NORMALIZED_WEATHER_PROTOCOL_20260918.md`
- Builder: `scripts/normalize_maize_weather_by_gmst.py`
- Independent audit: `scripts/validate_maize_weather_gmst_normalization.py`
- Ignored result SHA-256: `a518c0ca1090b78993dbfa7cf16dfb4f492be985f58b2b89649682c6ec0755fb`
- Weather parent SHA-256: `027bd174738cb8de16c218b4674c33e7360c88f50bf719ef9a901769976b44f1`
