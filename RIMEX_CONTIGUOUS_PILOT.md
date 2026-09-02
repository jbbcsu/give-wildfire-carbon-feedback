# Contiguous ISIMIP3b pilot for the RIME-X benchmark

Status: outcome-blind metadata selection and the first bracketing decade pass;
the two 2051--2060 files remain to be acquired and content-validated. No
feature response, damage, welfare, or SCC gate is open.

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

The 2031--2040 `pr`/`tas` pair now passes exact byte/SHA-512 and full decoded
content gates: 3,653 midnight daily values on the global 0.5-degree grid and
946,857,600 finite values per field, with no missing values or negative
precipitation. Ten same-realization GMST values and the bounded 5,488-season/
16,464-stage maize/rainfed feature block pass exact reconciliation. This
closes one decade only, not the 30-year pilot.

Before any fit, all four new files must pass their exact byte/SHA-512 and full
decoded-content gates; the complete 30-year pair must then pass chronology,
same-realization GMST, crop-year, stage/season reconciliation, and centered
window checks. This one-ESM/one-scenario/two-latitude pilot cannot satisfy the
whole-ESM, whole-scenario, multi-crop, rainfed/irrigated, joint-dependence,
actual-FAIR, response, damage, or SCC requirements.
