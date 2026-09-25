# Global drought-response literature transfer audit

Date: 2026-09-25

## Decision

No screened study supplies a publication-ready, directly reusable global
`change in drought index -> change in crop yield -> welfare` response object
that can be inserted into the GIVE pulse calculation without re-estimation or
an additional modeling assumption. The literature strongly supports treating
drought and compound hot--dry conditions as material, but it does not open the
project's drought SCC gate.

The defensible next step remains to estimate and validate a response on the
project's own matched crop-calendar panel. The published results below are
external benchmarks. They are not converted into per-unit SPEI coefficients
from plotted percentile contrasts, and they are not added to the direct
precipitation response.

## Transferability screen

| Source | Outcome and design | What is reusable | Why it is not a plug-in GIVE response |
|---|---|---|---|
| [Matiu, Ankerst, and Menzel (2017)](https://doi.org/10.1371/journal.pone.0178339) | Annual FAO country yields for maize, rice, soybean, and wheat, 1961--2014; crop-calendar temperature and one-month SPEI; crop-specific mixed models with quadratic, interaction, and lag terms; LOOCV. | Model structure, crop coverage, crop-area aggregation, temperature--SPEI interaction, and reported extreme-condition effect ranges. | SPEI embeds temperature through potential evapotranspiration; the published headline effects are contrasts between sample quantiles, not marginal coefficients for arbitrary future paths. The article does not distribute a fitted model object or a complete coefficient/covariance package. Country aggregation and flexible detrending also limit causal transport. |
| [Santini et al. (2022)](https://doi.org/10.1038/s41598-022-09611-0) | Country crop-yield anomalies and multiscale SPEI timing, duration, frequency, and severity for four crops. | Pre-sowing and within-season window definitions; multiscale SPEI candidates; severity thresholds. | The principal estimand is contingency/dominance of drought and low-yield classes, not a marginal log-yield response. Derived scripts and worksheets are available only on request. |
| [Heino et al. (2023)](https://doi.org/10.1038/s41598-023-29378-2) | Global gridded yield anomalies and hot/dry compound extremes; XGBoost and partial-dependence analysis. | Public code, global crop support, compound-extreme definitions, and an external predictive benchmark. | The gridded yield input is available on request, the workflow was designed for a computing cluster, and partial dependence is not a causal or directly pulse-scalable damage function. It does not isolate precipitation from temperature in the sense required for a precipitation-only SCC. |
| [Kuwayama et al. (2019)](https://doi.org/10.1093/ajae/aay037) | U.S. county fixed-effects estimates using annual sums of weekly USDM agricultural-area shares, with separate dryland and irrigated samples. | A strong U.S. sign, magnitude, irrigation-heterogeneity, and joint-weather validation target. | USDM combines precipitation, temperature, soil moisture, hydrology, and expert synthesis. Its coefficients are U.S.-specific and cannot be projected from global climate models without a separate USDM emulator. Adding them to direct weather terms would risk double counting. |
| [Heino et al. (2023) code](https://github.com/matheino/crops_vs_extremes) | Eight Python/MPI scripts processing AgMERRA, ERA5/GLEAM soil moisture, gridded yields, XGBoost, and partial dependence. | Reproducible feature and falsification ideas. | Data must be acquired separately and the documented implementation is cluster/MPI oriented; it is unsuitable as a low-memory drop-in module and does not provide welfare or SCC integration. |

## Quantitative benchmark boundaries

Matiu et al. report global dry-condition yield changes of about -7.8% for maize
and -10.7% for soybean at average temperature, and compound hot--dry changes of
-11.6% and -12.4%, respectively. These are useful sign and scale checks only.
They depend on the study's observed 5th-percentile SPEI and temperature values,
quadratic and interaction terms, detrending, and random-effects structure.
Dividing those percentages by an assumed SPEI interval would fabricate a
coefficient and is prohibited.

Heino et al. report an average global yield reduction of roughly 3.9% for
co-occurring growing-season hot and dry conditions defined at 1.5 standard
deviations. That is likewise an event contrast rather than a marginal
precipitation or SPEI slope.

Kuwayama et al. find that an additional week of U.S. drought is associated
with yield reductions of approximately 0.1--1.2% in dryland counties and
0.1--0.5% in irrigated counties. Their paper also finds that direct
precipitation and temperature explain most observed yield variation, while
some drought categories retain incremental information. This supports the
project's competing-family design: drought indices replace, rather than
automatically augment, direct moisture terms unless a pre-specified residual
attribution design passes validation.

## GIVE implementation consequence

1. Keep the validated annual-rainfall quantity SCC as the narrow benchmark.
2. Estimate direct-weather, SPEI, scPDSI/PDSI, and soil-moisture response
   families on identical support and outer blocked folds.
3. Allow temperature controls in every family, but do not interpret an SPEI
   coefficient as precipitation-only when its PET calculation contains
   temperature. Report that family as a joint climatic-water-balance pathway.
4. Promote at most one moisture representation for any crop/region/scenario.
   Do not sum USDM, SPEI, PDSI, soil moisture, and raw precipitation damages.
5. Require stable whole-country/region and time-block holdout gains, physically
   credible signs over the projected support, a matched pulse/base drought
   increment, and covariance propagation before monetization.
6. Use the literature effect ranges above only as external validation checks.

## Data-access implication

The fastest defensible path is local re-estimation using already staged public
yield and climate inputs, not reconstruction of the published cluster-scale
Heino workflow. Author requests for the Matiu fitted coefficients/covariance
and Santini derived scripts would still be valuable, because receipt of a
complete model object could create an independent literature-transport
sensitivity. Until then, no literature-derived drought SCC is reported.

