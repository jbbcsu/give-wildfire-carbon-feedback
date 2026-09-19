# Frozen descriptive GMST-normalized maize-weather comparison

This design was written before calculating any normalized feature ratio, but
after the area-weather result and the schemas plus first two rows of the nine
GMST files had been inspected. It is therefore a transparent post-result
descriptive normalization, not a blinded validation or a fitted emulator.

Use only the audited area-weighted annual means in
`data/interim/three_esm_maize_area_weather_20260918/result.json`: fixed
MIRCA-2000 rainfed-maize area, UKESM1-0-LL `r1i1p1f2`, IPSL-CM6A-LR
`r1i1p1f1`, MPI-ESM1-2-HR `r1i1p1f1`, SSP1-2.6/3-7.0/5-8.5, and harvest years
2092--2099. Bind that result by SHA-256. Do not reread or alter raw weather.

For the matching ESM/member/scenario, read resident source-derived annual GMST
files `data/interim/isimip3b/{esm}_{member}_{scenario}_gmst_2091_2100.parquet`.
Hash each file; require exactly years 2091--2100, one unique finite annual
value, expected 365/366 daily counts, and exact member/scenario identity. Use
only years 2092--2099 and average the eight annual GMST values equally, matching
the weather window. No historical anomaly origin is needed because only
within-ESM scenario differences enter.

For each ESM and higher scenario `h` in {SSP3-7.0, SSP5-8.5}, calculate

`ratio = (mean_feature_h - mean_feature_126) / (mean_GMST_h - mean_GMST_126)`.

Do this for all nine area-weighted crop-season features. Preserve both the
feature difference and GMST denominator, and fail if the denominator is not
strictly positive. Report all six ESM/contrast ratios; do not average them into
one production coefficient. Independently recompute input hashes, GMST means,
weather means, differences, and ratios from the parent annual ledgers.

These endpoint ratios are units-per-kelvin scenario normalizations, not local
derivatives, causal CO2 responses, pattern-scaling coefficients, uncertainty
intervals, or emulators. They mix scenario forcing composition and internal
variability and use one realization, three ESMs, one crop/management regime,
and eight terminal years. They may benchmark—but may not replace—the missing
marginal-pulse climate-to-weather link required by GIVE.

One numerical worker; sampled RSS <=512 MiB, owned output <=8 MiB, free disk
>=130 GiB, and log <=2 MiB. Raw/interim outputs remain ignored.
