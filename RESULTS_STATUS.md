# Analysis status and claim ledger

Updated: 2026-08-26. This file records completed computational milestones; it
does not report final response estimates or SCC values.

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
| Global maize/rainfed, 1992–2000 | Season-level and three-window temporal-proxy stage panels, GDHY join, deterministic validation labels, reconciliation, and fixed-effects numerical diagnostic complete: 606,780 potential crop-year rows; 135,405 observed-yield rows across 15,107 cells | Independent-period workflow/coverage diagnostic only; no SCC input |
| Global soybean/rainfed, 1982–89 | Season-level and three-window temporal-proxy stage panel, GDHY join, and deterministic validation labels complete: 539,360 potential crop-year rows; 48,900 observed-yield rows across 6,123 cells | Workflow/scaling diagnostic only; no SCC input |
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
| Historical crop-stage scPDSI path | The complete 1903--2025 CRU scPDSI file is acquired, SHA-512 recorded, and provenance-verified. Synthetic cross-year construction, longitude/grid matching, coverage, partition/combine, and join tests pass; a real 10-latitude maize/rainfed 1982--89 partition produced and validated 36,183 crop-stage rows | Historical climatic-index benchmark only; the -2 threshold is a diagnostic setting, the global crop panels and response comparison are incomplete, and no future drought path or SCC input exists |
| Rainfed/irrigated outcome-allocation gate | Synthetic fixed-baseline area-share allocation and failure-mode tests pass; one aggregate GDHY yield is collapsed to exactly one weighted-exposure row | Data-contract plumbing only; no production area weights, irrigated response, coefficient, or SCC input |
| U.S. county crop-season drought bridge | Synthetic cross-year USDM interval aggregation and failure-mode tests pass using an explicit state/crop/harvest-year calendar; the authorized key-safe Quick Stats fallback passed a real locked 2020 corn-grain smoke with 1,699 unique county-year yield rows | Historical external-validation input/plumbing only; no crop-area weather exposure, irrigation-screened panel, response estimate, or SCC input is created |
| Maize/rainfed blocked response audit, 1982–89 | 105,157 consecutive observed-yield pairs evaluated with crop-specific first-difference seasonal-precipitation, seasonal-joint, and three-window-joint models across spatial, temporal, and climate-extreme holdouts | Internal predictive diagnostic only; coefficients are suppressed and no causal, global-response, or SCC claim is permitted |
| Six-crop/rainfed blocked response audit, 1982–89 | 321,620 consecutive observed-yield pairs across maize, first/second rice, soybean, spring wheat, and winter wheat; exact crop/model/holdout coverage, metric arithmetic, fold reconciliation, and full-rank finite fits validated | Internal predictive diagnostic only; mixed crop/holdout rankings prohibit a universal-model or SCC claim |
| Maize/rainfed independent-period audit, 1992–2000 | 119,950 consecutive observed-yield pairs; the frozen models and validator rerun without using the 1982–89 outcome metrics | Internal predictive replication only; model ordering changes in the temporal block and no coefficient or SCC use is permitted |
| Maize/rainfed contiguous-period audit, 1982–2000 | Cross-file daily input and strict period-combination gates close 1990–91 and validate all 19 harvest years: 1,280,980 potential rows, 285,871 positive-yield rows, and 270,273 consecutive pairs | Longer-period internal predictive diagnostic only; mixed holdout rankings, rainfed-calendar exposure, and coefficient suppression prohibit causal or SCC use |
| Soybean/rainfed independent-period audit, 2002–2010 | Season and three-window panels contain 606,780 and 1,820,340 rows and reconcile exactly within stored precision; the frozen audit validates 48,959 consecutive observed-yield pairs | Internal predictive replication only; one source-zero GDHY value is preserved and excluded from log yield, coefficients remain suppressed, and no causal or SCC use is permitted |
| Matched future climate-feature driver | Frozen official catalogue selects the complete five-ESM/member by four-scenario by four-variable matrix: 80 public/unrestricted CC0 version-`20210512` datasets and 1,756,959,247,729 catalogue bytes. A pinned MRI-ESM2-0 SSP3-7.0 precipitation sidecar plus 64 KiB HDF5-header range passed. Synthetic executable gates enforce same-realization GMST, whole-ESM/scenario holdouts, common residuals, separate support flags, zero-pulse/pre-divergence identity, and three-size convergence. | Metadata and bounded-header engineering evidence only; the complete smoke file and projection matrix are not acquired, no full SHA-512/content/chronology validation or real holdout has run, and no fitted response, paired feature path, damage, or SCC input exists |
| Irrigated panels, full-period multi-crop coverage, and future scenarios | Not yet complete | No production global response or SCC claim |

## Completed empirical checks

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

The historical scPDSI benchmark workflow now maps monthly index values to the
same transparent crop-stage windows by exact day overlap. Its synthetic
cross-year test verifies stage lengths, day-weighted means, minima, drought-day
counts, longitude normalization, partition combination, and one-to-one panel
coverage. The source-role field explicitly prohibits using observed CRU scPDSI
as a future baseline/pulse input. The complete 355,230,575-byte CRU file is now
acquired and SHA-512/provenance verified. A real 10-latitude maize/rainfed
1982--89 slice produced 36,183 crop-stage rows and passed the partition gate at
a diagnostic scPDSI threshold of -2. This establishes real-data execution, not
a selected drought definition or a drought-response result; the global crop
panels, response comparison, and matched future drought paths remain open.

The executable outcome-exposure allocator now prevents pseudo-replication of
GDHY's aggregate crop-season yield across rainfed and irrigated calendar rows.
Its synthetic suite verifies successful fixed-share aggregation and rejects
non-unit shares, year-varying weights, outcome-derived source roles, missing
regime exposures, inconsistent duplicated yields, and duplicate keys. The
gate requires a separately acquired independent baseline crop-area-share
source before it can process real irrigated/rainfed panels; it therefore does
not change the rainfed-only diagnostics or authorize a production response.
