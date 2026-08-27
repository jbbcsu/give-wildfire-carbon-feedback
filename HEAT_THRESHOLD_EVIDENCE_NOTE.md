# Evidence note: daily heat thresholds for the maize/soybean diagnostic

## Decision and scope

For the **nonproduction global predictive diagnostic**, construct heat features at both 29 °C and 30 °C. Use the literature-registered crop-specific prior—29 °C for maize and 30 °C for soybean—as the primary diagnostic, and use a common 30 °C specification as a prespecified sensitivity. These are diagnostic controls, not globally estimated biological optima, production thresholds, causal coefficients, damage functions, or SCC inputs.

The evidence is strong that maize and soybean yields respond nonlinearly to within-season heat exposure and that a break occurs near 30 °C. It is not strong enough to claim that one invariant threshold transports causally across all countries, cultivars, management systems, crop calendars, irrigation regimes, weather products, or future climates. No threshold should be selected because it produces a larger yield loss, damage estimate, or SCC.

## Primary-source evidence

| Primary paper | Design and relevant result | Implication for this diagnostic |
|---|---|---|
| Schlenker and Roberts (2009), *PNAS*, [doi:10.1073/pnas.0906865106](https://doi.org/10.1073/pnas.0906865106) | U.S. county panel models using fine-scale temperature exposure found critical temperatures of 29 °C for maize and 30 °C for soybean; yield response rose modestly below and fell sharply above the crop-specific threshold. The paper's exposure construction represents the temperature distribution within days rather than merely counting days by seasonal mean temperature. | Register 29 °C for maize and 30 °C for soybean as literature priors. Do not treat those U.S. estimates as globally identified thresholds. |
| Schauberger et al. (2017), *Nature Communications*, [doi:10.1038/ncomms13931](https://doi.org/10.1038/ncomms13931) | U.S. observations and an ensemble of process-based crop models showed a yield-response break at roughly 30 °C for rainfed maize and soybean. Negative high-temperature responses were much weaker with irrigation/full water supply, supporting a heat–water-stress mechanism while also showing uncertainty in irrigated observations. | Include a common 30 °C sensitivity and retain irrigation/rainfed distinctions. Heat is not a nuisance independent of moisture; the interaction is scientifically material. |
| Lobell et al. (2011), *Nature Climate Change*, [doi:10.1038/nclimate1043](https://doi.org/10.1038/nclimate1043) | More than 20,000 historical African maize trials linked to daily weather showed nonlinear heat effects above 30 °C. Reported losses per degree day above 30 °C were larger under drought than under optimal rainfed conditions. | The 30 °C maize sensitivity has evidence outside the United States, and moisture modifies heat response. The trial evidence still does not establish universal global transfer or a soybean threshold. |
| Hogan and Schlenker (2024), *Nature Communications*, [doi:10.1038/s41467-024-48388-w](https://doi.org/10.1038/s41467-024-48388-w) | In U.S. maize and soybean panels, daily PRISM, ERA5-Land, and GMFD products recovered similar nonlinear shapes but cross-validated piecewise-linear breakpoints differed by weather product: 27–30 °C for maize and 28–30 °C for soybean. Daily-extreme specifications predicted held-out yields better than a quadratic in seasonal mean temperature. | Threshold location is data-product dependent. Building both 29 °C and 30 °C features is a narrow, literature-grounded robustness exercise; their performance should be reported by dataset and holdout rather than collapsed into a newly “discovered” global threshold. |

The recent cross-dataset paper relevant to the 27–30 °C range is Hogan and Schlenker (2024), not a Kotz et al. paper. That attribution is recorded here to prevent a mistaken citation.

## Diagnostic construction

For each crop-grid-cell-year growing season and threshold \(c \in \{29,30\}\), construct from daily maximum temperature \(T^{max}_d\):

\[
H_c = \sum_d \mathbf{1}(T^{max}_d \geq c), \qquad
X_c = \sum_d \max(T^{max}_d-c,0).
\]

Here, \(H_c\) is a hot-day count and \(X_c\) is daily-maximum degree-days above the threshold. Construct seasonal totals and the same quantities within the prespecified crop stages, with stage totals required to reconcile exactly to the seasonal totals. Apply nonlinear transformations at the grid-day level before harvested-area or irrigation weighting.

These daily-maximum measures are useful controls but are **not exact replications** of Schlenker and Roberts' within-day temperature-exposure measure. Where both daily minimum and maximum temperature are available and data quality is adequate, a separately documented sensitivity should reconstruct intraday exposure before aggregation. Results from the simpler daily-maximum features must not be described as degree-hour exposure estimates.

The registered comparison is:

1. **Primary diagnostic:** maize heat controls at 29 °C; soybean heat controls at 30 °C.
2. **Common-threshold sensitivity:** both crops at 30 °C.
3. **Optional joint sensitivity:** include the registered 29 °C and 30 °C basis only if collinearity and support diagnostics pass; do not infer separate biological effects from two highly correlated threshold variables.

This exercise does not search a large threshold grid and does not select a production specification. A later production threshold would require a frozen training-only selection rule, spatial and temporal held-out validation, stability across weather products, adequate hot-tail support, and uncertainty propagation. Selection must be blind to downstream damages and SCC.

Both 29 °C and 30 °C daily-maximum features have been constructed and
reconciled. The validated version-1 direct-versus-scPDSI result uses the
crop-specific primary controls only. The common-30 °C maize sensitivity and
optional joint specification remain pending and must not be reported as
completed.

## Fair comparison of direct-weather and scPDSI models

The heat basis, crop calendar, sample, fixed effects/trends, outcome, weights, and validation folds must be identical in the direct-precipitation and scPDSI candidate models. Otherwise, a difference in held-out performance cannot be attributed to the competing moisture representation: it could simply reflect different temperature controls, observations, or validation splits. The heat variables should therefore be built once, keyed and provenance-checked, and joined unchanged to the two separate model views.

This symmetry does not make either model causal. It only makes their predictive comparison interpretable. Report coefficient instability, collinearity, support failures, and null or worse held-out performance plainly.

## Attribution limit created by scPDSI

scPDSI is a persistent water-balance index, not precipitation alone. Its construction includes potential evapotranspiration (PET) and antecedent water-balance state. Wells, Goddard, and Hayes (2004) introduced the self-calibration used to improve spatial comparability ([doi:10.1175/1520-0442(2004)017%3C2335:ASPDSI%3E2.0.CO;2](https://doi.org/10.1175/1520-0442(2004)017%3C2335:ASPDSI%3E2.0.CO;2)). van der Schrier, Jones, and Briffa (2011) show explicitly that PET is an input to PDSI and compare temperature-based Thornthwaite and Penman–Monteith PET parameterizations ([doi:10.1029/2010JD015001](https://doi.org/10.1029/2010JD015001)). Although they find precipitation often dominates temporal PDSI variation, that empirical dominance does not remove the temperature/atmospheric-demand content of the index.

Consequently, even with the same explicit heat controls, an scPDSI coefficient cannot be labeled a precipitation-only effect. Its predictive contribution may combine precipitation deficit, evaporative demand, persistence, and their interaction. Adding scPDSI to raw precipitation and temperature as if it were an independent moisture term would also risk double counting. In the present design, direct precipitation features and scPDSI remain **competing moisture representations in separate models**. Causal moisture attribution would require a prespecified identification or decomposition design beyond this predictive diagnostic.

## Guardrails for reporting

- Describe 29/30 °C as literature-registered diagnostic thresholds, not globally valid causal thresholds.
- Report results separately by crop, weather product, irrigation regime where support permits, and temporal/spatial holdout.
- Do not interpret superior prediction as identification of climate-change damages.
- Do not transport diagnostic coefficients into future yield, welfare, damage, or SCC calculations until the production causal and projection gates are independently satisfied.
- Retain null findings and threshold sensitivity; never choose the threshold or model by the sign or magnitude of a downstream SCC.
