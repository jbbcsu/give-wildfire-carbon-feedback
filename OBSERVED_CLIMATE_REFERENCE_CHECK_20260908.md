# Observational reference identity and interpretation

## Project lineage and primary-source check

The continuous-panel config and acquisition manifest identify the observed-
source exposures as ISIMIP3a GSWP3-W5E5, product DOI
[10.48364/ISIMIP.982724.3](https://doi.org/10.48364/ISIMIP.982724.3).
The three1981–2010precipitation-file catalogue hashes and sizes match the
retained source manifest exactly. Their daily-file version is20211021; the
umbrella DOI product version1.3 is not the file's version date.

The official [DataCite methods metadata](https://data.isimip.org/api/v1/resources/866694bb-84ad-461f-952a-fc64ac72b4ed/)
states that GSWP3-W5E5 uses W5E5 v2.0 during1979–2019 and adjusted GSWP3
before1979. Therefore our1982–2010comparison uses the W5E5 period, not the
earlier GSWP3 component. It also documents existing detrended counterclim
inputs produced with ATTRICI v1.1. Their suitability for precipitation-pattern
attribution has **not yet been evaluated in this project**.

ISIMIP's [bias-adjustment fact sheet](https://www.isimip.org/documents/413/ISIMIP3b_bias_adjustment_fact_sheet_Gnsz7CO.pdf)
identifies W5E5 v2.0 as the ISIMIP3b reference,1979–2014as its training period,
and ISIMIP3BASD v2.5 as the method. It uses31day seasonal windows and did not
use its optional joint multivariate adjustment because of overfitting/spatial-
coherence concerns. Thus nominal reference-version compatibility is supported;
it does not imply identical crop-season statistics or joint dependence.

The fact sheet's Table1 defines pr as **total precipitation, including snow**.
Our pr-derived millimetres are water-equivalent total precipitation, not
liquid rainfall alone. Earlier shorthand “rainfall” should be read accordingly.
No snowfall component has been subtracted; rainfall-only attribution would
require explicit additional inputs and validation.

## Interpretation and remaining boundary

The measured historical model-versus-observed-series offsets remain real
distributional differences in these derived inputs. This check rules out an
assumed mismatch of the nominal W5E5 reference versions; it does not identify
how much comes from simulation variability, differing calibration/application
periods, sequence dependence, interpolation or other processing. Do not call
the offsets an identified observational error or attribute them entirely to
any single algorithmic mechanism. Free-running model years are still not
paired observed weather realizations.

No raw observation files were rehydrated. The project input config is
`config/continuous_global_panel_1982_2016_v1.toml`; acquisition identities are
in`data/provenance/isimip3a_daily_climate_plan.toml`. Official daily-pr dataset:
`ce7b96db-96cf-4d8e-a406-704338415eaa`, responseSHA256
`1874f0475aabb3d58b75e5dafe1fa1f37611a637fca93675cd7080e6da91f3d7`.
Matched1981/1991/2001file IDs respectively:
`9ec1a8b8-5ae6-4e0b-9c23-e53d425decf5`,
`cf07a7ed-7275-4eaa-acb6-828fc67778ce`,
`ac1bd66d-248f-4470-88c6-1ba92e430034`.
Official resource metadata responseSHA256 recorded at retrieval:
`4a0c442672fdb131c0cf926bd0c92a79896373b952801cc8687c9637c1ff49f6`.
The40page fact sheet was text-reviewed for relevant sections on PDFpages2,4,6;
its full document was not reviewed. Screenshot requests returned no model-
visible images through this interface, so visual verification is not claimed.
