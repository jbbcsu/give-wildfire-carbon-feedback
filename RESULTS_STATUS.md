# Analysis status and claim ledger

Updated: 2026-08-26. This file records completed computational milestones; it
does not report final response estimates or SCC values.

**Legacy-response notice.** Every real response metric generated before the
2026-08-26 endpoint-disjoint purge and response-specification hash revision is
stale. The historical values below are retained only to document pipeline
development and unsuccessful specification stability; they are not current
validation evidence and must be regenerated. This notice covers every
rainfed response audit listed below. The earlier primitive-weather-weighted
maize/soybean audits have the additional, separate basis-allocation error
described in their rows.

| Item | Status | Permitted use |
|---|---|---|
| GDHY v1.2/v1.3 yields | Acquired and checksum-verified | Outcome panel after coordinate checks |
| GGCMI Phase 3 2015soc calendars | 12 crop/irrigation files acquired and SHA-512 verified | Crop-year/stage windows |
| ISIMIP3a daily `pr` | 1981–2019 acquired; source sizes and SHA-512 recorded | Seasonal, dry-spell, wet-day, and extreme features |
| ISIMIP3a daily `tas` | 1981–2019 acquired; source sizes and SHA-512 recorded | Joint temperature control |
| `tasmax` | 1981–2019 acquired; source sizes and SHA-512 recorded | Required input for final heat-extreme specification |
| `tasmin` | 1981–2019 acquired; source sizes and SHA-512 recorded | Required input for final heat-extreme specification |
| Maize/rainfed pilot | Real 2-latitude, 1982–89 feature and GDHY join completed | Pipeline/coordinate/feature validation only |
| Global maize/rainfed, 1982–89 | Season-level and three-window temporal-proxy stage panel complete: 539,360 potential crop-year rows; 120,325 observed-yield rows across 15,098 cells | Workflow/scaling diagnostic only; no SCC input |
| Global maize/fully irrigated exposure, 1982–89 | Season-level and three-window panels contain 539,360 and 1,618,080 rows; all stage/season invariants pass and the same aggregate GDHY outcome has 120,325 positive observations | Irrigation-calendar exposure component only; it is not an irrigated-yield outcome and cannot be fitted as a separate response |
| Global maize/rainfed, 1992–2000 | Season-level and three-window temporal-proxy stage panels, GDHY join, deterministic validation labels, reconciliation, and fixed-effects numerical diagnostic complete: 606,780 potential crop-year rows; 135,405 observed-yield rows across 15,107 cells | Independent-period workflow/coverage diagnostic only; no SCC input |
| Global soybean/rainfed, 1982–89 | Season-level and three-window temporal-proxy stage panel, GDHY join, and deterministic validation labels complete: 539,360 potential crop-year rows; 48,900 observed-yield rows across 6,123 cells | Workflow/scaling diagnostic only; no SCC input |
| Global soybean/fully irrigated exposure, 1982–89 | Season-level and three-window panels contain 539,360 and 1,618,080 rows; all stage/season invariants pass and the same aggregate GDHY outcome has 48,900 positive observations | Irrigation-calendar exposure component only; it is not an irrigated-yield outcome and cannot be fitted as a separate response |
| Global spring-wheat/rainfed, 1982–89 | Season-level and three-window temporal-proxy stage panel, GDHY join, and deterministic validation labels complete: 539,360 potential crop-year rows; 40,977 observed-yield rows across 5,127 cells | Workflow/scaling diagnostic only; no SCC input |
| Global winter-wheat/rainfed, 1982–89 | Season-level and three-window temporal-proxy stage panel, GDHY join, and deterministic validation labels complete: 539,360 potential crop-year rows; 68,778 observed-yield rows across 8,668 cells | Workflow/scaling diagnostic only; no SCC input |
| Global first-rice/rainfed, 1982–89 | Season-level and three-window temporal-proxy stage panel, GDHY join, deterministic validation labels, reconciliation, and fixed-effects numerical diagnostics complete: 539,360 potential crop-year rows; 76,348 observed-yield rows across 9,564 cells | Workflow/scaling diagnostic only; no SCC input |
| Global second-rice/rainfed, 1982–89 | Season-level and three-window temporal-proxy stage panel, `rice_second` GDHY join, deterministic validation labels, reconciliation, and fixed-effects numerical diagnostics complete: 248,040 potential crop-year rows; 12,694 observed-yield rows across 1,587 cells. | Workflow/scaling diagnostic only; no SCC input |
| Six-crop-season rainfed panel, 1982–89 | Combined seasonal data contract and outcome-independent validation labels complete: 2,944,840 potential crop-year rows; 368,022 observed-yield rows. Crop/season identity and source panel are retained. | Data-contract and validation scaling diagnostic only; no common-slope or SCC input |
| Crop-response/SCC interface | Synthetic tests pass for crop-specific feature coefficients, pre-aggregation adaptation, fixed crop-value weights, partial/full coverage gates, and MooreAg-compatible `agcost` output | Executable interface contract only; contains no empirical coefficients, welfare calibration, or SCC result |
| Agriculture component-graph gate | Synthetic passing, missing-source, wrong-source, and coexistence cases pass; the unmodified GIVE baseline is correctly rejected because `Agriculture.agcost` supplies `DamageAggregator.damage_ag` | Structural replacement audit only; no full replacement model, marginal run, or SCC result |
| Full-GIVE replacement execution gate | The installation harness removes legacy MooreAg agriculture, reuses GIVE's regional socioeconomic aggregators, preserves declared sector flags, passes the graph audit, and runs the unmodified GIVE model with six crops and synthetic full-time-axis zero-response inputs under the archived Julia 1.6.4 x86_64/Rosetta environment; active-year crop/regional outputs are complete, coverage is one, and component plus aggregated agriculture damage paths are zero | Synthetic execution/connectivity only; shares and zero coefficients are not empirical inputs, no paired marginal run, empirical damage, welfare, discount, or SCC result is created, and native Apple-silicon execution is blocked before the harness by an unavailable archived Electron artifact |
| Paired agriculture component-output gate | Synthetic matched baseline/pulse runs pass shape, finiteness, pre-divergence identity, targeted post-divergence propagation, and complete-horizon zero-pulse controls; malformed, early-divergence, and false zero-pulse cases fail | Component-boundary conservation only; no empirical bundle, full GIVE paired run, welfare calibration, discounting, or SCC result |
| Stage heat and paired-bundle gates | Synthetic cross-year heat construction, executable stage/season reconciliation audit, cross-threshold nesting checks, partition combine, panel join, and baseline/pulse identity/coverage/weight/conservation checks pass; a real 10-latitude maize slice also reconciles | Pipeline/schema validation only; 30/34 C were QA inputs, not selected heat thresholds, and no fitted response or SCC result is created |
| Continuous global maize/soy feature and candidate panel, 1982--2016 | All 720 isolated 1990--2011 source partitions, 720 receipts, and 144 scPDSI manifests pass the complete registry. Atomic assembly emits 20 validated tables. GDHY joins and fixed-MIRCA basis-before-weighting yield separate continuous direct/heat/scPDSI candidates. Exact direct/scPDSI common support contains 1,053,418 maize rows/491,918 observed outcomes and 772,352 soybean rows/204,917 outcomes; immediate-input recomputation passes. | Data and predictive-diagnostic milestone only. Historical CRU scPDSI remains retrospective, SPEI is not yet on full support, and no family stacking, causal response, future projection, damage, welfare, or SCC result is authorized. |
| Historical crop-stage scPDSI path | The complete 1903--2025 CRU scPDSI file is acquired, SHA-512 recorded, and provenance-verified. Synthetic cross-year construction and real global partition/combine gates pass. Raw-source/calendar-bound manifests and complete derived-input allocation recomputation validate separate fixed-MIRCA aggregate-regime candidates with 16 seasonal/stage features. For 1982--1989: 240,784 maize rows/115,758 positive outcomes and 176,537 soybean rows/47,653 outcomes. For 2012--2016: 150,490/59,772 and 110,336/26,601. Direct-weather columns are absent and missing drought/weight support is excluded only as complete outcome keys with counts recorded. The candidate validator does not claim to independently recompute every raw monthly metric. | Historical competing climatic-water-balance candidate only. The -2 threshold is diagnostic; this construction step emits no coefficient and authorizes no production response. CRU scPDSI is not projected, and no causal, future-drought, damage, or SCC input exists. |
| Direct-weather/scPDSI common-support bundles | Four validated, data-only intersections emit separate 54-feature direct-weather and 16-feature scPDSI views with identical keys and outcomes. Maize 1982--1989 retains 240,784 rows/115,758 observed outcomes and drops 24,744 direct-only rows/1,921 observed outcomes; soybean 1982--1989 retains 176,537/47,653 and drops 14,935/269; maize 2012--2016 retains 150,490/59,772 and drops 15,465/1,046; soybean 2012--2016 retains 110,336/26,601 and drops 9,334/147. scPDSI-only drops are zero rows and zero observed outcomes in all four bundles. | Immediate-input, data-contract validation only. The validator hash-checks inputs/outputs and exactly recomputes both views and their intersection from the supplied candidate tables; it neither reruns upstream raw sources nor binds upstream validation receipts. Those upstream validations and retained receipts are an external prerequisite. No fit, coefficient, causal effect, model selection, future projection, damage, or SCC result is produced. Seasonal quantity remains the direct-weather reference; distribution requires robust stable outer-holdout value, and drought families compete mutually exclusively rather than stack. |
| Direct-weather versus historical scPDSI predictive diagnostic | The real-data coefficient-suppressing diagnostic validates 209,036 global-gridded maize/soybean consecutive-year pairs under identical stage temperature/heat controls and exact direct/scPDSI support. Across five unbuffered hashed 5-degree folds, direct seasonal quantity has the lowest mean RMSE for both crops (maize 0.288589 versus 0.290401 controls and 0.288697 best scPDSI; soybean 0.209670 versus 0.211282 and 0.210183) and lowers RMSE in all ten crop-fold cases. Improvements are below 1%, and MAE is less uniform: direct quantity lowers maize MAE in 4/5 folds and soybean MAE in 2/5. The richer seasonal scPDSI summary is lowest-RMSE in all five maize stress subsets but not a stable general winner. All 110 crop-model-holdout metrics pass an independent clean-room refit and exact audit/receipt/hash/lineage validation; no coefficients or row predictions are emitted. | Historical predictive diagnostic only, not production selection. Metrics weight crop-grid-year pairs equally; folds are unbuffered; buffered/leave-region, common-30 C, SPEI, and soil-moisture sensitivities remain pending. The CRU index uses 1901--2025 full-record calibration, so the early-to-later score is retrospective, not prospective. This result establishes no causal precipitation/drought response, climate-to-drought change, damage, future projection, welfare effect, or SCC input. |
| Paired spatial-OOF loss-difference sensitivity | A hash-locked 5,000-draw paired cluster bootstrap resamples crop-specific 10-degree cells while retaining all years and both episodes together. It exactly reproduces all 50 underlying spatial-fold fits. Maize has 126 occupied cells (effective count 65.26; maximum pair share 2.71%) and soybean 56 (26.66; 6.23%). Direct-minus-controls pooled OOF RMSE differences are -0.001784 [-0.002724, -0.000751] for maize and -0.001576 [-0.003137, +0.000001] for soybean; both MAE intervals include zero. Every one of the 12 scPDSI-versus-direct RMSE/MAE intervals includes zero. An independent clean-room audit reproduces every endpoint exactly; a separate 20,000-draw stream changes endpoints by at most 0.0000631 without changing zero inclusion. | Descriptive geographic-resampling sensitivity only, conditional on fixed OOF fits and equal pair weighting. It does not refit training samples, define a random target population, resolve dependence beyond 10-degree cells, or cover model-choice, causal-response, future-climate, damage, welfare, or SCC uncertainty. The soybean direct-control RMSE endpoint lies only about 0.000001 above zero and is Monte-Carlo-fragile. No significance claim or production selection is permitted. |
| MIRCA-OS v2 irrigation weights | The 284,005,995-byte annual harvested-area archive is MD5/SHA-512 verified; 40 publisher-supplied 0.5° GeoTIFFs for four crops and five vintages pass grid, finiteness, nonnegativity, uniqueness, and unit-share gates. Fixed-2000 maize and soybean weights cover 97.79% and 97.99% of observed-yield cells in the existing 1982--89 panels. | Independent exposure-weight input only. Exact maize/soybean mappings are eligible for allocation; annual rice/wheat maps remain blocked from season-specific outcomes. No response or SCC input. |
| MIRCA rice-season source gate | The 1,537,240,142-byte official monthly archive is object-identity/SHA-512 pinned and all 30 Rice1--Rice3 filenames exist. Metadata pass 21/30: all nine 2005--2015 rainfed files declare year 2020 and are blocked. The six 2000 files pass full input checks, but their maximum-over-month reconstruction exceeds annual Rice by 64,247.23 irrigated ha and 5,302.04 rainfed ha, so both reconciliations fail and no table is emitted. | Failed source-consistency gate only; rice weights remain blocked pending publisher clarification/correction, and neither discrepancy is relaxed or converted into an effect estimate. |
| Rainfed/irrigated outcome-allocation gate | Synthetic failure modes plus real fixed-2000 maize/soybean source/coverage allocations pass. The one-outcome tables retain 117,679/120,325 maize and 47,922/48,900 soybean observations; 2,646 and 978 unmatched outcomes are explicitly excluded without infill or renormalization. | The legacy tables weighted primitive weather before constructing nonlinear terms, so they are not valid response inputs. Only their source, support, exclusion, and one-row-per-outcome audits stand. Production must construct every nonlinear regime basis before area weighting. |
| U.S. county outcome, irrigation, and historical-weather gate | The key-safe Quick Stats fallback retained 7,253 real-FIPS 2018--2022 all-practice corn county-years. The direct-practice screen retains 7,079 corn, 4,845 soybean, and 9,672 all-classes-wheat crop-county-year pairs, but only regional support. All 468 monthly 1981--2019 nClimGrid objects (27,857,685,556 bytes), 419 eligible corn/soy county weights, and 39 harvest-year partitions pass identity/content/schema/calendar/coverage gates. Exact assembly and recomputation produce 23,722 paired-practice corn/soy rows (SHA-256 `205a94ae...c46d7`) and 20,228 common direct-weather/PDSI consecutive-year changes. A second isolated all-practice smoke validates Acadia Parish, Louisiana (22001) in 2019: 119 polygon/grid weights, five monthly weather objects, and one soybean crop-county-year feature row. | Input, construction, and common-support evidence only. Direct-practice support remains regional, the Louisiana result is one engineering row rather than national validation, all-wheat class weights are unresolved, eight historical-boundary cases need sensitivity treatment, and a predictive comparison cannot supply a causal response. No global transfer, damage, or SCC input is created. |
| U.S. all-practice national county-weight expansion | The registered all-county launcher validates and resumes 932 of 2,628 isolated county-weight receipts, then fails closed at Trigg County, Kentucky (21221). Exact recomputation gives full geometric grid coverage but only 0.907267979 weather-valid area relative to declared land, below the fixed 0.95 gate; 209,051,009 m2 of polygon intersection is masked. The same 77 valid cells and area terms recur exactly in January 1981, July 2000, and January 2019, and separate `prcp`, `tavg`, `tmin`, and `tmax` masks reproduce that exact result. Sixteen masked whole-cell intersections total 2.030 times declared county water; even assigning all water to them leaves at least 106,051,904 m2 beyond declared water. A hash-bound scan revalidates all 932 completed receipts and weight hashes: 60 have positive masked area, the minimum completed land-relative ratio is 0.960832366, only one is below 0.97, and seven are below 1.0. | Reproducible structural-coverage blocker only. Completed receipts are 35.46% of registered counties across 16 states, but reflect FIPS-ordered execution plus earlier smokes and are not representative. Trigg is below every completed ratio, yet the threshold is unchanged, no Trigg partition is written, and no partial national feature panel, response, damage, or SCC input is authorized. Resolve the common cell mask against fractional land/water geometry and preregister any corrected denominator, exclusion, or sensitivity rule before resuming. |
| U.S. corn/soy competing-moisture predictive diagnostic | On 20,228 exact-support consecutive-year changes, distribution fails the frozen uniform eligible-state gate for irrigated corn (1/5 states) and non-irrigated corn (4/5; South Dakota reverses), but passes for irrigated and non-irrigated soybean (3/3 each). Non-irrigated corn PDSI is the most stable drought competitor: seasonal and stage PDSI beat quantity-only in all five eligible states and in terminal/extreme tests. Non-irrigated soybean distribution also improves quantity-only in every eligible state, terminal, and extreme test; irrigated-soy distribution reverses in the terminal test. A clean-room raw-level QR audit reproduces all 120 metrics within `2.00e-15` and every discrete gate exactly. A separate hash-bound 5,000-draw county bootstrap exactly reconstructs all fits and reports 62 conditional RMSE/MAE comparisons; the tracked aggregate receipt SHA-256 is `192655a3...2c457e`. | Regional historical prediction only. Direct-practice county support shrinks to 63/25 corn/soy levels in 2018 and 3/1 in 2019; nothing is filled. The 2019-exclusion check is a no-op because no 2019 difference survives the registered same-county terminal rule. A post hoc balanced 2012--2018 check retains only 13/8 corn/soy counties and is point-only; distribution-versus-quantity rankings do not flip. The bootstrap is conditional on fitted models/splits, not refit, model-selection, population, causal, damage, welfare, or SCC uncertainty, and it does not revise the frozen promotion rule. |
| Preliminary U.S. direct-practice precipitation fixed-effects association | Through 2018, county and crop-specific state-by-year fixed-effects fits retain 7,013 corn observations/361 counties and 4,844 soybean observations/255 counties per practice. For non-irrigated corn, +100 mm is associated with +11.07%, +7.72%, and +3.59% fitted yield differences at the observed precipitation quartiles; corresponding irrigated values are +0.04%, -0.41%, and -0.98%. For non-irrigated soybean, registered quantity-plus-timing values are +7.44%, +4.46%, and +1.11%, and a partial 10-point middle-for-late rainfall-share shift is +4.73%; the irrigated timing shift is -0.21%. County-clustered normal 95% intervals exclude zero for all three non-irrigated quantity contrasts and for the non-irrigated-soy timing contrast. Corn timing remains secondary because it failed the prior geographic-stability gate. A clean-room projection plus QR/cluster-sandwich implementation reproduces 324 numeric fields within `1.04e-13`. | Preliminary selected-sample historical association only. Fixed effects and county-clustered uncertainty do not identify causality; crop calendars are fixed; irrigation water, adaptation, CO2 fertilization, and correlated sequence metrics are not separately modeled. No national/global extrapolation, climate attribution, damage, welfare, or SCC claim is authorized. Alternative heat, balanced-support, drought, causal-response, and transport gates remain pending. |
| Trigg official fractional-water mask audit | The official 2019 Census TIGER/Line area-water archive has 2,123 hydrographic polygons whose `AWATER` attributes sum exactly to Trigg County's 102,999,105 m2 declaration. Attribute-weighted EPSG:5070 polygon/grid intersections place 81,538,947 m2 water and 127,512,062 m2 land in the 16 nClimGrid-masked cells. Removing water from both valid and masked areas yields 0.888503097 weather-valid fractional-land coverage. | The source-level correction remains below the unchanged 0.95 gate and strengthens the blocker. No threshold relaxation, county exclusion, weight partition, response, damage, or SCC input is authorized. |
| Official nClimGrid county-average sensitivity samples | Exact January 1981, July 2000, and January 2019 NOAA county-average files for PRCP/TAVG/TMIN/TMAX each contain the same 3,107 county rows and are hash-bound with product-version receipts and the numeric NCEI-to-FIPS crosswalk. NCEI code 15221 maps to Trigg FIPS 21221 and all sampled real-day values are finite and ordered, with a 0.005 C maximum rounded TAVG midpoint error; Trigg monthly precipitation is 30.6, 69.64, and 105.75 mm in the three samples. July 2000 independently validates Adair County, Iowa (19001), with 115.50 mm precipitation and the same value gates. | Three-month source-route feasibility only. This narrows temporal, seasonal, and regional schema drift and bypasses the local polygon mask, but does not replace the registered estimator; historical boundary vintage, numeric-code review, full-panel source identity, and feature-equivalence validation remain open. No response, damage, or SCC use is authorized. |
| Official-versus-polygon nClimGrid estimator sensitivity | The outcome-blind comparison retains Cuming County, Nebraska (31039), and Fresno County, California (06019), across April 1990, July 2000, and drought-month July 2012. Every month has exact 3,107-county support in PRCP/TAVG/TMIN/TMAX. Temperature correlations exceed 0.99999 except April's still-high 0.999993 minimum; precipitation correlations are at least 0.99983 except Fresno's near-zero-rain July 2012 value of 0.98533. The largest polygon-minus-official monthly rain difference is 0.9926 mm. | Bounded weather-measurement sensitivity only. Close daily agreement does not establish nationwide, seasonal, or historical-boundary equivalence, and the nonzero rainfall differences prohibit silently replacing either estimator. No yield response, damage, welfare, or SCC input is authorized. |

The outcome-blind February 2000 leap-month extension retains the same counties
and four variables, validates exactly 29 finite days, and has minimum daily
correlation 0.999988. Polygon-minus-official monthly precipitation is +0.2838
mm in Cuming and +0.6589 mm in Fresno. This closes a leap-day decoding check
only; the nonzero differences continue to reject estimator equivalence.
| Maize/rainfed blocked response audit, 1982–89 | **Legacy pre-purge audit:** 105,157 consecutive observed-yield pairs were evaluated under the superseded split/hash | Stale engineering history only; rerun required before predictive comparison, and no causal, global-response, or SCC claim is permitted |
| Maize/MIRCA-2000 area-weighted response audit, 1982–89 | Legacy invalid-order output: nonlinear precipitation bases and interactions were constructed after rainfed/irrigated primitive-weather averaging. The previously listed RMSEs are withdrawn. | Superseded engineering artifact only; do not cite, compare, fit, or use for causal/damage/SCC work. Rerun requires regime-basis-before-area-weighting and a basis-preserving evaluator. |
| Soybean/MIRCA-2000 area-weighted response audit, 1982–89 | Legacy invalid-order output: nonlinear precipitation bases and interactions were constructed after rainfed/irrigated primitive-weather averaging. The previously listed RMSEs are withdrawn. | Superseded engineering artifact only; do not cite, compare, fit, or use for causal/damage/SCC work. Rerun requires regime-basis-before-area-weighting and a basis-preserving evaluator. |
| Maize/MIRCA-2000 corrected minimal response audit, 1982–89 | Current-hash basis-before-weighting diagnostic: 117,679 observed levels and 102,847 consecutive pairs. Stage-joint is descriptively lowest RMSE spatially (0.2921 versus 0.3082 zero) and for the retrospective high-tail stress split (0.2974 versus 0.3144 zero); seasonal-joint is lower temporally by 0.000056 RMSE (0.3070 versus 0.3071). All purged endpoint-overlap counts are zero. | Validated predictive diagnostic only. Eight years, minimal feature basis, area-share reduced-form exposure, suppressed coefficients, and unresolved causal specification prohibit damage or SCC use. |
| Soybean/MIRCA-2000 corrected minimal response audit, 1982–89 | Current-hash basis-before-weighting diagnostic: 47,922 observed levels and 41,915 consecutive pairs. Stage-joint is descriptively lowest RMSE spatially (0.2185 versus 0.2322 zero) and for the retrospective high-tail stress split (0.2212 versus 0.2332 zero); seasonal-joint leads temporally (0.2586 versus 0.2737 zero). All purged endpoint-overlap counts are zero. | Validated predictive diagnostic only. Eight years, minimal feature basis, area-share reduced-form exposure, suppressed coefficients, and unresolved causal specification prohibit damage or SCC use. |
| Direct precipitation-pattern candidate bases, maize/soybean MIRCA-2000, 1982–89 | Validated 54-column basis-before-weighting tables contain 265,528 maize and 191,472 soybean outcome rows, including 117,679 and 47,922 observed yields. Seasonal/stage amount, normalized shares/timing/concentration, wet-day frequency/intensity, CDD, Rx1day, Rx5day, temperature, and interactions pass stage/season and range gates. | Candidate data contract only. The 1 mm wet-day setting is unselected, heat and alternative drought families are separate open gates, and fitting/causal/damage/SCC use is explicitly unauthorized. |
| Locked quantity-versus-distribution predictive screen, maize/soybean MIRCA-2000, 1982–89 | A separate hash-locked contract compares stage-temperature controls, seasonal rainfall quantity, and nested timing/concentration, occurrence/intensity, dry-spell, and wet-extreme sets. A full independent rerun reproduces every metric with zero endpoint overlap. The best distribution candidate reduces pooled RMSE beyond seasonal quantity by 0.00117–0.00138 for maize and by 0.00084–0.00261 for soybean across the three holdouts, but the full distribution model worsens soybean temporal RMSE by 0.00355. | Coefficient-suppressing screening evidence only. Differences are small and fold/year heterogeneous, have no paired uncertainty or multiple-comparison adjustment, and do not establish causality, production-model selection, damages, or SCC use. The retrospective high-tail stress split covers about 47% of pairs and is not rare-event validation. |
| Aggregate-regime maize/soybean feature panels, 2012–2016 | Rainfed and fully irrigated daily-feature panels are complete for both crops. Fixed-2000 MIRCA basis-before-weighting allocation yields 165,955 maize and 119,670 soybean crop-grid-year rows, with 60,818 and 26,748 positive observed yields; 484 and 433 observed outcomes without eligible weights are excluded without infill. Seasonal/stage quantity, distribution, dry-spell, wet-extreme, and temperature reconciliation checks pass. | Real later-period engineering and predictive-diagnostic inputs only. GDHY remains an aggregate outcome, heat and competing drought families remain separate, and no causal coefficient, damage, or SCC input is authorized. |
| Locked quantity-versus-distribution predictive screen, maize/soybean MIRCA-2000, 2012–2016 | Full input-panel recomputation validates 46,434 maize and 20,682 soybean consecutive pairs. No distribution family improves on seasonal quantity in all three holdouts for either crop. All maize distribution extensions worsen spatial and temporal RMSE; timing/concentration improves the high-tail score by only 0.000044. Soybean dry spells improve spatial RMSE by 0.001516 and occurrence/intensity improves the high-tail score by 0.001366, but all distribution extensions worsen temporal RMSE. The full set worsens temporal RMSE by 0.004826 for maize and 0.003491 for soybean. | Adverse and heterogeneous predictive screening evidence retained under the registered hierarchy. It supports using seasonal quantity as the parsimonious reference unless later causal/external validation overturns it; it does not select a production response or authorize damages/SCC. The short-panel high-tail split covers about 66% of pairs and is not rare-event validation. |
| GDHY 2012–2016 support sensitivity | The checksum-verified official archive has lower positive-yield support in 2015, followed by restoration in 2016: 1,791 maize-major cells and 596 soybean cells. No values are imputed or relabeled. A separate three-model minimal-basis complete-positive-support sensitivity retains 87.06%/91.23% of maize levels/pairs and 91.07%/94.23% of soybean levels/pairs; seasonal joint temperature–quantity is lowest-RMSE in all six crop-by-holdout comparisons in that selected sample. | Source-support and sample-composition sensitivity only. The seven-family distribution screen has not been rerun on this subset, which may be nonrepresentative; the unbalanced positive-pair panel remains primary, and publisher clarification plus endpoint exclusions remain publication sensitivities. |
| Evidence-led water-stress hierarchy | The production registry now makes joint temperature plus crop-calendar seasonal precipitation quantity the parsimonious reference; distribution terms require robust stable incremental outer-holdout value. PDSI/scPDSI and SPEI are serious competing moisture-stress families under common validation, not additive controls. Executable scope tests fail if null/worse-result reporting, drought competition, non-stacking, or the prohibition on selection by SCC magnitude is removed. | Design and integrity rule only. No water-stress family or primary production response has been selected, and no coefficient, damage, or SCC input is authorized. |
| Leakage-safe SPEI source/method gate | Primary SPEI-1/3/6 is locked to source-consistent local nClimGrid-Daily (U.S.) and ISIMIP3a GSWP3-W5E5 (global) precipitation and temperature. Daily Hargreaves-Samani reference ET uses FAO-56 radiation; monthly `P-ET0` is fit by grid cell/calendar month with a three-parameter log-logistic unbiased-PWM estimator on 1982--2011 and applied frozen after 2011. NOAA nClimGrid-Monthly SPEI (1895--2014 calibration, Thornthwaite) and SPEIbase 2.11 (CRU/FAO-56, public generation-code version gap) are retrospective checks only. Contract, radiation/ET/month/rolling primitives, source coverage predicate, and adversarial tests pass. | Source/method/scaffold gate only. No full SPEI field, crop-calendar candidate, outcome fit, causal effect, damage, or SCC result exists. Partial boundary-month weighting is retrospective; scales remain separate rather than outcome-selected or stacked. Sixteen provisional 1982 maize keys requiring pre-1981 antecedent climate must be recomputed and removed through the master intersection unless older forcing is separately acquired. |
| Welfare-support audit, MIRCA-2000 with current 1982–89 response support | Consecutive-pair cells cover 79.017% of positive MIRCA maize area and 89.288% of soybean area, not the roughly 98% suggested by conditioning the denominator on GDHY-observed cells. A MIRCA-area-times-GDHY-2000 production proxy is undefined over 20.984%/10.713% of global MIRCA area; spatial crop-value coverage is unavailable. | Harvested-area support diagnostic only. Unconditional production/revenue coverage, cross-crop welfare aggregation, sample-gap treatment, and SCC use remain blocked pending a pinned compatible production/value source or an explicit bounded gap model. |
| MIRCA fixed-vintage response sensitivity, 2000--2020 | Legacy invalid-order outputs for all maize/soybean vintages; their model rankings and RMSE movements are withdrawn pending a corrected rerun. Source coverage across vintages remains an independent valid audit. | No response sensitivity result. A future rerun must hold each vintage fixed, build nonlinear bases within regime, and use an evaluator that never overwrites prebuilt terms. |
| Six-crop/rainfed blocked response audit, 1982–89 | **Legacy pre-purge audit:** 321,620 consecutive observed-yield pairs under the superseded split/hash; source row counts remain valid | Stale engineering history only; rerun required and no universal-model, causal, or SCC claim is permitted |
| Maize/rainfed independent-period audit, 1992–2000 | **Legacy pre-purge audit:** 119,950 consecutive observed-yield pairs under the superseded split/hash; source row counts remain valid | Stale engineering history only; rerun required and no coefficient or SCC use is permitted |
| Maize/rainfed contiguous-period audit, 1982–2000 | Data combination remains valid (1,280,980 potential rows; 285,871 positive-yield rows), but the 270,273-pair response audit is **legacy pre-purge** | Stale response history only; rerun required and rainfed-calendar exposure still prohibits causal or SCC use |
| Soybean/rainfed independent-period audit, 2002–2010 | Source panels/reconciliation remain valid, but the 48,959-pair response audit is **legacy pre-purge** | Stale response history only; rerun required, coefficients remain suppressed, and no causal or SCC use is permitted |
| Matched future climate-feature driver | Frozen official catalogue selects the complete five-ESM/member by four-scenario by four-variable matrix: 80 public/unrestricted CC0 version-`20210512` datasets and 1,756,959,247,729 catalogue bytes. Bounded complete-file `pr`/`tas` coverage now includes historical plus SSP1-2.6/3-7.0/5-8.5 for all five frozen ESM realizations. Every file passes exact API-byte/SHA-512, decoded-content, historical-boundary, same-realization GMST, and bounded maize/rainfed feature gates. The UKESM expansion adds six files/6,680,992,736 bytes and exact-reconciliation feature cells. Its historical/four-scenario diagnostic has 113,190 rows and 44 folds; the simple GMST adjustment improves 23, with median RMSE ratio 0.999853 and maximum 1.032478, so it is not promoted. The exact five-ESM/four-scenario product has 565,950 rows. Whole-ESM folds improve 41/55 (median RMSE ratio 0.997595; maximum 1.051452); whole-scenario folds improve 36/44 (median 0.997441; maximum 1.016051). Both engineering gates pass independent validation, but the emulator is not promoted. A separate 880-row aggregate artificial-Kelvin pairing smoke passes common-residual, zero-pulse, pre-divergence, support-flag, direct/centered, and decreasing-pulse numerical gates; 19 pulse rows are above and 10 below bounded support. The pinned core GIVE/FAIR API separately produces 2,204 matched 1750--2300 temperature rows for zero plus three decreasing 2020 CO2 pulses; baselines, zero/pre-pulse identity, 2021 first divergence, and normalized convergence pass, with a 1.8368e-7 K maximum response to 0.0001 GtC. A 127,160-row alignment sensitivity shows exact practical equivalence of absolute-anomaly and centered-coordinate affine mappings (maximum disagreement `4.55e-12`) but only 5.95% mapped-temperature and 35.90% feature support within the bounded training range per method; mapped baseline GMST first exceeds support in 2021/2027/2033 for GFDL/MPI/the other three ESMs. | Seven nonoverlapping years, one crop/regime, and two latitude rows only. The severe support failure rejects promotion of the affine smoke. Full temporal/spatial/multi-crop coverage, a production reference window/response, residual path, damage, and SCC gates remain open. |
| Predeclared later-century ISIMIP3b support expansion | The live official API validates a full 5-ESM x 3-SSP x 2-variable x 2-period Cartesian product: 30 version-`20210512` datasets and 60 public, unrestricted CC0 files totaling 124,935,312,957 bytes. The fixed blocks are 2041--2050 and 2091--2100; eligible engineering harvest years are 2042--2049 and 2092--2099 so cross-year seasons never cross an unacquired boundary. All six registered GFDL-ESM4 and all six IPSL-CM6A-LR scenario/period `pr`/`tas` pairs, plus MPI-ESM1-2-HR SSP1-2.6 in both 2041--2050 and 2091--2100, pass full SHA-512, decoded 3,652-day global-grid, same-realization GMST, and bounded-feature gates; IPSL and MPI use an exact 12:00 daily timestamp contract while GFDL uses 00:00. Each variable/block has 946,598,400 finite values and zero missing values; every `pr` block has zero negative values. Each two-latitude-row maize/rainfed smoke produces 5,488 seasonal and 16,464 stage rows with exact additive reconciliation. Matched IPSL SSP3-7.0-minus-SSP1-2.6 means are +0.365 C, +13.22 mm seasonal rain, +0.93 wet days, -1.36 maximum dry-spell days, +2.18 mm Rx1day, and +3.84 mm Rx5day at midcentury; corresponding end-century means are +4.146 C, +25.70 mm, +2.85 days, -2.26 days, +3.12 mm, and +4.47 mm. Matched IPSL SSP5-8.5-minus-SSP1-2.6 means are +0.607 C, +19.88 mm, +2.07 days, -0.77 days, +2.01 mm, and +3.13 mm at midcentury and +6.289 C, +5.94 mm, +0.71 days, +2.15 dry-spell days, +2.13 mm Rx1day, and +2.56 mm Rx5day at end century. The joined IPSL three-SSP midcentury product has 181,104 rows: GMST adjustment improves 15/33 comparisons (median RMSE ratio 1.00028; maximum 1.02568), only 3/11 for held-out SSP5-8.5, and 20,529/181,104 values (11.34%) are outside exact support. The matching IPSL end-century product improves 10/33 (median 1.00275; maximum 1.27466), only 2/11 for held-out SSP5-8.5, with 30,619/181,104 values (16.91%) outside support. The joined GFDL midcentury product improves 14/33 (median 1.00036; maximum 1.06410), only 1/11 for held-out SSP5-8.5, with 20,562/181,104 values (11.35%) outside support. The GFDL end-century product improves 13/33 comparisons (median ratio 1.00110; maximum 1.23350), with 27,260/181,104 held-out values (15.05%) outside support. Temperature-only reclassification of paired FAIR paths against the 287.659--291.189 K GFDL envelope puts every 2012--2300 baseline year within the envelope while pairing, identity, and decreasing-pulse gates remain passed. | Twenty-eight of 60 complete-file gates and fourteen bounded feature blocks only. The IPSL climate comparisons are descriptive, and both the IPSL and GFDL scenario holdouts reject promotion; the two same-scenario MPI later-century cells do not support a new response claim. Whole-ESM validation remains incomplete. Support flags describe held-out climate features, not FAIR baseline/pulse features; response, damage, and SCC gates remain open. The blocks are noncontiguous, and FAIR after 2100 remains outside direct ISIMIP daily-feature support despite the temperature-only envelope. |
| U.S. national reported-zero support | The exact 1981--2019 all-practice corn source contains 499 reported zero-yield county-years across 150 counties, 18 states, and 217 consecutive spells; the longest spell is 10 years and 118 zero rows have an adjacent positive observation. Every zero lies in 1998--2009, leaving 17 declared years before and 10 after with none, and the top five states contain 73.55% of zero rows (state-row HHI 0.1552). The fixed geography gate retains 419 rows. Only 45 zero rows have a usable fixed-2017 irrigation share; 7/8/8 meet the 10/20/30% high-rainfed selectors. Among adjacent-positive rows, those counts fall to 111 geography-eligible, 15 irrigation-share-eligible, and 4/5/5 high-rainfed. | Descriptive zero-outcome support only. The temporal/state concentration prevents interpreting reported zeroes as a generic crop-failure signal. Nothing is replaced, log-transformed, or modeled; all-practice zeroes are not direct rainfed outcomes. A two-part or other zero-retaining outcome model remains unselected, and no response, damage, or SCC claim is authorized. |
| Remaining production coverage | Corrected MIRCA-weighted aggregate-regime quantity/distribution panels and separate direct/heat/historical-scPDSI candidates now cover maize/soybean continuously through 1982--2016. A source-consistent leakage-safe SPEI method is locked but its full fields/candidates are not built. Rice/wheat irrigation mappings, soil-moisture competitors, causal response draws, matched future drought features, the full future ensemble, welfare calibration, and paired SCC runs remain incomplete. | No production global response or SCC claim |

Post-table checkpoint (2026-08-31): the MPI-ESM1-2-HR SSP5-8.5 2041--2050
`pr`/`tas` pair, same-realization GMST, and bounded feature block now pass.
Together with the separately registered MRI SSP1-2.6 2041--2050 block, this
raises the later-century expansion to 32 of 60 complete-file gates and sixteen
feature blocks. Exact-key SSP5-8.5-minus-SSP1-2.6 MPI means are +0.237 C,
+17.88 mm seasonal rain, +1.37 wet days, -1.00 maximum dry-spell days, +1.71
mm Rx1day, and +6.75 mm Rx5day across 5,488 fixed seasonal cells. This is a
descriptive climate-support diagnostic only; whole-scenario, whole-ESM,
response, damage, and SCC gates remain open. This checkpoint supersedes the
28/60 and fourteen-block counts in the table row above.

The MRI-ESM2-0 SSP3-7.0 2041--2050 `pr`/`tas` pair, same-realization GMST,
and 5,488-season/16,464-stage maize/rainfed block now also pass exact checksum,
decoded-content, and reconciliation gates. Relative to matched MRI SSP1-2.6
cells, mean differences are +0.369 C, -11.02 mm seasonal rain, -1.07 wet days,
+0.23 maximum dry-spell days, -0.32 mm Rx1day, and +0.26 mm Rx5day. Tracked
progress is 34/60 files and seventeen feature blocks; these descriptive values
do not close whole-scenario, whole-ESM, response, damage, or SCC gates.

The MRI SSP5-8.5 2041--2050 pair and bounded block now pass the same gates,
raising progress to 36/60 files and eighteen blocks. Relative to SSP1-2.6,
mean differences are +0.777 C, -8.81 mm seasonal rain, +0.28 wet days, -2.83
maximum-dry-spell days, -1.50 mm Rx1day, and -2.68 mm Rx5day. The resulting
181,104-row MRI three-scenario midcentury holdout improves 15/33 comparisons,
has median/maximum RMSE ratios of 1.00027/1.04233, and flags 21,236 values
(11.73%) outside support. This adverse engineering result does not authorize a
response, damage function, or SCC input. The MRI SSP1-2.6 and SSP3-7.0
end-century pairs now pass the same complete-file, same-realization GMST,
feature, and reconciliation gates. Matched SSP3-7.0 minus SSP1-2.6 means are +2.928 C, +2.24 mm
rain, -0.97 wet days, +2.41 maximum-dry-spell days, +0.25 mm Rx1day, and
+1.15 mm Rx5day. The MRI SSP5-8.5 end-century pair and block also pass,
raising tracked progress to 42/60 files and twenty-one blocks. Relative to
SSP1-2.6, means are +4.591 C, -13.23 mm rain, -2.62 wet days, +5.44 maximum-
dry-spell days, +0.75 mm Rx1day, and +0.56 mm Rx5day. The 181,104-row MRI end-
century holdout improves 16/33 comparisons, has median/maximum RMSE ratios of
1.00006/1.06514, and flags 27,090 values (14.96%) outside support. This mixed,
adverse engineering result does not authorize a response, damage, or SCC input.

Post-table checkpoint (2026-09-01): the remaining frozen MPI-ESM1-2-HR
SSP3-7.0 mid- and end-century pairs and SSP5-8.5 end-century pair pass exact
catalogue bytes/SHA-512, full decoded-content, same-realization GMST, bounded
maize/rainfed feature, and exact stage/season reconciliation gates. This raises
tracked expansion to 48/60 files and twenty-four blocks. Relative to matched
SSP1-2.6 cells, mean SSP3-7.0 differences are +0.447 C, -4.38 mm seasonal
rain, -0.36 wet days, +2.53 maximum-dry-spell days, -1.17 mm Rx1day, and
+0.71 mm Rx5day at midcentury, and +3.273 C, -17.02 mm, -1.61 days, +2.54
days, -2.49 mm, and -3.59 mm at end century. End-century SSP5-8.5 differences
are +4.251 C, -13.20 mm, -1.43 days, +2.18 days, -0.92 mm, and -1.11 mm.
These are descriptive support diagnostics; whole-scenario, whole-ESM, FAIR
feature-support, response, damage, welfare, and SCC gates remain closed. The
registered MPI whole-scenario audits are adverse: midcentury improves 14/33
comparisons (median/maximum RMSE ratios 1.00163/1.05542) with 21,100/181,104
(11.65%) values outside exact support; end century improves 15/33
(1.00028/1.09814) with 27,605/181,104 (15.24%) outside support. Neither opens
an emulator, response, damage, welfare, or SCC gate.

The version-pinned four-ESM whole-ESM evaluator joins the GFDL, IPSL, MPI, and
MRI three-scenario products with exact source-audit and training hashes. Each
period has 724,416 rows and 44 comparisons. Midcentury improves 27/44
(median/maximum RMSE ratios 0.99954/1.00969) and flags 60,393 values (8.34%)
outside exact three-ESM support. End century improves only 12/44
(1.00040/1.06362) and flags 68,582 (9.47%). Both complete reruns are
byte-identical. UKESM remains absent; production emulator, FAIR feature-path,
response, damage, welfare, and SCC gates remain closed.

The first later-century UKESM1-0-LL pair (SSP1-2.6, 2041--2050) passes exact
catalogue bytes/SHA-512 and all 946,598,400 decoded values per field, with no
missing values or negative precipitation. Its exact midnight chronology is a
registered ESM-specific boundary, not a shifted or inferred date; the same-
realization GMST and 5,488-season/16,464-stage maize block reproduce byte-
identically and reconcile exactly. Coverage is now 50/60 files and twenty-
five blocks. Five UKESM pairs, the complete five-ESM holdout, FAIR feature
support, response, damage, welfare, and SCC gates remain closed.

The matching UKESM SSP1-2.6 2091--2100 pair also passes and reproduces its
same-realization GMST and 5,488-season/16,464-stage block byte-identically.
Separate-slice end-century-minus-midcentury means are +0.849 C, -3.19 mm
seasonal rain, +0.33 wet days, +0.49 maximum-dry-spell days, +0.69 mm Rx1day,
and +2.48 mm Rx5day. They are descriptive period means, not a response or
causal contrast. Coverage is 52/60 files and twenty-six blocks; four UKESM
pairs and every production/damage/SCC gate remain open.

The UKESM SSP3-7.0 2041--2050 pair passes exact catalogue bytes/SHA-512,
explicit-midnight decoded content, same-realization GMST, and byte-identical
5,488-season/16,464-stage reconciliation. Against the exact-key SSP1-2.6 cell,
mean changes are +0.876 C, -6.76 mm rain, -0.72 wet days, +2.66 maximum-dry-
spell days, -0.53 mm Rx1day, and +1.60 mm Rx5day. Coverage is 54/60 files and
twenty-seven blocks; three UKESM pairs, the five-ESM rerun, FAIR feature
support, response, damage, welfare, and SCC gates remain open.

The matching UKESM SSP3-7.0 2091--2100 pair passes and raises coverage to
56/60 files and twenty-eight blocks. Against exact-key SSP1-2.6, mean changes
are +4.293 C, +8.32 mm rain, +1.07 wet days, +0.60 maximum-dry-spell days,
+1.46 mm Rx1day, and +2.85 mm Rx5day. Two SSP5-8.5 UKESM pairs and the
five-ESM/FAIR/response/damage/welfare/SCC gates remain open.

The UKESM SSP5-8.5 2041--2050 pair passes exact catalogue bytes/SHA-512,
explicit-midnight decoded content, same-realization GMST, and byte-identical
5,488-season/16,464-stage reconciliation. Against exact-key SSP1-2.6, mean
changes are +1.195 C, +5.16 mm rain, -0.19 wet days, +0.55 maximum-dry-spell
days, +2.37 mm Rx1day, and +6.68 mm Rx5day. Coverage is 58/60 files and
twenty-nine blocks; the last UKESM pair plus all five-ESM, FAIR, response,
damage, welfare, and SCC gates remain open.
The complete 181,104-row UKESM midcentury whole-scenario audit improves only
13/33 comparisons over the cell-mean benchmark, with median/maximum RMSE
ratios 1.00035/1.22120 and 22,115 values (12.21%) outside exact support.
Held-out SSP3-7.0 improves only 1/11 comparisons. This outcome-blind adverse
evidence leaves every production and SCC gate closed.

The fixed Cuming/Fresno official-NOAA-versus-polygon comparison now includes
January 2019 as a recent-boundary check. All four variables retain exact
3,107-county support and 31 finite days; polygon-minus-official monthly rain is
+0.0441 mm in Cuming and +0.4057 mm in Fresno. Nonzero differences continue
to reject estimator equivalence and authorize no response, damage, or SCC use.
The fixed December-2019 seasonality extension retains exact 3,107-county
support and 31 finite days. Polygon-minus-official monthly rain is -0.3216 mm
in Cuming and +0.3431 mm in Fresno, and all eight county-variable correlations
are at least 0.999986. Nonzero signed differences continue to reject estimator
equivalence and authorize no route replacement, response, damage, or SCC use.

## Completed empirical checks

Unless explicitly labeled current-hash and basis-before-weighting, response
RMSEs and rankings in the historical narrative below are legacy pre-purge
diagnostics under a superseded specification hash. They are preserved for an
auditable record of prior work, not as current results.

The pilot produced 5,488 crop-year feature rows, had no duplicate crop-year
grid keys, and passed nonnegative precipitation and stage-to-season
reconciliation checks. The exact ISIMIP/GDHY coordinate conversion was
validated; 43.4% of potential calendar cells in this pilot had an observed
GDHY yield. That coverage rate is a data-support diagnostic, not a global
agricultural coverage estimate.

The fixed-effects pilot fit exists only to test panel dimensionality and
numerical conditioning. Its coefficients and in-sample fit are not reported
in the manuscript and are prohibited from SCC integration by the validation
protocol.

The global maize/rainfed panel passed the same coordinate and uniqueness
checks and supported a scalable two-way within-estimator run. The three-window
stage panel has 1,618,080 rows and exactly reconciles to all 539,360
season-level records in crop-year days, wet-day counts, and maximum daily
rainfall; the largest precipitation-sum difference is 0.000855 mm from stored
floating-point precision. A stage-resolved fixed-effects diagnostic also ran
on the 120,325 observed-yield rows. Its numerical estimates remain
diagnostic-only and are not reported or used as SCC inputs.

The same maize/rainfed block now has an executable held-out predictive audit
using 105,157 consecutive-year observed-yield pairs. All three registered
models produced finite, full-rank fits in every split. The three-window joint
model had log-yield RMSE of 0.2945 in aggregated leave-one-spatial-fold-out
predictions, 0.3082 in the final-two-year block, and 0.2992 for pairs with a
climate-extreme endpoint, compared with 0.2971, 0.3088, and 0.3034 for the
seasonal joint model. The corresponding zero-change benchmarks were 0.3103,
0.3277, and 0.3163. These small predictive differences are a workflow and
specification-comparison diagnostic on one crop, one rainfed exposure proxy,
and eight years; coefficients are deliberately absent from the audit and the
metrics do not establish causality or support SCC integration.

The identical frozen diagnostic now covers all six available rainfed
crop-season panels and 321,620 consecutive-year pairs. The audit validator
confirmed the exact six-crop by three-model by three-holdout product, fold-row
reconciliation, common zero-change benchmarks, metric arithmetic, and finite
full-rank designs; the largest design condition number was 19.38. There was no
universal predictive winner. The three-window joint model had the lowest RMSE
in 11 of 18 crop/holdout comparisons, the seasonal joint model in five, and
the seasonal precipitation-only model in two. In second-season rice, only the
precipitation-only model beat zero change in the spatial audit, and no model
beat zero change in the temporal audit; the three-window model's temporal RMSE
was 0.2872 versus 0.2747 for zero change. Spring wheat also favored the simpler
precipitation-only model in its temporal block (RMSE 0.3487 versus 0.3688 for
the three-window model). These outcome-blind, retained unfavorable results
preclude choosing one response family from this eight-year diagnostic. They
do not supply coefficients, causal evidence, global external validity, or an
SCC input. The source artifact is generated at
`outputs/multicrop_noirr_1982_1989_response_evaluation.json` and validated into
`outputs/multicrop_noirr_1982_1989_response_summary.json`; both remain ignored
derived products and must be regenerated from the documented command.

The independent 1992–2000 maize/rainfed seasonal panel contains 606,780
potential crop-year records and 135,405 observed-yield records across 15,107
supported grid cells. It spans nine harvest years, has no duplicate crop-year
grid keys, assigns five deterministic spatial folds, reserves 1999–2000 as the
temporal holdout (22.2% of all rows), and flags 24.7% of all rows as a
climate-feature-defined dry-spell or heavy-rain case. The panel passed the
same precipitation/count/extreme invariants as the earlier block. These are
data-contract and validation-design checks only; no response coefficient from
this block is yet permitted in SCC calculations.

The same frozen coefficient-suppressing audit formed 119,950 consecutive-year
pairs in this independent period, and the complete audit validator passed with
a maximum design condition number of 13.83. The three-window joint model had
the lowest RMSE in spatial blocks (0.3273 versus a 0.3348 zero-change
benchmark) and climate-extreme cases (0.3228 versus 0.3266), but the
precipitation-only model led the temporal block (0.2836 versus 0.2882 for the
three-window model and 0.2883 for zero change). The precipitation-only model
also fell slightly behind zero change in the climate-extreme block (0.3267
versus 0.3266). Thus the stage model's temporal advantage in 1982–89 did not
replicate in 1992–2000. This is an intentionally retained diagnostic failure
of stable model ordering, not evidence for selecting period-specific models.
It supplies no coefficient or SCC input.

The matching three-window stage panel contains 1,820,340 rows and reconciles
to all 606,780 season-level records: crop-year days, wet-day counts, and
maximum daily rainfall agree exactly, and the largest precipitation-sum
difference is 2.27e-13 mm. A 15-feature stage-resolved within-estimator
diagnostic on the 135,405 observed-yield rows has full matrix rank and a
condition number of 21.9. This checks estimation plumbing and numerical
conditioning only; its coefficients and in-sample fit are prohibited from
causal interpretation, manuscript results, or SCC integration.

The decadal-file boundary was then closed with a real 1990–91 maize/rainfed
build. Its 134,840 season rows and 404,520 three-window rows reconcile exactly
for days, wet days, and Rx1day; the largest precipitation-total difference is
2.27e-13 mm. Rejoining all outcomes under the corrected GDHY zero semantics
and combining non-overlapping panels produced a contiguous 1982–2000 audit:
1,280,980 level rows, 285,871 positive observed-yield rows, and 270,273
consecutive-year pairs. The validator confirmed every harvest year from 1982
through 2000. Stage-joint was descriptively lowest-RMSE for spatial blocks
(0.3111 versus 0.3221 zero change) and climate-extreme pairs (0.3243 versus
0.3324 zero), while precipitation-only led the final-1999–2000 temporal block
(0.2833 versus 0.2878 stage-joint and 0.2883 zero). All models beat zero in the
spatial and temporal blocks, but precipitation-only was slightly worse than
zero for climate extremes (0.3341 versus 0.3324). This longer panel therefore
strengthens the evidence that timing/extreme features can add predictive
information without yielding a stable universal ranking. It is still one
crop, one rainfed-calendar proxy, an internal first-difference diagnostic, and
contains no released coefficient or SCC input.

An outcome-separate 2002–2010 soybean replication now contains 606,780
potential crop-year rows and 55,088 positive observed-yield rows. The source
has one additional nonmissing zero in 2007; GDHY documents that negative
aligned values were clipped to zero, so the join preserves the raw zero and a
machine-readable flag but excludes it from the log-yield outcome. Its
1,820,340 stage rows reconcile to every seasonal row: crop-year days,
wet-day counts, and Rx1day agree exactly, and the largest precipitation-total
difference is 2.27e-13 mm. The frozen diagnostic forms 48,959 consecutive
positive-yield pairs. All designs are finite and full rank (maximum condition
number 20.11). The stage-joint model is descriptively lowest-RMSE in spatial,
temporal, and climate-extreme holdouts (0.2143, 0.2406, and 0.2175) versus
zero-change benchmarks of 0.2202, 0.2493, and 0.2251. All three registered
models beat zero in all three blocks. This later-period result is consistent
with stage timing carrying predictive information for soybean, but it remains
one crop, a rainfed-calendar proxy, and an internal predictive audit. It does
not identify causal coefficients, resolve irrigation or drought-family
selection, or authorize an SCC response.

The soybean stage panel has the same 1,618,080-row structure and reconciles to
every season-level record in crop-year days, wet-day counts, and maximum daily
rainfall; its maximum precipitation-sum rounding difference is 0.000732 mm.
Its stage diagnostic uses the 48,900 supported yield rows and is likewise
prohibited from causal or SCC use.

The spring-wheat stage panel likewise has 1,618,080 rows and passed complete
stage-to-season reconciliation (maximum precipitation-sum rounding difference
0.000855 mm). Its stage diagnostic is limited to 40,977 supported yield rows
and remains prohibited from causal or SCC use.

The winter-wheat stage panel also has 1,618,080 rows and passed complete
stage-to-season reconciliation (maximum precipitation-sum rounding difference
0.000855 mm). Its stage diagnostic uses 68,778 supported yield rows and is
prohibited from causal or SCC use.

The first-rice panel has 539,360 potential crop-year records and 76,348
observed-yield records in the documented `rice_major` GDHY directory. It
passed the same feature-key and outcome-join checks. Its deterministic
validation labels assign five spatial folds, reserve 1988–89 as the temporal
holdout, and flag 28.1% of rows as a climate-feature-defined dry-spell or
heavy-rain case. The three-window stage panel has 1,618,080 rows and passed
complete stage-to-season reconciliation (maximum precipitation-sum rounding
difference 0.000732 mm). Season- and stage-level fixed-effects numerical
diagnostics completed only to check matrix dimensions and conditioning; their
estimates are not reported and are prohibited from causal interpretation or
SCC integration.

The second-rice panel has 248,040 potential crop-year records and 12,694
observed-yield records in the documented `rice_second` GDHY directory. It
passed feature-key and outcome-join checks. Its deterministic labels assign
five spatial folds, reserve 1988–89 as the temporal holdout, and flag 27.3%
of rows as climate-feature-defined dry-spell or heavy-rain cases. Its
season-level numerical diagnostic is only a matrix-dimension and conditioning
check; its estimates are not reported and are prohibited from causal
interpretation or SCC integration.

The second-rice three-window stage panel has 744,120 rows and passed complete
stage-to-season reconciliation (maximum precipitation-sum rounding difference
0.000419 mm). Its stage diagnostic uses the same 12,694 supported-yield rows
and remains prohibited from causal interpretation or SCC integration.

The combined six-crop-season rainfed panel retains maize, first/second rice,
soybean, spring wheat, and winter wheat as distinct crop/season labels. It
contains 2,944,840 potential crop-year records and 368,022 observed-yield
records. Its outcome-independent labels assign five spatial folds, reserve
1988–89 as the temporal holdout, and flag 27.1% of rows as a climate-feature-
defined dry-spell or heavy-rain case. Combining the data contract does not
license a common crop slope; the final response must use crop interactions or
pre-specified hierarchical partial pooling.

An executable outcome-independent validation panel has also been generated
for this pilot. It assigns deterministic 5° spatial blocks to five folds,
reserves 1988–89 as the temporal holdout (25% of rows), and labels grid-level
upper-tail dry-spell or heavy-rain cases from climate features alone (27.7% of
rows). It is a validation-design check, not a held-out performance result.

On 2026-08-17 the maize outcome join was changed from the undocumented
convenience `maize` directory to the documented season-specific `maize_major`
directory. This gives 120,325 observed rows and is the only permitted
maize-pilot outcome mapping going forward; the crosswalk and its limitation
for second maize seasons are recorded in `data/provenance/`.

This does not clear the main-analysis gate: remaining crop seasons/years,
crop-specific phenology, final heat features, production holdout performance
across the complete crop-period panel,
uncertainty, CO2 treatment, adaptation estimation, welfare translation, and
matched future baseline/pulse paths remain outstanding.

The executable integration scaffold now preserves crop/season coefficients
through the response step and rejects incomplete crop-value coverage by
default. Its tests use synthetic arrays only. Allowing partial coverage is
explicitly diagnostic; normalizing represented crops to the entire
agricultural value pool or reporting an SCC still requires a justified welfare
gap model and every empirical validation gate above.

The stage-heat workflow now mirrors the latitude-partitioned precipitation
pipeline and preserves crop/stage identity through the estimation-panel join.
Its test covers a cross-year crop season and verifies threshold-day,
degree-day, stage-length, and weighted-mean reconciliation. The shared
seasonal/stage validator also requires hotter-threshold day counts to nest
inside cooler-threshold counts and degree-day differences to lie inside their
necessary aggregate bounds. On a real 10-latitude maize/rainfed slice for
1982--89, 26,824 crop-year rows and 80,472 three-stage rows passed these gates
at 30 and 34 C; every additive metric reconciled exactly and the maximum
weighted-mean difference was 7.11e-15 C. Those two thresholds are pipeline-QA
inputs only, not a selected crop response specification. No production heat
threshold is encoded: thresholds remain an explicit, pre-registered response-
specification choice. The paired response-bundle gate is also executable on
CSV or Parquet inputs, but has been exercised only on synthetic arrays.

The historical scPDSI benchmark workflow maps monthly index values to the same
transparent crop-stage windows by exact day overlap. Its synthetic cross-year
test verifies stage lengths, day-weighted means, minima, monthly-index
threshold day-equivalents,
longitude normalization, partition combination, and one-to-one coverage. The
complete 355,230,575-byte CRU file is SHA-512/provenance verified, and the
source role explicitly prohibits using observed CRU scPDSI as a future
baseline/pulse input. Global 1982--1989 and 2012--2016 rainfed and fully
irrigated stage construction now passes for maize and soybean. A dedicated allocator builds 16
seasonal/stage scPDSI features separately by regime before fixed MIRCA-2000
weighting and emits no direct-weather terms. Source-bound raw-CRU/calendar
manifests plus complete derived-input allocation recomputation validate
240,784 maize rows with 115,758 positive outcomes and 176,537 soybean rows with
47,653 outcomes in 1982--1989, plus 150,490/59,772 and 110,336/26,601 in
2012--2016. Missing scPDSI or weight support removes a complete
crop-grid-year key rather than one regime, and every exclusion is audited. The
-2 threshold remains a diagnostic construction value. A downstream
coefficient-suppressing predictive diagnostic has fit the competing historical
families internally and reports aggregate held-out metrics only; it emits no
coefficient and selects no production drought family. Matched future drought
paths remain open.

The subsequent common-support assembly emits the direct-weather and scPDSI
families as separate, non-stacked views with 54 and 16 features, respectively.
The exact common rows/observed outcomes and direct-only rows/observed outcomes
are 240,784/115,758 and 24,744/1,921 for maize 1982--1989;
176,537/47,653 and 14,935/269 for soybean 1982--1989;
150,490/59,772 and 15,465/1,046 for maize 2012--2016; and
110,336/26,601 and 9,334/147 for soybean 2012--2016. scPDSI-only drops are
zero rows and zero observed outcomes in every bundle. Validation recomputes
these data-only views from their immediate inputs and verifies input/output
hashes. It does not rerun upstream raw sources or bind upstream validation
receipts, so upstream validation with retained receipts remains an external
prerequisite. The bundles themselves fit no model and produce no coefficient,
causal effect, model-selection, future-projection, damage, or SCC result. Their
separate downstream diagnostic reports only aggregate historical predictive
metrics under the limitations recorded in the results table above.

The executable outcome-exposure allocator now prevents pseudo-replication of
GDHY's aggregate crop-season yield across rainfed and irrigated calendar rows.
Its synthetic suite verifies successful fixed-share aggregation and rejects
non-unit shares, year-varying weights, outcome-derived source roles, missing
regime exposures, inconsistent duplicated yields, duplicate keys, and source
mappings marked production-ineligible.

The independent source gate is now closed for maize and soybean with MIRCA-OS
v2 annual harvested-area grids. The verified 2000 source contains 33,362
maize and 24,054 soybean crop cells; its area-weighted irrigated shares are
0.2112 and 0.0822, respectively. Exact coordinate joins cover 14,765 of 15,098
observed-yield maize cells and 6,000 of 6,123 soybean cells in the existing
1982--89 panels. Missing cells are not infilled or renormalized. Fixed 2005,
2010, 2015, and 2020 vintages are built for sensitivity analysis. Annual rice
and wheat parent-crop maps cannot distinguish `ri1`/`ri2` or `swh`/`wwh`; the
builder marks those mappings production-ineligible and the allocator rejects
them. These are source and coverage diagnostics, not a yield response or SCC
input.

Matching maize and soybean fully irrigated calendar exposures are now built
for 1982--1989 and reconcile exactly to their season summaries. Fixed-2000
MIRCA source/coverage allocation retains 117,679 maize and 47,922 soybean
observed outcomes, with every missing-weight outcome counted and removed as a
complete key. The first area-weighted held-out runs are quarantined because
they averaged primitive rainfed/irrigated weather and only then constructed
`log1p` precipitation and temperature--precipitation interactions. Nonlinear
bases do not commute with area weighting, and the post-aggregation interaction
also introduces cross-regime products. The associated model rankings and RMSE
comparisons are therefore withdrawn, including all four later-vintage reruns.
The corrected design constructs each complete nonlinear basis within regime,
then applies one fixed MIRCA vintage and sums across regimes. Primitive-weather
mode rejects area-weighted panels; the explicit prebuilt-basis mode consumes
the supplied basis without overwriting it. Under the current hash and purged
splits, the corrected 2000-vintage maize and soybean diagnostics validate
102,847 and 41,915 consecutive pairs with zero endpoint overlap. Stage-joint
is descriptively best spatially and for climate-extreme pairs in both crops;
seasonal-joint leads the temporal block, essentially tied for maize. These
runs are limited predictive diagnostics and produce no causal coefficient,
damage, or SCC input.

A separate locked diagnostic now holds seasonal `log(1 + precipitation)`
quantity fixed while adding normalized timing/concentration, wet-day
occurrence and conditional intensity, dry-spell fractions, and Rx1day/Rx5day
sets. A full validator reruns the regression from the exact hash-locked source
panels rather than merely checking reported arithmetic. The best distribution
candidate lowers pooled RMSE relative to seasonal quantity in all six
crop-by-holdout comparisons, by 0.00117--0.00138 for maize and
0.00084--0.00261 for soybean. This is not uniform across model sets: the full
distribution model is 0.00355 worse than seasonal quantity in the soybean
temporal block, and fold/year signs vary. No paired uncertainty or
multiple-comparison correction has been applied. The so-called extreme label
is a retrospective high-tail stress split containing about 47% of pairs
because either endpoint may cross either within-cell CDD or Rx1day threshold;
it is not rare-event or prospective validation. These results are screening
evidence only and release no coefficient, damage, or SCC input.

The same frozen comparison has now been independently recomputed for real
2012--2016 aggregate-regime panels. It covers 60,818 maize levels and 46,434
consecutive pairs, plus 26,748 soybean levels and 20,682 pairs. No distribution
family improves on seasonal quantity in all three holdouts for either crop.
For maize, every extension worsens spatial and temporal RMSE; the only gain is
0.000044 for timing/concentration in the high-tail split, while the full set is
0.004826 worse temporally. For soybean, dry spells improve spatial RMSE by
0.001516 and occurrence/intensity improves high-tail RMSE by 0.001366, but
every extension is worse temporally and the full set is 0.003491 worse. The
maize temporal block is more adverse still: zero change has RMSE 0.267661,
better than temperature only, seasonal quantity, or any distribution model.
The high-tail label includes 66.15% of maize pairs and 66.39% of soybean pairs
in this short panel and is not rare-event validation.

The official GDHY archive also shows a 2015-only positive-support drop that is
fully restored in 2016 (1,791 maize-major and 596 soybean grid cells). A
complete-positive-support sensitivity is therefore reported without imputing
or relabeling values. It retains 87.06% of maize levels and 91.23% of maize
pairs, and 91.07% and 94.23% for soybean. Seasonal joint
temperature--quantity is lowest-RMSE in all six balanced-sample comparisons,
but conditioning on complete source support may itself select a
nonrepresentative sample. Together, the later-period and support-sensitivity
results favor the parsimonious quantity reference for continued work while
leaving drought-index families as genuine competitors. They remain
predictive, not causal or SCC evidence.
