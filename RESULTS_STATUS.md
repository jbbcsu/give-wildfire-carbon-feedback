# Analysis status and claim ledger

Updated: 2026-08-21. This file records completed computational milestones; it
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
| Global soybean/rainfed, 1982–89 | Season-level and three-window temporal-proxy stage panel, GDHY join, and deterministic validation labels complete: 539,360 potential crop-year rows; 48,900 observed-yield rows across 6,123 cells | Workflow/scaling diagnostic only; no SCC input |
| Global spring-wheat/rainfed, 1982–89 | Season-level and three-window temporal-proxy stage panel, GDHY join, and deterministic validation labels complete: 539,360 potential crop-year rows; 40,977 observed-yield rows across 5,127 cells | Workflow/scaling diagnostic only; no SCC input |
| Global winter-wheat/rainfed, 1982–89 | Season-level and three-window temporal-proxy stage panel, GDHY join, and deterministic validation labels complete: 539,360 potential crop-year rows; 68,778 observed-yield rows across 8,668 cells | Workflow/scaling diagnostic only; no SCC input |
| Global first-rice/rainfed, 1982–89 | Season-level and three-window temporal-proxy stage panel, GDHY join, deterministic validation labels, reconciliation, and fixed-effects numerical diagnostics complete: 539,360 potential crop-year rows; 76,348 observed-yield rows across 9,564 cells | Workflow/scaling diagnostic only; no SCC input |
| Global second-rice/rainfed, 1982–89 | Season-level and three-window temporal-proxy stage panel, `rice_second` GDHY join, deterministic validation labels, reconciliation, and fixed-effects numerical diagnostics complete: 248,040 potential crop-year rows; 12,694 observed-yield rows across 1,587 cells. | Workflow/scaling diagnostic only; no SCC input |
| Six-crop-season rainfed panel, 1982–89 | Combined seasonal data contract and outcome-independent validation labels complete: 2,944,840 potential crop-year rows; 368,022 observed-yield rows. Crop/season identity and source panel are retained. | Data-contract and validation scaling diagnostic only; no common-slope or SCC input |
| Other crops/periods/scenarios | Not yet complete | No global response or SCC claim |

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
crop-specific phenology, final heat features, pre-specified
holdout performance results,
uncertainty, CO2 treatment, adaptation estimation, welfare translation, and
matched future baseline/pulse paths remain outstanding.
