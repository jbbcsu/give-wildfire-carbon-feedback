# GIVE precipitation and hydrologic-damages extension

This directory is a standalone research/implementation track for adding the
marginal damages of CO2-induced precipitation change to GIVE's social cost of
carbon (SCC).  It does not modify or import any wildfire/biomass-burning work.
The files here are specifications and an unintegrated component interface;
they are intentionally not wired into the baseline model.

## Current boundary

The first build prioritizes **global agricultural damages from precipitation
patterns**—seasonality, timing, dry spells, wet-day frequency, and extremes—in
a joint temperature--precipitation response. Coastal storm-surge and
sea-level-rise costs remain the responsibility of CIAM. Inland flood/built
infrastructure is a secondary, separately accounted track. Agricultural
damages must replace, not be added to, the current temperature-indexed MooreAg
sector, which has no explicit separable precipitation input in this checkout.

See [PLAN.md](PLAN.md) for the phased protocol, [SOURCES.md](SOURCES.md) for
authoritative inputs, and [src/PrecipitationDamages.jl](src/PrecipitationDamages.jl)
for the isolated Mimi component contract.  The literature-first recommendation
and ML contingency are in [AGRICULTURE_RESEARCH.md](AGRICULTURE_RESEARCH.md).
The climate-emulation literature and published-method reuse decision are in
[CLIMATE_PRECIPITATION_EMULATOR_AUDIT.md](CLIMATE_PRECIPITATION_EMULATOR_AUDIT.md).
The reviewed USEPA annual pattern-scaling workflow is retained as a distinct
external benchmark and FAIR--GCM pairing sensitivity in
[EPA_PATTERN_SCALING_BENCHMARK.md](EPA_PATTERN_SCALING_BENCHMARK.md); it is not
the primary crop-feature driver or an additional damage term.
Local storage is governed by the machine-readable eviction receipt at
`data/provenance/local_isimip3b_raw_eviction_20260903.json`. Sixty completed,
checksum-verified public ISIMIP source files were removed after their derived
features and provenance were preserved, reclaiming 124.6 GB. Their absence is
intentional and must not trigger automatic reacquisition. Rehydrate a recorded
file only for a specific unfinished downstream calculation, verify it against
the retained byte/SHA-512 contract, process it sequentially, and evict it again
after the new derived output is validated.
The primary matched baseline/pulse route and its acquisition/validation gates
are fixed in [PAIRED_CLIMATE_FEATURE_DRIVER.md](PAIRED_CLIMATE_FEATURE_DRIVER.md):
derive the exact crop features from version-pinned daily ISIMIP3b fields, fit
ESM-specific feature responses to same-realization GMST, and evaluate matched
FAIR paths with common random numbers. Scenario differences are training data,
not one-tonne CO2 experiments.
The outcome-blind selection is now frozen to the five complete ISIMIP3b ESM
realizations across historical, SSP1-2.6, SSP3-7.0, SSP5-8.5 and the four daily
variables (80 version-`20210512` datasets). Bounded complete-file `pr`/`tas`
coverage now includes historical plus all three SSPs for all five frozen ESM
realizations. Every available file is API-identity/version/checksum bound and
passes decoded global-grid, units, exact daily chronology, missingness, and
physical-value gates. Same-realization annual GMST and two-latitude
maize/rainfed feature cells pass for every bounded scenario. MRI's newly closed
SSP1-2.6 and SSP5-8.5 block adds four complete files (4,953,940,488 bytes) and
its exact historical/four-scenario product passes 44 whole-scenario engineering
folds; the simple GMST adjustment improves 24 folds, with median RMSE ratio
0.99971 and worst ratio 1.09903, so it is not promoted. The UKESM expansion
adds six complete files (6,680,992,736 bytes), exact historical/future
boundaries, same-realization GMST, and exact-reconciliation feature cells. Its
four-scenario diagnostic improves 23/44 folds (median RMSE ratio 0.99985;
worst 1.03248). The exact five-ESM joint product has 565,950 rows. Whole-ESM
folds improve 41/55 (median 0.99760; worst 1.05145) and whole-scenario folds
improve 36/44 (median 0.99744; worst 1.01605). It remains an engineering gate
and is not promoted. These
are seven-year, one-crop/two-latitude engineering smokes, not acquisition of
the 1.757 TB matrix or a production feature response. A separate
area-unweighted aggregate numerical smoke produces 880 common-residual
baseline/pulse rows across all 55 ESM-feature fits. Zero-pulse and
pre-divergence identity, separate support flags, direct/centered agreement, and
three decreasing positive pulse scales pass; 19 pulse rows are above and 10
below bounded training support. These artificial Kelvin perturbations are not
FAIR paths. Actual FAIR pairing, spatial support, and production convergence
remain open.
The core deterministic GIVE/FAIR marginal API is now separately pinned and
reproduced for a 2020 CO2 pulse: 2,204 matched temperature rows cover
1750--2300 for zero plus 0.0001/0.00005/0.000025 GtC pulses. Baselines are
identical across runs, zero and pre-pulse paths are exact, temperature first
diverges in 2021, and normalized smallest-pulse signals converge. The maximum
0.0001-GtC temperature difference is 1.8368e-7 K. This validates the actual
FAIR temperature-delta input only; ESM baseline alignment, feature levels,
support, damages, and SCC remain unauthorized.
A version-pinned alignment sensitivity now maps the same FAIR paths onto each
ESM using a 2012--2014 historical overlap mean. For the bounded affine feature
surface, absolute anomaly mapping and centered-coordinate evaluation are
algebraically equivalent: all 127,160 paired rows pass common-residual,
zero-pulse, pre-divergence, support, direct/centered, and decreasing-pulse
gates, and the largest method disagreement is `4.55e-12`. This does not select
the reference window or promote the surface. Only 3,784 of 63,580 temperature
rows per formulation (5.95%) remain within the seven-year GMST training range;
22,824 feature rows (35.90%) remain within bounded feature support. The result
therefore diagnoses extrapolation rather than authorizing production use. The
mapped FAIR baseline first exceeds bounded GMST support in 2021 for GFDL, 2027
for MPI, and 2033 for IPSL, UKESM, and MRI.
Joining the complete early-, mid-, and end-century bounded products yields a
deterministic 2,376,990-row, 23-year training surface. Re-evaluating the same
FAIR common-random-number paths against that enlarged surface produces 127,160
paired rows. All 63,580 feature values per alignment method are within bounded
feature support; 63,536/63,580 mapped temperature rows are within support, with
only MPI in 2012 below its envelope. Zero-pulse and pre-divergence identity,
separate baseline/pulse flags, direct/centered agreement, and decreasing-pulse
convergence pass, and maximum alignment-method disagreement is `2.56e-13`.
This closes a bounded aggregate feature-support engineering gate only: the
affine surface was not promoted by holdout evidence, represents one crop/regime
and two latitude rows, and has no direct daily support after 2100. Response,
damage, welfare, and SCC use remains unauthorized.
The first registered multi-crop expansion now adds first- and second-season
rice, soybean, spring wheat, and winter wheat rainfed-calendar cells plus a
soybean irrigated-calendar cell for UKESM midcentury SSP1-2.6/SSP5-8.5. All
six pass exact seasonal/stage reconciliation and checksum-bound provenance;
second-season rice's lower 3,264-row support is explicit. Rainfall, dry-spell,
extreme-rain, and timing changes are heterogeneous across crops, while the
soybean irrigation contrast is explicitly a calendar sensitivity rather than
a treatment effect. See
[ISIMIP3B_MULTICROP_SUPPORT_AUDIT.md](ISIMIP3B_MULTICROP_SUPPORT_AUDIT.md).
No response, damage, or SCC gate is opened.
The next response candidate is preregistered, not fitted: a pathway-aware
ridge basis with continuous same-realization GMST level/change and time terms,
partially pooled ESM deviations, no scenario categorical shortcut, nested
whole-ESM/whole-scenario selection, and strict actual-FAIR pulse gates. See
[STRUCTURAL_FEATURE_RESPONSE_CANDIDATE.md](STRUCTURAL_FEATURE_RESPONSE_CANDIDATE.md).
The first nested real evaluation improves 71/88 comparisons and passes the
median criterion (RMSE ratio 0.99443), but fails the maximum criterion (1.00703)
and produces 85 negative feature predictions. It is not promoted. All
production gates remain closed.
Before examining another fit, a physical-link successor was frozen in
[PHYSICAL_LINK_FEATURE_RESPONSE_CANDIDATE.md](PHYSICAL_LINK_FEATURE_RESPONSE_CANDIDATE.md).
It retains the same continuous pathway basis and nested whole-ESM/whole-
scenario design, but uses positive log links, bounded logits, and a joint
centered-log-ratio stage-share composition. Lambda selection and promotion are
scored after inversion on the original physical scale. Its locked evaluation
improves only 34/88 comparisons; median and maximum RMSE ratios are 1.00775 and
1.13855. Physical bounds and stage-share sums pass, but predictive promotion
criteria fail. It is rejected, and the actual FAIR pulse path was not run.
A literature-constrained review now selects published RIME-X v1.0 as the next
direct-feature benchmark rather than tuning a third response to these results.
Its exact article/software identities and a synthetic common-random-number
interpolation smoke are frozen in
[RIMEX_FEATURE_RESPONSE_BENCHMARK.md](RIMEX_FEATURE_RESPONSE_BENCHMARK.md).
The real fit is deliberately blocked: the published method uses 21-year
smoothing but the bounded training years are discontinuous, and its univariate
quantile maps do not preserve the joint crop-feature dependence needed for
agriculture. No FAIR feature response, damage, or SCC gate is opened.
The first outcome-blind repair is metadata-pinned before acquisition: a
GFDL-ESM4/SSP1-2.6 `pr`/`tas` pilot spanning 2031--2060. Its 28 consecutive
crop-feature years can yield exactly eight centered 21-year outputs for
2042--2049. The six official CC0 version-`20210512` files total 12.385 GB;
all six files, 30 annual same-realization GMST values, 28 crop years, exact
unsmoothed reconciliation, and the centered-window mechanics now pass the
bounded gate.
This pilot cannot by itself clear whole-ESM, whole-scenario, joint-dependence,
response, damage, or SCC gates; see [RIMEX_CONTIGUOUS_PILOT.md](RIMEX_CONTIGUOUS_PILOT.md).
Before any joint fit, [RIMEX_JOINT_DEPENDENCE.md](RIMEX_JOINT_DEPENDENCE.md)
registers ECC-Q empirical-copula coupling on physically constrained rainfall,
extreme, temperature, and stage-composition coordinates. Synthetic mechanics
preserve every marginal multiset and the complete rank template with zero
physical failures. The pilot has only eight distinct templates versus the
locked 51-template minimum, so real dependence and FAIR gates remain closed.
Before constructing another feature table, the complete six-crop by two-
calendar-regime expansion on this same contiguous realization is fixed in
[RIMEX_CONTIGUOUS_MULTICROP_REGIME.md](RIMEX_CONTIGUOUS_MULTICROP_REGIME.md).
It locks all 12 calendar hashes, bounded support counts, 28 annual feature
years, eight centered years, common same-realization GMST, and exact
reconciliation. Irrigated/rainfed contrasts remain calendar sensitivity checks,
not treatment effects. All 214,928 seasonal and 644,784 stage rows pass, as do
61,408 centered seasonal and 184,224 centered stage rows. The paired calendar
contrasts are heterogeneous across crops, while the two rice pairs are
identical on this bounded support. All response, damage, and SCC gates remain
closed.
The preregistered GFDL-ESM4 SSP3-7.0 and SSP5-8.5 replications now pass the
same complete 2031--2060 source, feature, reconciliation, and calendar-regime
gates. Each scenario's 12 cells contain 214,928 seasonal, 644,784 stage,
61,408 centered seasonal, and 184,224 centered stage rows tied to its own
same-realization GMST series. In SSP5-8.5, `firr` minus `noirr` centered
seasonal rain ranges from -22.21 to +13.80 mm across crops, while both rice
pairs remain identical. The three completed GFDL scenarios provide only 24
center-year templates, still below the locked 51-template dependence minimum
and without a whole-ESM holdout; this remains support evidence only.
The first cross-ESM contiguous replication, IPSL-CM6A-LR `r1i1p1f1`
SSP1-2.6, now passes the same six-file 2031--2060 content gate and all 12
crop-by-calendar feature gates. It adds 214,928 seasonal, 644,784 stage,
61,408 centered seasonal, and 184,224 centered stage rows, with a common
30-year same-realization GMST series and a byte-identical aggregate audit.
Centered `firr` minus `noirr` seasonal-rain differences range from -23.71 to
+12.66 mm across crops; the two rice pairs are identical. Across the three
GFDL scenarios and this IPSL scenario, only 32 centered templates exist, so a
balanced whole-ESM/scenario holdout, response, damage, and SCC claim remains
closed.
The matching IPSL-CM6A-LR SSP3-7.0 replication now passes the same six-file,
30-year GMST, 12-cell feature, reconciliation, and deterministic-audit gates.
It adds another 214,928 seasonal, 644,784 stage, 61,408 centered seasonal, and
184,224 centered stage rows. Centered `firr` minus `noirr` seasonal-rain
differences range from -25.10 to +12.80 mm across crops, while both rice pairs
remain identical. The IPSL-CM6A-LR SSP5-8.5 replication subsequently passes
the same gates and row counts with its own same-realization GMST series and a
byte-identical aggregate-audit rerun. Its centered calendar-only seasonal-rain
differences range from -25.94 to +12.50 mm, again with identical rice pairs.
In the exact-key 2032--2059 comparison with IPSL SSP1-2.6, SSP5-8.5 is
0.580--0.836 C warmer and seasonal rain changes range from -5.07 to +12.62 mm
across the 12 cells; these are descriptive climate-feature differences, not
crop responses.
The completed contiguous design therefore contains 48 center-year templates:
three scenarios for each of two ESMs. It is still below the locked 51-template
dependence minimum, and holding out either ESM leaves only 24 training
templates while holding out one scenario leaves 32. Joint-dependence,
whole-ESM/scenario response, damage, and SCC use therefore remain closed.
The preregistered MPI-ESM1-2-HR `r1i1p1f1` SSP1-2.6 cell now passes the same
six-file checksum/content, 30-year same-realization GMST, 12-cell feature,
reconciliation, and byte-identical aggregate-audit gates. It adds 214,928
seasonal, 644,784 stage, 61,408 centered seasonal, and 184,224 centered stage
rows. Centered `firr` minus `noirr` seasonal-rain differences range from
-22.48 to +14.72 mm across crops, with both rice pairs identical. The matrix
now has 56 templates in total, above the unconditional 51-template minimum,
but it remains unbalanced: holding out MPI leaves 48 templates, holding out
GFDL or IPSL leaves 32, and holding out SSP1-2.6 leaves 32. Joint-dependence
fitting, whole-ESM/scenario promotion, response, damage, and SCC use remain
closed until the registered balanced holdouts can be run.
The matched preregistered MPI SSP3-7.0 cell now passes the same six-file,
same-realization GMST, 12-cell, reconciliation, and deterministic-rerun gates,
with the same 214,928/644,784 raw and 61,408/184,224 centered row counts.
Calendar-only `firr` minus `noirr` centered seasonal-rain differences range
from -21.76 to +11.22 mm across crops, with both rice pairs identical. The
matrix now has 64 templates, but every whole-ESM or whole-scenario exclusion
retains only 40--48, below the locked 51-template minimum. Joint dependence,
holdout promotion, response, damage, and SCC use therefore remain closed.
The preregistered MPI SSP5-8.5 cell also passes all six checksum/content,
30-year same-realization GMST, 12-cell feature, exact reconciliation, and
byte-identical aggregate-audit gates. It contributes the same raw and centered
row counts. Calendar-only `firr` minus `noirr` centered seasonal-rain
differences are +0.85 mm for maize, -14.35 mm for soybean, zero for both rice
seasons, +12.62 mm for spring wheat, and -23.99 mm for winter wheat. The
matrix now has 72 templates, but excluding any ESM or scenario retains only 48,
below the locked 51-template minimum. Joint-dependence fitting, whole-ESM and
whole-scenario promotion, response, damage, and SCC use remain closed.
The MRI-ESM2-0 `r1i1p1f1` SSP1-2.6 cell next passes the same six-file,
same-realization GMST, 12-cell, exact-reconciliation, and deterministic-rerun
gates, adding the same raw and centered row counts. Calendar-only `firr` minus
`noirr` centered seasonal-rain differences range from -28.16 to +13.80 mm,
with both rice pairs identical. The matrix now has 80 templates. Whole-ESM
exclusions retain 56--72 templates and SSP3-7.0 or SSP5-8.5 exclusions retain
56, but an SSP1-2.6 exclusion retains only 48. The balanced preregistered
matrix remains incomplete, so joint dependence, holdout promotion, response,
damage, and SCC use remain closed.
The MRI-ESM2-0 `r1i1p1f1` SSP3-7.0 cell also passes the frozen six-file
checksum/content, same-realization 30-year GMST, 12-cell raw/centered,
exact-reconciliation, and byte-identical aggregate-audit gates. It contributes
214,928 seasonal, 644,784 stage, 61,408 centered-seasonal, and 184,224
centered-stage rows. Calendar-only `firr` minus `noirr` centered seasonal-rain
differences range from -22.93 to +13.08 mm, with both rice pairs identical;
these are calendar contrasts, not irrigation treatment effects. The available
matrix now has 88 templates. Excluding any represented ESM leaves 64--72
training templates, while excluding a scenario leaves 56--64, so every
currently represented exclusion is numerically above the locked 51-template
minimum. UKESM1-0-LL still has no contiguous feature templates and the balanced
five-ESM matrix remains incomplete; joint dependence, holdout promotion,
response, damage, and SCC use therefore remain closed.
The completed-matrix inventory is independently regenerated by
`scripts/audit_isimip3b_rimex_contiguous_completed_matrix.py`; its tracked
receipt binds every contributing config and aggregate audit by SHA-256 and
lists the four missing ESM/scenario cells without fitting a model.
An outcome-blind dependence-stability diagnostic was then registered and its
implementation committed before reading the real templates. It processes all
88 centered-year templates from derived Parquet files, one crop/regime file
pair and center-year block at a time, and compares median within-template
Spearman matrices under represented whole-ESM and whole-scenario exclusions.
Six of seven exclusions pass the locked tolerances. MRI-ESM2-0 fails the
maximum-difference gate: its wet-frequency versus Rx1-given-Rx5 correlation
changes by 0.192318, above the fixed 0.15 limit. The other three ESM and all
three scenario exclusions pass, and no strong-pair sign flip occurs. Maximum
observed peak RSS across two deterministic runs is 187,662,336 bytes, below the
2 GiB gate. This adverse structural diagnostic
is not an ECC-Q fit and does not open joint-dependence, FAIR, response, damage,
or SCC gates; no tolerance was retuned.
The locked follow-up decomposition then tests whether MRI's missing SSP5-8.5
cell alone explains that failure. Restricting both MRI and the other three ESMs
to their common SSP1-2.6/SSP3-7.0 support reduces the focal difference only
from 0.192318 to 0.173654, still above the unchanged 0.15 gate. The two
scenario-specific differences are 0.163224 and 0.204990; all eight center-year
comparisons exceed 0.15. Ten of twelve crop/calendar-regime cells also exceed
the gate, while both winter-wheat cells are below it (0.070128 irrigated
calendar and 0.084917 rainfed calendar). Scenario imbalance is therefore not
sufficient to explain the MRI instability, although crop heterogeneity is
material. This remains a descriptive decomposition and opens no downstream
gate.
A separately preregistered receipt-only decision audit then compares pooled
and ESM-conditional dependence pools without reading derived Parquet or fitting
a model. The pooled sample has 88 templates, above 51, but fails the complete
five-ESM/three-scenario requirement and retains the unresolved MRI stability
failure. Each complete ESM-conditional pool would contain only 24 templates
under the frozen eight-center-year design, 27 below the locked 51-template
minimum. No current pool is permitted for dependence fitting, FAIR evaluation,
response estimation, damage, or SCC use.
An initial receipt-only temporal count is explicitly withdrawn because it
incorrectly assigned 21-year windows to legacy annual one-crop/regime holdout
rows. The corrected, separately preregistered compatibility-first audit counts
only the centered 21-year linked multicrop/regime RIME-X products. Their 88
nominal templates comprise eight overlapping center years in each of 11
completed ESM--scenario cells, so at most 11 are pairwise nonoverlapping.
Completing all 15 cells would raise that upper bound only to 15; future
whole-ESM and whole-scenario bounds would be 12 and 10. The 2,376,990 legacy
early/mid/end rows contribute zero compatible dependence templates. Pairwise
nonoverlap is itself only an upper bound on independence, and no fit or
downstream gate opens.
A separately preregistered metadata-only feasibility audit identifies the
smallest balanced expansion that can clear the locked count after structural
holdouts: seven ESM-member tracks, three SSPs, and four pairwise-nonoverlapping
21-year windows produce 84 compatible templates. Whole-member, worst-case
whole-ESM-family (with at most two members from one family), and whole-scenario
holdouts retain 72, 60, and 56 templates. Six tracks retain only 48 after the
limiting family or scenario holdout. This arithmetic selects no ESM member or
file, checks no new catalogue availability, estimates no bytes, and authorizes
no acquisition, fit, response, damage, or SCC work.
A separately preregistered live official-catalogue screen then queried all six
SSP-by-variable cells without pre-filtering climate forcing or ensemble member.
Only five complete ESM-member tracks are available across SSP1-2.6, SSP3-7.0,
SSP5-8.5, daily `pr`/`tas`, and the four nonoverlapping 21-year windows, versus
the locked minimum of seven. The complete five-track pool comprises 30 datasets
and 270 public, unrestricted CC0 version-`20210512` files totaling
536,861,000,440 catalogue bytes. The track-count gate therefore fails before
storage or fitting; no ensemble is selected and no payload is downloaded.
A pre-acquisition contiguous holdout matrix now pins all 90 version-`20210512`
files needed for five ESMs, three scenarios, `pr`/`tas`, and 2031--2060. The
public, unrestricted CC0 matrix totals 187.139 GB. If every content and feature
gate passes, it yields 120 complete centered templates; a whole-ESM holdout
retains 96 training templates and a whole-scenario holdout retains 80, both
above the locked 51-template minimum nominally. Because the eight centers
overlap, the corrected distinctness audit does not count these as independent
support. No new matrix files were acquired and no
holdout, response, damage, or SCC gate is yet open.
A registered later-century expansion now fixes the next acquisition before any
later-century feature or response result is examined. It selects exactly the
2041--2050 and 2091--2100 `pr`/`tas` files for the full five-ESM by three-SSP
matrix: 30 official version-`20210512` datasets and 60 public, unrestricted
CC0 files totaling 124,935,312,957 catalogue bytes. Harvest years are limited
to 2042--2049 and 2092--2099 so every crop season is contained within one
selected daily block. This is a metadata-pinned acquisition plan, not content
validation, expanded support, a fitted response, damages, or an SCC input.
The first registered GFDL-ESM4 SSP1-2.6 `pr`/`tas` pair for 2041--2050 is now
fully acquired. Both files pass exact byte, SHA-512, and decoded 3,652-day
global-grid gates, and the paired `tas` yields ten annual same-realization GMST
rows. A bounded two-latitude-row maize/rainfed smoke produces 5,488 seasonal
and 16,464 stage rows for the eight preregistered harvest years with exact
additive stage reconciliation. The matching 2091--2100 pair and 2092--2099
feature block pass the same gates. The registered SSP3-7.0 2041--2050 pair and
bounded feature block also pass. Against matched SSP1-2.6 cells, mean
SSP3-7.0 differences are +0.574 C, -18.33 mm seasonal rain, -1.11 wet days,
and +3.20 maximum dry-spell days. The registered SSP5-8.5 2041--2050 pair
and bounded feature block pass the same gates. The SSP3-7.0 2091--2100 pair
and its bounded 2092--2099 feature block now also pass. The SSP5-8.5 2091--2100
pair and its bounded 2092--2099 feature block pass as well, bringing the
expansion to 12 of 60 files and six feature blocks. The next registered
IPSL-CM6A-LR SSP1-2.6 2041--2050 pair and its matching 2091--2100 pair also
pass exact bytes, SHA-512, model-specific 12:00 daily chronology, decoded
content, same-realization GMST, and bounded-feature reconciliation. The IPSL
SSP3-7.0 2041--2050 and 2091--2100 pairs and bounded feature blocks now pass
the same gates. Both IPSL SSP5-8.5 pairs now also pass exact checksum/content,
same-realization GMST, and bounded-feature gates, bringing the expansion to 24
of 60 files and twelve feature blocks. Both MPI-ESM1-2-HR SSP1-2.6 blocks,
2041--2050 and 2091--2100, also pass exact checksum, model-specific 12:00
daily content, same-realization GMST, and bounded-feature gates, bringing the
expansion to 28 of 60 files and fourteen feature blocks. The MPI SSP5-8.5
2041--2050 pair now passes those same gates. Together with the separately
registered MRI SSP1-2.6 2041--2050 block, this brings the expansion to 32 of
60 files and sixteen feature blocks. Against matched MPI SSP1-2.6 cells, its
mean differences are +0.237 C, +17.88 mm seasonal rain, +1.37 wet days, -1.00
maximum dry-spell days, +1.71 mm Rx1day, and +6.75 mm Rx5day. Against matched
MRI SSP1-2.6 cells, the newly registered MRI SSP3-7.0 midcentury block averages
+0.369 C, -11.02 mm seasonal rain, -1.07 wet days, +0.23 maximum dry-spell
days, -0.32 mm Rx1day, and +0.26 mm Rx5day. It raises tracked progress to 34
of 60 files and seventeen feature blocks but does not yet close an MRI
whole-scenario or whole-ESM gate. Against matched MRI SSP1-2.6 cells, the
SSP5-8.5 midcentury block averages +0.777 C, -8.81 mm
seasonal rain, +0.28 wet days, -2.83 maximum-dry-spell days, -1.50 mm Rx1day,
and -2.68 mm Rx5day. It closes the MRI three-scenario midcentury matrix at
36/60 files and eighteen blocks. The whole-scenario audit improves 15/33
comparisons and places 11.73% of held-out values outside support, so the
response, damage, and SCC gates remain closed. The MRI SSP1-2.6 and SSP3-7.0
2091--2100 pairs now also pass exact complete-file, same-realization GMST,
bounded feature, and reconciliation gates. SSP3-7.0 minus SSP1-2.6 averages
+2.928 C, +2.24 mm seasonal rain, -0.97 wet days, +2.41 maximum-dry-spell
days, +0.25 mm Rx1day, and +1.15 mm Rx5day. The MRI SSP5-8.5 end-century pair
then passes the same gates, raising progress to 42/60 files and twenty-one
blocks. SSP5-8.5 minus SSP1-2.6 averages +4.591 C, -13.23 mm seasonal rain,
-2.62 wet days, +5.44 maximum-dry-spell days, +0.75 mm Rx1day, and +0.56 mm
Rx5day. Its 181,104-row whole-scenario audit improves 16/33 comparisons
(median RMSE ratio 1.00006; maximum 1.06514), including 9/11 for held-out
SSP5-8.5, while 27,090 values (14.96%) fall outside support. This mixed,
adverse engineering result keeps the response, damage, and SCC gates closed.
The frozen MPI-ESM1-2-HR matrix is now complete for all three scenarios and
both later-century periods. The six newly registered `pr`/`tas` files pass
full checksum/content gates, and their three bounded blocks pass
same-realization GMST and exact stage/season reconciliation, bringing the
expansion to 48/60 files and twenty-four blocks. Matched MPI SSP3-7.0 minus
SSP1-2.6 seasonal rain changes are -4.38 mm at midcentury and -17.02 mm at end
century; end-century SSP5-8.5 minus SSP1-2.6 is -13.20 mm. These are climate
diagnostics only; no response, damage, or SCC gate is opened. The matching
MPI whole-scenario audits remain adverse: GMST adjustment
improves 14/33 feature comparisons at midcentury and 15/33 at end century;
11.65% and 15.24% of held-out feature values, respectively, are outside exact
two-scenario support. The emulator is not promoted. The fail-closed four-ESM
whole-ESM audit joins GFDL, IPSL, MPI, and MRI across
all three SSPs. Midcentury improves 27/44 feature comparisons with 8.34% of
held-out values outside exact three-ESM support; end century improves only
12/44 with 9.47% outside support. UKESM remains missing, so the planned
five-ESM and FAIR feature-support gates remain open. The frozen UKESM1-0-LL
SSP1-2.6 2041--2050 `pr`/`tas` pair now passes exact catalogue bytes/SHA-512,
complete midnight daily chronology, decoded-content, same-realization GMST,
bounded maize/rainfed feature, and exact reconciliation gates. This brings
later-century coverage to 50/60 files and twenty-five blocks. UKESM's
remaining scenarios/period and the resulting five-ESM holdout are not yet
complete, so the emulator and every response/damage/SCC gate stay closed.
The matching UKESM SSP1-2.6 2091--2100 pair passes the same gates and raises
coverage to 52/60 files and twenty-six blocks. Over separate fixed maize
slices, end-century minus midcentury means are +0.849 C, -3.19 mm rain, +0.33
wet days, +0.49 maximum-dry-spell days, +0.69 mm Rx1day, and +2.48 mm Rx5day.
These are descriptive period means, not an exact-key response; four UKESM
pairs and all production gates remain open.
The UKESM SSP3-7.0 2041--2050 pair also passes exact bytes/checksums, midnight
decoded content, same-realization GMST, and 5,488-season/16,464-stage feature
reconciliation. Relative to the exact-key SSP1-2.6 cell, means change by
+0.876 C, -6.76 mm rain, -0.72 wet days, +2.66 maximum-dry-spell days,
-0.53 mm Rx1day, and +1.60 mm Rx5day. Coverage is 54/60 files and twenty-seven
blocks; this descriptive support contrast does not authorize a response,
damage function, or SCC input.
The matching UKESM SSP3-7.0 2091--2100 pair passes the same gates and raises
coverage to 56/60 files and twenty-eight blocks. Relative to exact-key
SSP1-2.6, mean changes are +4.293 C, +8.32 mm rain, +1.07 wet days, +0.60
maximum-dry-spell days, +1.46 mm Rx1day, and +2.85 mm Rx5day. Only the two
SSP5-8.5 UKESM pairs remain before the five-ESM later-century rerun; no
response, damage, or SCC gate is opened.
The UKESM SSP5-8.5 2041--2050 pair now passes the same exact catalogue,
midnight chronology, decoded-content, same-realization GMST, bounded-feature,
and reconciliation gates. Relative to the exact-key SSP1-2.6 cell, means
change by +1.195 C, +5.16 mm rain, -0.19 wet days, +0.55 maximum-dry-spell
days, +2.37 mm Rx1day, and +6.68 mm Rx5day. Coverage is 58/60 files and
twenty-nine blocks; the end-century UKESM pair and complete five-ESM reruns
remain required, and no response, damage, welfare, or SCC use is authorized.
The complete UKESM midcentury three-scenario product has 181,104 rows. Whole-
scenario GMST adjustment improves 13/33 feature comparisons over the cell-mean
benchmark (median RMSE ratio 1.00035; maximum 1.22120), while 22,115 values
(12.21%) are outside exact two-scenario support. Held-out SSP3-7.0 improves
only 1/11 comparisons. This adverse outcome-blind result keeps production,
FAIR baseline/pulse, response, damage, welfare, and SCC gates closed.
The complete five-ESM midcentury product contains 905,520 rows and 55 whole-
ESM comparisons. GMST adjustment improves 32/55 over the cell-mean benchmark
(median/maximum RMSE ratios 0.99969/1.08533), while 58,580 values (6.47%) lie
outside exact four-ESM support. This completes the registered midcentury
whole-ESM engineering gate. The final UKESM SSP5-8.5 2091--2100 pair brings
coverage to 60/60 files and thirty bounded feature blocks. Relative to the
matched SSP1-2.6 cell, mean changes are +5.918 C, +29.61 mm seasonal rain,
+2.46 wet days, +0.93 maximum-dry-spell days, +2.44 mm Rx1day, and +4.68 mm
Rx5day. The complete UKESM end-century whole-scenario audit improves 17/33
comparisons, with median/maximum RMSE ratios 0.99958/1.06170 and 29,898 values
(16.51%) outside exact two-scenario support. The complete five-ESM end-century
product has 905,520 rows: GMST adjustment improves 30/55 comparisons, with
median/maximum RMSE ratios 0.99982/1.01357 and 64,665 values (7.14%) outside
exact four-ESM support. These results complete the registered acquisition and
whole-scenario/whole-ESM engineering matrix, but FAIR baseline/pulse feature
support remains open; no response, damage, or SCC use is authorized.
Against matched IPSL SSP1-2.6 cells, mean SSP3-7.0 differences at
midcentury are +0.365 C, +13.22 mm seasonal rain, +0.93 wet days, -1.36
maximum dry-spell days, +2.18 mm Rx1day, and +3.84 mm Rx5day. At end century,
the matched means are +4.146 C, +25.70 mm seasonal rain, +2.85 wet days, -2.26
maximum dry-spell days, +3.12 mm Rx1day, and +4.47 mm Rx5day. These are
descriptive climate differences only. At midcentury, matched IPSL SSP5-8.5
minus SSP1-2.6 means are +0.607 C, +19.88 mm rain, +2.07 wet days, -0.77
maximum dry-spell days, +2.01 mm Rx1day, and +3.13 mm Rx5day. The exact joined
IPSL three-SSP product has 181,104 feature rows; GMST adjustment improves only
15/33 comparisons (median RMSE ratio 1.00028; maximum 1.02568), including
3/11 for held-out SSP5-8.5, and 20,529/181,104 values (11.34%) are outside the
two-scenario envelope. The matching IPSL end-century product also has 181,104
rows; adjustment improves only 10/33 comparisons (median ratio 1.00275;
maximum 1.27466), including 2/11 for held-out SSP5-8.5, and 30,619 values
(16.91%) are outside support. The corresponding GFDL
midcentury product has 181,104 feature rows. Leave-one-scenario-out GMST adjustment improves only
14/33 feature comparisons versus a cell-mean benchmark (median RMSE ratio
1.00036; maximum 1.06410), and only 1/11 when SSP5-8.5 is held out. Across all
held-out climate values, 20,562/181,104 (11.35%) lie outside the exact two-
scenario cell/feature envelope. The matching end-century three-SSP product
also has 181,104 rows; its GMST adjustment improves 13/33 comparisons (median
RMSE ratio 1.00110; maximum 1.23350), while 27,260 values (15.05%) fall outside
the two-scenario support envelope. A temperature-only FAIR sensitivity using
the now-expanded 287.659--291.189 K GFDL envelope extends the mapped-baseline
last-within year from 2020 through 2300 and revalidates
common-random-number pairing, zero/pre-divergence identity, and decreasing-
pulse convergence. The adverse GFDL and IPSL mid- and end-century holdout results reject promotion; whole-ESM,
FAIR feature-support, response, damage, and SCC gates remain open.
The evidence-bounded manuscript and Methods/SI blueprints are in
[MANUSCRIPT_OUTLINE.md](MANUSCRIPT_OUTLINE.md) and
[METHODS_SI_OUTLINE.md](METHODS_SI_OUTLINE.md).
All claims and results are governed by
[SCIENTIFIC_INTEGRITY_PROTOCOL.md](SCIENTIFIC_INTEGRITY_PROTOCOL.md); an
independent replication and adversarial-review path is provided in
[INDEPENDENT_REVIEW_CHECKLIST.md](INDEPENDENT_REVIEW_CHECKLIST.md).
The executable crop-specific array, coverage, adaptation, and replacement
boundary is documented in
[SCC_INTEGRATION_DESIGN.md](SCC_INTEGRATION_DESIGN.md). It contains no fitted
coefficients or SCC estimates.

The empirical climate pipeline is deliberately staged: daily ISIMIP inputs are
converted to calendar-defined crop-year features, independently reconciled
against stage partitions, then joined to GDHY yields before any pilot response
diagnostic. Stage-resolved daily-maximum heat features now use the same
partition boundaries, require explicit temperature thresholds, and must
reconcile additive heat days and degree-days to the season. Seasonal and stage
validators also enforce the necessary nesting of day counts and degree-day
totals across ordered thresholds. The stage fractions
are temporal proxies rather than asserted crop phenology. A parallel historical
drought-benchmark path day-weights monthly CRU scPDSI over those same windows,
requires exact 0.5-degree grid correspondence and complete monthly coverage,
and preserves an explicit `historical_benchmark_not_future_scc_input` role
through regime-first allocation. The global 1982--1989 and 2012--2016 maize
and soybean candidate panels now pass raw-source/calendar manifest binding and
complete derived-input allocation recomputation; they remain unfitted and
contain no direct-weather terms. It does not substitute observed CRU scPDSI
for a matched future drought path. See the scripts directory and
[RESULTS_STATUS.md](RESULTS_STATUS.md) for the current evidence boundary.
The resumable `scripts/run_historical_crop_chunk.sh` command executes the
seasonal and stage extraction, completeness checks, independent
reconciliation, GDHY join, and precipitation-pattern construction for one
crop, irrigation calendar, and historical time block. All generated products
remain below the ignored `data/interim/` boundary.
Daily precipitation, mean-temperature, and maximum-temperature builders accept
chronologically ordered file lists. They reject coordinate or unit changes,
duplicate or missing boundary dates, and non-daily steps before crop-season extraction;
they then read only the calendar years that can enter the requested harvest
years. This permits cross-year seasons to span version-pinned decadal files
without silent edge loss and is also required for historical/future ISIMIP3b
blocks in the matched-feature driver.

Before any empirical response array can approach GIVE wiring,
`scripts/validate_scc_response_bundle.py` enforces the frozen crop/FUND order,
full crop-value coverage, matched baseline/pulse identifiers, one declared
water-stress family, fixed-within-draw weights, finite coefficients, and
pre-divergence conservation. Passing this schema gate is not evidence of
held-out skill or authorization to calculate an SCC.

After wiring, `src/AgricultureReplacementAudit.jl` inspects Mimi's component
graph and fails unless `DamageAggregator.damage_ag` has exactly one internal
producer, `JointAgriculture.agcost`, and no component named `Agriculture`
remains instantiated. Synthetic missing-source, wrong-source, and coexistence
cases are tested. The unmodified GIVE baseline is a deliberate negative
control: it is rejected because `Agriculture.agcost` still supplies
`damage_ag`. A graph pass establishes the replacement topology only; it does
not clear empirical, welfare, coverage, support, paired-run, or SCC gates.

`src/AgricultureReplacementHarness.jl` now performs that replacement on a
MimiGIVE-style model: it deletes the legacy component and its MooreAg-only
parameters, installs the crop response and joint agriculture components,
reuses the existing regional socioeconomic aggregators, preserves the
declared sector-inclusion flags, and reconnects `damage_ag` once. The executed
integration control in `scripts/test_give_replacement_harness.jl` passes
against the unmodified GIVE model with synthetic zero-response inputs: every
active-year crop and regional response output is complete, coverage is one,
and both `JointAgriculture.agcost` and GIVE's aggregated agriculture damage are
zero. Mimi requires externally supplied arrays on the full GIVE model time
dimension, including years before the components' 2020 start. This is a
synthetic execution/connectivity result, not a paired marginal run, empirical
damage estimate, or SCC result.

That control was executed with the archived GIVE runtime (Julia 1.6.4
x86_64 under Rosetta). The archived dependency lock does not currently run
natively on Apple silicon because its Electron artifact is unavailable for
`aarch64-apple-darwin`; `REPOSITORY.md` records the exact reproducible command.

`src/PairedAgricultureAudit.jl` checks the next component boundary after the
response and replacement components run: matched dimensions, finite values,
pre-divergence conservation, and an all-years zero-pulse identity control. It
remains an output-contract gate rather than a full GIVE marginal run or SCC.

The pre-integration validation layer now also includes
`scripts/evaluate_crop_response_models.py`, driven by the frozen
`config/response_evaluation_spec.toml`. It evaluates crop-specific
first-difference predictions across outcome-blind spatial, temporal, and
climate-extreme holdouts and intentionally emits no coefficients. Its output
is diagnostic and cannot be used as an SCC response bundle.
That diagnostic comparison is deliberately smaller than the production estimand:
it omits wet-day frequency, conditional wet-day intensity, Rx5day, heat, and
the two alternative drought families, and represents normalized stage
timing/distribution only indirectly through stage totals. The response audits
reported before the purged-split revision used temporal and extreme
first-difference pairs that could share a level-yield endpoint across training
and test. Those values are legacy dependent stress tests and become stale when
the hashed diagnostic specification changes; they are not production outer
holdouts. The revised evaluator and audit validator now enforce zero endpoint
overlap and pass synthetic tests. Corrected 1982--1989 MIRCA-2000 maize and
soybean minimal diagnostics pass under the new hash; other historical panels
remain stale or pending. The complete not-yet-frozen registry and the required
purged-split promotion gate are documented in
[RESPONSE_SPECIFICATION_BOUNDARY.md](RESPONSE_SPECIFICATION_BOUNDARY.md).
`scripts/validate_response_evaluation_audit.py` then fails unless the audit
matches the exact configuration hash and contains the complete explicitly
declared crop/model/holdout product with reconciled folds, benchmarks, metrics,
and row counts. When an expected year range is declared, it also requires the
exact contiguous harvest-year list. Its descriptive ranking is not a
model-selection rule.

Run the independent scope boundary before any response work:

```bash
./.venv/bin/python scripts/validate_response_spec_boundaries.py
```

This check confirms omissions and non-authorization; it does not freeze or fit
a production model.

For a panel that already contains stage features, create the outcome-blind
labels and run the audit with:

```bash
./.venv/bin/python scripts/make_validation_folds.py \
  --panel data/interim/STAGE_PANEL.parquet \
  --out data/interim/STAGE_VALIDATION_PANEL.parquet
./.venv/bin/python scripts/evaluate_crop_response_models.py \
  --panel data/interim/STAGE_VALIDATION_PANEL.parquet \
  --out outputs/response_evaluation.json
./.venv/bin/python scripts/validate_response_evaluation_audit.py \
  --audit outputs/response_evaluation.json \
  --expected-crop mai --expected-crop ri1 --expected-crop ri2 \
  --expected-crop soy --expected-crop swh --expected-crop wwh \
  --expected-year-start 1982 --expected-year-end 1989 \
  --summary-out outputs/response_evaluation_summary.json
```

The approved calendar-to-yield season crosswalk is recorded in
[data/provenance/crop_calendar_gdhy_crosswalk.md](data/provenance/crop_calendar_gdhy_crosswalk.md).
It deliberately does not use GDHY convenience aggregate directories where a
season-specific outcome exists.
The aligned GDHY method can clip a negative aligned yield to zero. The join
preserves that source zero in `gdhy_yield_raw_t_ha` and flags it with
`yield_nonpositive`, but marks it unobserved for the log-yield response; it
never silently adds an arbitrary positive offset.

GDHY does not provide separate rainfed and irrigated yield outcomes. The
production path must therefore never duplicate one observed yield into two
regime-specific estimation rows. `scripts/allocate_outcome_exposures.py`
enforces the one-outcome and independent-share contract. For a nonlinear
response, every regime-specific transform, extreme, drought index, spline,
threshold, and interaction must be built before the fixed shares are applied;
averaging primitive weather and transforming it afterward is invalid.
`scripts/allocate_irrigation_response_basis.py` implements this order for the
minimal predictive diagnostic. Its output is accepted only by the evaluator's
explicit contract-aware prebuilt-basis mode, which consumes supplied basis
columns without rebuilding them. The complete production basis and causal
estimator remain to be frozen. The allocator fails
on missing regimes, inconsistent yields, time-varying or non-independent
weights, incomplete shares, nonfinite features, and duplicate keys. The
synthetic test exercises these gates. MIRCA-OS v2 is now acquired and
checksum/grid validated as that independent area source.
`scripts/build_mirca_irrigation_shares.py` constructs fixed 2000 shares and
the registered 2005--2020 vintage sensitivities on the common 0.5° grid.
Maize and soybean mappings are exact; annual rice and wheat weights carry
`production_eligible=false` because they cannot identify the two rice seasons
or spring/winter wheat, and the allocator now rejects them. The source closes
a weighting-input gate but does not supply an irrigated yield outcome,
response coefficient, damage, or SCC.
`scripts/allocate_irrigation_distribution_basis.py` extends the same ordering
to a 54-column direct-pattern candidate contract: seasonal and three-window
amounts, normalized shares/timing/concentration, wet-day occurrence and
conditional intensity, CDD, Rx1day, Rx5day, mean temperature, and registered
temperature-by-log-amount terms. The current 1 mm wet-day definition remains
a recorded candidate/QA definition, not a selected production threshold. The
script validates stage/season reconciliation and emits `fit_authorized=false`;
heat and alternative drought-family features remain separate open gates.
`scripts/allocate_irrigation_scpdsi_basis.py` implements the separate
historical climatic-water-balance candidate: it builds seasonal/stage scPDSI
means, minima, monthly-index threshold day-equivalents, and fractions within each irrigation
calendar before fixed-area weighting, removes only complete outcome keys when
coverage is missing, and emits no direct precipitation or temperature terms.
`scripts/validate_irrigation_scpdsi_basis.py` hash-checks the raw-source and
calendar manifest chain and fully recomputes the candidate from its derived
stage tables. It does not label that derived-input check as full raw-metric
recomputation. `scripts/run_scpdsi_candidate_chunk.sh` composes the complete
partition-to-validation route; it performs no response fit and authorizes no
future, causal, damage, or SCC use.
`scripts/build_direct_scpdsi_common_support.py` then constructs four data-only
common-support bundles while keeping the 54-feature direct-weather and
16-feature scPDSI views separate. Common rows/observed outcomes and direct-only
dropped rows/observed outcomes are: maize 1982--1989,
240,784/115,758 and 24,744/1,921; soybean 1982--1989,
176,537/47,653 and 14,935/269; maize 2012--2016,
150,490/59,772 and 15,465/1,046; and soybean 2012--2016,
110,336/26,601 and 9,334/147. scPDSI-only drops are 0/0 in every bundle.
`scripts/validate_direct_scpdsi_common_support.py` verifies hashes and exactly
recomputes both views and the intersection from the immediate candidate
tables. It does not rerun upstream raw sources or bind upstream validation
receipts; running those validators and retaining their receipts is an external
prerequisite. These bundles fit no model and report no coefficient, causal
effect, model selection, future projection, damage, or SCC result. Seasonal
quantity remains the direct-weather reference, distribution terms require
robust stable outer-holdout value, and drought families remain mutually
exclusive competitors rather than stacked controls. See
[DIRECT_SCPDSI_COMMON_SUPPORT_CONTRACT.md](DIRECT_SCPDSI_COMMON_SUPPORT_CONTRACT.md).
The matched comparison now also has a separate, validated heat-control basis
constructed within rainfed and fully irrigated calendars before fixed-share
aggregation. It uses crop-stage mean temperature plus daily-maximum
degree-days above 29 C for maize and 30 C for soybean; the parallel 30 C maize
basis is retained as a sensitivity. See
[HEAT_CONTROL_BASIS_CONTRACT.md](HEAT_CONTROL_BASIS_CONTRACT.md) and
[HEAT_THRESHOLD_EVIDENCE_NOTE.md](HEAT_THRESHOLD_EVIDENCE_NOTE.md).

The resulting coefficient-suppressing historical diagnostic contains 209,036
maize and soybean consecutive-year pairs. Across five unbuffered 5-degree
spatial folds, direct seasonal precipitation quantity has the lowest mean RMSE
for both crops and lowers RMSE in all ten crop-fold comparisons, but the gains
are below 1% and MAE rankings are less uniform. Richer scPDSI summaries add
stress-specific rather than stable general predictive value. All 110 aggregate
metrics pass exact recomputation and a separate clean-room refit. This is not a
causal response, production-model selection, climate-change projection,
damage estimate, or SCC input. Exact results, hashes, and limitations are in
[GLOBAL_DIRECT_SCPDSI_DIAGNOSTIC_RESULTS.md](GLOBAL_DIRECT_SCPDSI_DIAGNOSTIC_RESULTS.md);
the executable contract is documented in
[DIRECT_SCPDSI_PREDICTIVE_DIAGNOSTIC.md](DIRECT_SCPDSI_PREDICTIVE_DIAGNOSTIC.md).
The paired geographic loss sensitivity and its narrower uncertainty boundary
are documented in
[DIRECT_SCPDSI_PAIRED_LOSS_UNCERTAINTY.md](DIRECT_SCPDSI_PAIRED_LOSS_UNCERTAINTY.md).

The primary SPEI competitor is now literature- and source-locked without
reusing a later-period standardized field. It will compute separate SPEI-1,
SPEI-3, and SPEI-6 candidates from the already acquired nClimGrid-Daily and
ISIMIP3a GSWP3-W5E5 precipitation/temperature, using daily Hargreaves-Samani
reference ET, monthly water balance, and a grid-cell/calendar-month
three-parameter log-logistic unbiased-PWM fit over 1982--2011 frozen before
the 2012 terminal holdout. NOAA's published U.S. SPEI and SPEIbase 2.11 remain
retrospective implementation/PET checks because their calibration/source
boundaries do not match the terminal diagnostic. The contract and physical/
time primitives pass; full SPEI fields and crop/outcome models do not yet
exist. See [SPEI_COMPETITOR_DESIGN.md](SPEI_COMPETITOR_DESIGN.md).
`scripts/run_irrigation_basis_chunk.sh` composes these gates for one completed
maize or soybean period: it constructs the corrected minimal basis, assigns
fixed outcome-blind validation folds, runs and validates the coefficient-
suppressing predictive audit, then constructs and validates the broader
distribution candidate without fitting it. All products remain ignored and
explicitly ineligible for causal, damage, or SCC use.
`scripts/filter_complete_yield_support.py` creates a separate sample-
composition sensitivity for periods in which GDHY's finite spatial support
changes by year. It retains only cells observed in every declared year, imputes
nothing, and warns that complete-support conditioning can itself select a
nonrepresentative subset; it does not replace the unbalanced primary panel.
Cell-count support is not welfare support. The fail-closed audit in
`scripts/audit_mirca_welfare_support.py` shows that the current 1982--1989
response-pair cells cover 79.02% of positive MIRCA maize area and 89.29% of
soybean area, despite roughly 98% coverage when the denominator is only
GDHY-observed cells. A same-vintage MIRCA-area-times-GDHY-yield proxy is
undefined over the remaining 20.98%/10.71% of global MIRCA area, and no pinned
spatial crop-value input exists. [WELFARE_SUPPORT_AUDIT.md](WELFARE_SUPPORT_AUDIT.md)
therefore blocks interpreting the current sample as global production/value
coverage or normalizing it to global welfare.
The aggregate observation equation, identification restrictions, distinction
between area, production, and revenue weights, and required sensitivities are
recorded in [IRRIGATION_AGGREGATE_ESTIMAND.md](IRRIGATION_AGGREGATE_ESTIMAND.md).
Legacy maize/soybean all-area response outputs constructed nonlinear terms
after primitive-weather weighting are withdrawn; only their source/support
audits remain valid.
The season-specific evidence and executable 5′ rice validation gate are
recorded in [MIRCA_SEASON_CROSSWALK_GATE.md](MIRCA_SEASON_CROSSWALK_GATE.md).
The real 2000 Rice1--Rice3 reconstruction does not reconcile to the annual
Rice maps, so the builder records a failure audit and emits no production
weights. Wheat remains blocked without an explicit spring/winter area source.

Reproduce the candidate rice source gates with the following commands. The
inventory command is expected to exit nonzero because nine publisher files
carry inconsistent year metadata; the 2000 builder is also expected to exit
nonzero after writing its annual-reconciliation audit. Neither emits rice
weights.

```bash
./.venv/bin/python scripts/download_mirca_rice_seasons.py
./.venv/bin/python scripts/audit_mirca_rice_inventory.py
./.venv/bin/python scripts/build_mirca_rice_season_shares.py \
  --monthly-root data/raw/mirca_os_v2/monthly_rice \
  --annual-root data/raw/mirca_os_v2/extracted_30arcmin --year 2000 \
  --out data/interim/mirca_os_v2/rice_season_irrigation_shares_2000.parquet \
  --audit-out data/interim/mirca_os_v2/rice_season_irrigation_shares_2000_audit.json
```

Rebuild the ignored source and fixed-2000 table with:

```bash
./.venv/bin/python scripts/download_mirca_os_v2.py
./.venv/bin/python scripts/build_mirca_irrigation_shares.py \
  --input-root data/raw/mirca_os_v2/extracted_30arcmin --year 2000 \
  --out data/interim/mirca_os_v2/irrigation_shares_2000.parquet \
  --audit-out data/interim/mirca_os_v2/irrigation_shares_2000_audit.json
```

[METHODS_BENCHMARK_QIU_2025.md](METHODS_BENCHMARK_QIU_2025.md) records the
adapted ensemble/validation design benchmark used for the next specification.
The high-resolution US validation track is isolated in
[us_county_validation/README.md](us_county_validation/README.md).
