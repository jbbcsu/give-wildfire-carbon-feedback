# Contiguous ISIMIP3b pilot for the RIME-X benchmark

Status: bounded contiguous-support mechanics pass. No feature response,
damage, welfare, or SCC gate is open.

The published RIME-X method uses a centered 21-year running mean. The existing
GIVE feature artifact has three discontinuous blocks and cannot supply that
operation. The first bounded repair is therefore one GFDL-ESM4 `r1i1p1f1`,
SSP1-2.6 pilot spanning daily `pr` and `tas` from 2031 through 2060. The
2031--2040 and 2051--2060 files bracket the already validated 2041--2050 pair.

This exact design yields crop-feature years 2032--2059 and eight centered
21-year outputs for 2042--2049. It does not pad endpoints, join across gaps,
or treat a scenario label as a predictor. The official ISIMIP API metadata is
frozen in `data/provenance/isimip3b_rimex_contiguous_gfdl_ssp126_plan.csv`.
The six public, unrestricted CC0 version-`20210512` files total
12,384,708,500 bytes and are tied to DOI `10.48364/ISIMIP.842396.1`.

All six files now pass exact byte/SHA-512 and full decoded-content gates. The
30-year same-realization GMST has one value for every 2031--2060 year. The
bounded maize/rainfed panel has 19,208 season and 57,624 stage rows over every
2032--2059 crop year, with exact unsmoothed stage/season reconciliation.

The preregistered centered operation emits exactly 5,488 season, 16,464 stage,
and eight same-realization GMST rows for 2042--2049. Every output uses 21 real
consecutive years; no endpoint padding or cross-gap adjacency is possible.
Smoothed stage precipitation and wet-day sums reconcile to their seasonal
means to `2.28e-13` and `1.43e-14`. The complete receipt is
`data/provenance/isimip3b_rimex_contiguous_gfdl_ssp126_complete_20260902.toml`.

This one-ESM/one-scenario/one-crop/one-irrigation/two-latitude pilot cannot
satisfy whole-ESM, whole-scenario, multi-crop, rainfed/irrigated,
joint-dependence, actual-FAIR, response, damage, or SCC requirements.
