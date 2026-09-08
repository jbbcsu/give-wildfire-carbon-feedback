# Active continuation checkpoint

## Latest: U.S. paired county climate benchmark COMPLETE; regional queue ACTIVE

After6f146a6, completed the existing-input/geometry inventory and immediately
built and compared paired climate features on the exact NASS calendars and
county polygons. See `US_PAIRED_COUNTY_CLIMATE_RESULTS_20260908.md` and
`data/provenance/us_paired_county_climate_20260908.json`. Full ignored data:
`data/interim/us_paired_overlap_20260908/result.json` and
`data/interim/us_paired_county_climate_20260908/` (receipt, two573row climate
tables, comparison). 16corn/15soy counties;346/227county-years,36daily cells.
Factual-minus-counterclim precipitation+26.10/+24.48mm,dryspells−2.28/−2.61days.
GSWPfactual-minus-nClimGrid precipitation+31.87/+32.25mm on same keys/calendars.
No crop response fit, new holdout, national damage or SCC. Nine targeted tests
passed; all real stages first-pass; max301.84MiB sampledRAM,649,211bytes before
publication exports. Do NOT repeat these completed stages.

The narrow strip fails the existing response sample minimum(25counties,
500rows/practice). Instead of lowering it, registered54regional source
cutouts over the retained419counties' geometry envelope. Three bands:
south25.5–33.5,central33.5–41.5,north41.5–49.5N; all109.5–74.5W,16x70cells.
Same18parent sources/dates/rights/IDs, no new climate source. New child configs
`config/isimip3a_us_{band}_{scenario}_{var}_{first}_20260908.json` reference
UNCHANGED original parent configs/hashes. Old validators unchanged. Read
`US_PAIRED_REGIONAL_ACQUISITION_PROTOCOL_20260908.md`; four regional-contract
tests passed incl real syntheticNetCDF validation. Counterclim domain must
equal all4hash-bound calendar masks daily; no static/intermittent imputation.

Acquisition driver `scripts/continue_us_paired_regional_acquisition.py` runs
one bounded child at a time and at most2unfinished server requests, preserving
pending jobs/uncertain POSTs/failures. First queue slice COMPLETE:5/54 validated,
79,468,075retained regional bytes. Second slice is ACTIVE at checkpoint write
(unified command session55971); do not launch another analysis while it runs.
Use process check and receipts to determine actual state after interruption,
not this historical session number. Currently completed central counterclim:
pr1981/1991/2001 andtas1981/1991. Counts may have advanced since this write.

NEXT: finish all54regional acquisitions with
`.venv/bin/python scripts/continue_us_paired_regional_acquisition.py --max-actions 108 --max-seconds 600`
after checking for an active driver/child. It resumes validated outputs and
saved server requests; no perfile user approval. Requests normally live in
`data/interim/us_paired_regional_requests_20260908/`; FIRST centralcounterclim
pr1981request is the special retainedpath insideus_paired_county_climate directory
handled bydriver. Outputs:`data/interim/us_{band}_{scenario}_{var}_{first}_20260908/`.
Do not treat pending command return0 as download completion; require receipt
status`regional_paired_climate_content_validated`. All attempts use unique
resource/log names; source caps16MiBarchive/64MiBtotal remain enforced.
Then aggregate receipts/resources/cumulative storage; inspect complete finite
county support across3bands and generalize the new county-calendar builder to
this region in a separate registered stage (current builder intentionally
requires the original16/15county573row pilot). No barred coefficients may be
exported; then freeze source-matched joint response/validation contract.
Keep one1024MiBsampled job,64MiBowned disk,130GiBfloor. No new user decision.
Earlier NEXT blocks below are superseded; routine notifications remain muted.

## Latest: paired empirical weather-support diagnostic COMPLETE

After 39458f4, registered and completed the small existing-data support check.
Read `PAIRED_WEATHER_SUPPORT_RESULTS_20260908.md`; compact hash-bound aggregate
`data/provenance/paired_weather_support_20260908.json`. Full ignored result:
`data/interim/paired_weather_support_20260908/result.json`. Six synthetic tests
pass; real job first execution completed, sampled peak258.59MiB, 703,865new
disk bytes, no downloads. Export also complete. No process remains running.
Exact observed cohort8,465mai/4,321soy rows,292/149cells; distribution excludes
seven maize cells. Quantity+heat marginal outside50.25%mai/46.59%soy versus
joint-distance flags6.47%/.93%. These are different diagnostic criteria, NOT
causal support certificates, yield estimates, model selection or SCC.
No barred coefficients used/exported; no old inputs/gates changed.

NEXT: `JOINT_RESPONSE_RESEARCH_DESIGN_20260908.md` defines the separate new
research design. First executable step: small existing-manifest inventory of
the completed U.S. NASS irrigation analysis's county outcome/weather sources,
exact intersection with paired climate strip, and genuinely untouched years
if any. Do not call inspected validation sets new holdouts. No county-centroid
assignment masquerading as area weather, no broad downloads, no repeat of
completed association/OOS/daily-input construction. Then source-bound response
contract addressing nonlinear heat/quantity, irrigation, source dependence,
support/hybrid-state interpretation, CO2/adaptation before any new fit. The
global source-unit-dependence inventory is secondary if it does not slow this.
No new user decision needed for the existing-input inventory. Keep one bounded
job/thread,1024MiB sampledRAM,64MiB owned disk,130GiB floor; muted notifications.
Earlier next-step blocks below are superseded.

## Latest: paired factual/counterclim climate diagnostic COMPLETE

After dcf9169, acquired18smallpublicGSWP3-W5E5obsclim/counterclim daily
pr/tas/tasmax1981–2010cutouts and built both crops/bothcalendars for eachpath.
All four builds firstexecutionpassed;47,966jointrows total. Final paired
diagnostic validated after exact-domain and numerical-reference audits below.
Read`FACTUAL_COUNTERCLIM_RESULTS_20260908.md`; aggregatewithFAILURES preserved:
`data/provenance/factual_counterclim_pilot_20260908.json`. Finalignoredoutput:
`data/interim/counterclim_soy_joint_20260908/paired_comparison.json`.
Factual-minus-counterclim1982–2010full500/327cells:precip+8.70/+12.47mm,
dryspells−.411/−.656days,Rx5+.501/+.385mm,stage2Tmean+.982/+.800°C,
stage2DD+14.66/+9.19°Cdays. Shape488/325cells. These are conditionalhistorical
climate-inputdifferences,NOTanthropogenicforcing/yielddamages/SCC/globalmeans.
Do NOT repeat acquisition/builds/pairedcomparison or previousGFDL/IPSL work.

Important resolved failures, not permission blockers:
1. Firstcounterclimpr1981fullgridvalidationfailed on2,753,608NaNs. Exactaudit
shows754alwaysmissing NONCROPcells,686alwaysfinitecells exactlyall4calendars,
no missingcropvalues. Separate`validate_counterclim_crop_domain.py` requires
thisexactmaskdaily,source-specificIDs/version andall4calendarhashes; keeps
fullgridgate unchanged. Sourceacqflag`--counterclim-crop-domain`; newstatus
`crop_domain_climate_content_validated`. Firstpayloadreusedwithoutdownload
withNEWcrop_domain_receipt.json; originalreceipt/failure untouched. Amendment
`FACTUAL_COUNTERCLIM_DOMAIN_AMENDMENT_20260908.md` records post-failurechange.
2. Two tinytestattempts stopped onvolume-free-spacedelta. Noanalysisrunning
probe showedfree-spacechangeselsewhere; causeNOTattributedtoDropbox. Added
optionalOWNEDoutput/scratchaccounting to`run_bounded_job.run`, same64MiBcap,
130GiBfloor,1024MiBsampledRAM. FreshTMPDIR,bytecodewritesdisabled. Tests3pass,
fullgridregressiontestused95,632newbytes. Oldfailurespreserved. See
`OWNED_DISK_ACCOUNTING_20260908.md`. Use thismodeforownedexisting-datajobs;
declareALLoutputs/scratch, neverhydrateevictedraworwriteoutsidewatchedpaths.
3. Strictfactualparity failed atlogP,totals<.0001mm different. Initialuniform
earlyfloat32reconstructionfailed. Actualhash-boundearlypanels:rainfedfloat32,
irrigatedfloat64, bothcrops. EVERYoldprimitiveequalsoneexactdocumentedsum,
EVERYnewfloat64season/stagesumexactlyreproducedfromresidentdailypr. Rebuilt
legacyweightedfeaturesZEROresidual on8,465/4,321observedkeys. No tolerance
increase; olddataunchanged. `reconcile_factual_precision.py`, receipt
`data/interim/obsclim_soy_joint_20260908/precision_reconciliation.json`;
`FACTUAL_PARITY_PRECISION_RECONCILIATION_20260908.md` logs bothhypothesistests.
Finalcomparatorrequiresthis source/code/protocol-boundproof plus unchanged
strictchecks onallunaffectedfeatures. Originalstrictfailedstatusretained.

Eighteendistincttargetedtests passed. Peak sampledRAM786.52MiB;newretained
407.95MiB,cumulativeprecedingclimatestages1,132.19MiB,159.16GiBfreeatexport.
No analysisprocess remainsrunning atthischeckpoint. Allpubliccode/docs only
to precipitation-scc branch;raw/interim/outputs stayignored. Next: explicit
jointcrop-response/transport design, first a SMALLexisting-data paired-cohort
jointweather-support diagnostic (no barredcoefficients, no causal/SCCclaims)
on292/149positive-yieldobservedcells, then a separate justifiedresponsecontract.
Avoid assuming an observedtrends counterclimate suppliesanthropogenicforcing
or futureFAIRpulse. Preservequantity-first/nulltiming,droughtcompetingfamilies,
CO2/adaptation,welfare andrepresentativecoverage gates. No newdownloadneeded.
EarlierNEXT blocks below are superseded. Notifications remainmuted.

## Latest: independent IPSL historical benchmark COMPLETE

After a36da21, registered/acquired nine IPSL historical pr/tas/tasmax1981–2010
cutouts and generalized the historical wrappers with explicit model-specific
IDs/paths/protocols. Eight targeted tests pass, including rejection of merely
relabeled GFDL sources. Built14,500mai/9,483soy rows, both calendars, exact
dates/axes/dailymean<=maximum, one latitude row per child. All real jobs passed
first execution. Peak sampledRAM746.70MiB; new retained248.85MiB, cumulative
with preceding GFDLhistory/future724.24MiB;132.70GiBfree at export. No process
remains running at this checkpoint. Do NOT repeat either historical benchmark.

Results:`IPSL_HISTORICAL_CLIMATE_BENCHMARK_RESULTS_20260908.md`, durableaggregate
`data/provenance/ipsl_historical_climate_benchmark_20260908.json`. Same292/149
observed-supported cells as GFDL. IPSL historical dry spells+.55/+.76days and
Rx5+1.12/+1.84mm vs observed source, smaller offsets than GFDL; thresholdheat
offsets larger. SSP585future minus ownhistory precipitation+15.98/+30.39mm,
versusGFDL−3.42/+.05. These are NOT higher-minus-lower-scenario comparisons.
Ownhistory any6heatoutside fractions70.02%mai/63.64%soySSP585. No yielddamage,
correction, causal attribution or SCC. Manuscript/SI/evidencebrief updated.

NEXT: published ATTRICI counterclimate route, not a new custom emulator yet.
Read`ATTRICI_METHOD_ASSESSMENT_20260908.md`. Main-text methods/discussion read:
historical trend removal, seasonal occurrence/intensity, not anthropogenic
forcing/SCC, and not proven storm-persistence attribution. Code/supplement
not audited. LLAAE2021 is an additional ABSTRACT-only reviewed literaturelead.
Metadata feasibility COMPLETE via`inspect_counterclim_catalogue.py`; exact
six dataset/18file records in`data/provenance/counterclim_catalogue_feasibility_20260908.json`.
No counterclim bytes downloaded or subset requested. AllpublicCC0; nineobsclim
1981–2010hashes/sizes match retained factualmanifest. Obsclimversion20211021,
counterclim20220506; allcite10.48364/ISIMIP.982724.3. Resolve exactcounterclim
construction lineage using officialresource metadata/version notes before
attribution. Public resourceAPI866694bb-84ad-461f-952a-fc64ac72b4ed hasDataCite
descriptions (do notdumpwholecontributorspayload). Do not repeat completed
catalogue discovery; use retainedIDs/hashes. Then register small pairedfactual/
counterclim two-row climate-only diagnostic with samecalendars/featurechecks,
no fake outcomes. Existing acquisition validator accepts arbitrary registered
publicsourceidentity but historicalbuilder intentionally onlyGFDL/IPSL; add
separate observational-counterclim wrapper/contract, never relabelmodeldata.
Counterfactualversion label alone does not establisha newreference mismatch.
Response transport, CO2/adaptation/welfare/GIVEpulse remain independent gates.

Routine continuation notifications are muted; standinglawfuldata authorization
applies without perfileapproval. Keep1024MiB provenmonitorbudget(onejob/thread),
<=64MiBnewdisk perbatch and>=130GiBfree. No newpresentation or sectors. Earlier
NEXT blocks below are superseded by this one.

## Latest: GFDL historical source benchmark COMPLETE

After1da44bd: acquired nine small1981–2010historical pr/tas/tasmax cutouts,
validated source/chronology/grid/units and daily tas<=tasmax(1e-5°Ctolerance),
built29year maize/soy joint inputs on both calendars, one latitude per child.
14,500mai/9,483soy rows; source comparison on292/149observed-supported cells.
Historical model-minus-observed-source dry spells+1.86/+1.88days and Rx5day
+6.09/+10.77mm; stage2Tmean offsets only+.048/+.101°C. UnderSSP585 soybean
dry spells change−.20days vs model history but+1.68vs observed-source history.
No simulated year is paired as observed weather. Heat extrapolation persists
against model-history ranges:78.82%mai/78.50%soy SSP585future rows outsideat
least1of6heat ranges. No bias correction/yield effects/damages/SCC estimated.
All real jobs passed first execution;13unittesttests plus multifile testscript
passed. Peak sampledRAM743.78MiB;246.42MiB retainedhistorical,475.39MiB combined
with precedingfutureextension,132.96GiBfree at export. All jobs finished.
Read`HISTORICAL_CLIMATE_BENCHMARK_RESULTS_20260908.md`; durableaggregate:
`data/provenance/historical_climate_benchmark_20260908.json`. Do NOT rebuild
GFDLhistorical/future or repeat the completed distribution comparisons.

Reference check COMPLETE:`OBSERVED_CLIMATE_REFERENCE_CHECK_20260908.md`.
Observed GSWP3-W5E5 v1.3 uses W5E5 v2.0 for1979–2019 per officialDataCite;
ISIMIP3b adjustment uses W5E5 v2.0 perauthorfactsheet. Retained1981–2010pr
hashes/sizes match officialdailyversion20211021. Do not infer nominalversion
mismatch from residual pattern offsets. pr includes snow; rainfallshorthand
is totalwater-equivalentprecipitation. Fact sheet relevantpagestextread,
visualscreenshotsnotavailable; no full40pagereviewclaimed. No rawrehydration.

NEXT: register the independent IPSL-CM6A-LR historical pr/tas/tasmax1981–2010
benchmark, same version/member/two rows, reusing tested cutout workflows.
Catalogue filtering works:api/v1/datasets/?simulation_round=ISIMIP3b&climate_forcing=ipsl-cm6a-lr&climate_scenario=historical&climate_variable=VARIABLE.
Validate returned IDs/specifiers/rights rather than assuming them. Current
`build_historical_climate_benchmark.py` deliberately binds GFDL IDs andpaths;
generalize with explicit model/source tests before IPSL (never merely relabel).
One row per child and1024MiB monitoredRAM sufficed for simultaneouspr/tas;
keep<=64MiB newdisk perbatch and>=130GiBfree, no perdownloadapproval. Compare
historical distributions, not simulated/observed weather-year errors. Defer
any empirical correction until reference compatibility and independent-model
checks are assessed. Newly discovered published ATTRICI v1.1 counterclim
ISIMIP3a route deserves a bounded literature-first assessment for historical
precipitation-pattern attribution (rg found no prior ATTRICI/counterclim docs
inthisproject). Do not assume it provides futureSCC or removes all changes
insequence dependence; inspect primarymethod before using. Response,
CO2/adaptation, welfare and GIVE pulse remain
unfinished; do not weaken model-promotion or causal/SCC gates. Earlier NEXT
blocks are superseded by this one.

## Latest: GFDL/IPSL full28year matched heat COMPLETE

September8 after5631e13: acquired eight small missing2031–2040/2051–2060
Tmax cutouts under standing authorization, reused four2041–2050files, and
built all eight model/scenario/crop joint2032–2059tables.92,624rows total;
500mai/327soy cells, two latitude rows only. All eight2042–2049overlaps match
every column exactly (26,464oldrows). Full paired climate comparisons and
eight historical heat-range diagnostics completed; no empirical damages/SCC.
GFDL/IPSL stage2heat rises29.61/28.47°C·days for maize29°C and26.83/26.69for
soy30°C; existing full-period rainfall differences reproduce exactly.
SSP585 any-six-heat-range outside shares80.49/81.46%mai,75.74/75.12%soy.
Read`FULL_PERIOD_HEAT_RESULTS_20260908.md` and the new preliminary evidence
brief. Aggregate receipts:`data/provenance/full_period_heat_20260908.json`.
Twenty tests pass. One legacy synthetic fixture needed dated source fields;
original failed test log retained. First IPSL server-status check returned
started without downloading; later acquired the same completed job (v2log),
no resubmission. All real construction/validation jobs passed first execution.
Peak sampled RAM801.08MiB; new raw+derived retained228.97MiB; free133.24GiB
at export. All jobs finished, no detached analysis process. Raw data ignored.

NEXT executable priority is`RESPONSE_TRANSPORT_NEXT_STAGE_20260908.md`:
source-matched historical climate benchmark, starting with GFDL before IPSL.
Inspect retained manifests then resolve official historical daily pr/tas/
tasmax1981–2010source blocks for harvest1982–2010, same39.25/39.75N grid,
member/version/calendars/weights. Existing historical smoke is only2012–2014
maize/noirr and is not the required benchmark. Do not hydrate evicted global
raw inputs. Use registered small cutouts under existing safeguards/standing
authorization; build a separate historical wrapper with distributional—not
observed-year weather-paired—comparison. Existing future wrapper intentionally
rejects undocumented periods. Historical-source differences must be assessed
before attributing all future out-of-range heat to forced warming. No need
to rerun completed future calculations or broaden the two-row pilot first.
Response transport, CO2/adaptation, welfare and GIVE pulse links still remain.
Do not export barred diagnostic coefficients or loosen failed promotion gates.
Older NEXT/permission text below is superseded by this block.

## Latest: independent IPSL pair and exploratory window check COMPLETE

After b413412, two public IPSL cutouts were acquired and four crop/scenario
joint products validated (same29°Cmai/30°Csoy,2042–2049,two latitude rows).
IPSL reverses GFDL rainfall/dry-spell signs: rain+22.63/+26.23mm and dry
spell−1.33/−0.38days for mai/soy. Stage2heat rises+12.16/+12.67°C·days.
Do not promote one-model direction as robust. The new18comparison window
sensitivity uses resident GFDL/IPSL/MPI rainfall over2032–39,2042–49,2052–59;
IPSL/MPI change signs in the middle window. Previously saved full28year rain
differences are negative for all3models/bothcrops. Shared middle-window
rainfall summaries match the completed joint-climate calculations EXACTLY.
Read`IPSL_AND_WINDOW_RESULTS_20260908.md`. These remain climate diagnostics,
not yield losses or SCC. All real jobs and10wrapper/comparison/window tests
passed; maximum sampled RAM486.83MiB. New IPSL batches27.12/27.18MiB each.
All jobs have finished; no detached analysis process. Do not redo this work.

NEXT executable priority: extend matched daily-heat inputs to2032–2059,
starting with GFDL SSP126/SSP585 missing2031–2040and2051–2060decades. The
2041–2050cutouts are resident and must be reused. Query exact source catalogue
metadata; do not infer source IDs/hashes. Keep two-row server cutouts, same
model/member/version and bounded sequential acquisition. `validate_cutout`
currently hardcodes2041–2050 dates: generalize with explicit registered
start/end dates and chronology tests before using other decades. Existing
heat builders already accept multiple daily files, but the new source-bound
wrapper must validate every file's lineage, common grid and contiguous dates
before constructing28year crop windows. Preserve original pilot outputs.
Measure RAM and use1GiB first (up to approved4GiB if scientifically justified),
one numeric thread,<=64MiB new disk per bounded batch and>=130GiB free.
Do not request individual download approval. Retained full28year nonlinear
rainfall tables are already built; do not reconstruct them.

The short-window sign sensitivity makes this higher value than adding more
eight-year pilot fits. Monetary-source/cost/inventory and global-response
transport work remain unfinished and independent. All older next-step or
approval-pending statements below are historical and superseded.

## Latest: matched SSP585/SSP126 inputs and comparisons COMPLETE

September8 after commit84b3e6f: acquired the separate registered SSP585 cutout
and constructed maize29°C/soybean30°C heat for both calendars. No original
source/config/approval was relabeled. Exact paired joint inputs contain
4,000maize/2,616soy crop-years,500/327cells,2042–2049,39.25/39.75N only.
Higher-minus-lower equal-cell-average seasonal rain−9.86/−19.98mm, longest
dry spell+0.85/+1.05days, stage2degree days+20.50/+18.60°C·days. Geographic
rainfall signs vary. These are NOT global averages, yield losses or SCC.
SSP585 historical heat-range any-feature outside shares79.79%/75.42% on
2,336/1,192evaluable rows. See`PAIRED_HEAT_CLIMATE_RESULTS_20260908.md`.
Five new synthetic tests plus4existing join tests pass; all real jobs passed.
Largest sampled group RSS484.09MiB; SSP585 retained outputs27.03MiB. All jobs
finished; no detached analysis process remains. Do not rebuild this pair.

NEXT climate step: a matched independent ESM comparison (IPSL-CM6A-LR is
already in the retained balanced rainfall basis), SSP126 andSSP585, same
2041–2050 raw period/2042–2049 crop years and two latitude rows. Query official
catalogue metadata to identify actual member/version/file hashes and prepare
new isolated configs. Current wrapper still hardcodesGFDL-ESM4/r1i1p1f1:
generalize explicitly with source-identity tests before any other-ESM run;
do not merely relabel outputs. Keep standing authorization, sequential jobs,
<=64MiB per batch and >=130GiB free; no per-file permission requests.
One additional paired ESM directly checks whether the first result's direction
survives internal variability/model differences. No global bulk acquisition.

Next economic work remains locating actual K.4 monetary source/cost/inventory
conventions and harmonized calorie/revenue inputs. Full HultgrenSectionK
review and the price/quantity-only implementation are already complete.
Raw publication and climate files stay ignored. All older NEXT or pending-
permission language below is historical, superseded by the newest blocks.

## Latest completed work and next executable step (September8, later run)

Soybean30°C heat, both calendars, is COMPLETED from the resident SSP126 file.
Exact rainfall/control identity and degree-day/count bounds versus29°C pass;
2,616joint climate rows. Historical30°C ranges:703/1,192evaluable rows outside
at least one feature(58.98%), not damages. Eight wrapper/range tests pass.
Read`SOY_HEAT30_RESULTS_20260908.md`; do not rebuild30°C as unfinished.

Hultgren95page supplement ACQUIRED (34,800,087bytes) and Section K fully
text/visually reviewed(PDF79–88, SI-76–85). Its3published market scenarios and
39% price-level storage shrinkage are verified. Independent price/quantity-
only component`src/anticipated_weather_market.py` passes4test groups; no
surplus/damage/SCC result.13vs15year expectation window and55%vs57.25% listed-
number arithmetic remain explicit ambiguities. Source/code scope findings:
`HULTGREN_WELFARE_SOURCE_REVIEW_20260908.md`. Public GitLab API works, but
inspected main-figure/Table1 directories did not locate monetary K.4 code.
Do not redownload the supplement or repeat the completed section review.

NEXT executable climate task: prepare and acquire the matching small
GFDL-ESM4 SSP585 daily Tmax2041–2050 spatial cutout, same member/version/grid
and four calendars, under STANDING authorization. Read the existing
`prepare_heat_subset_pilot.py` and its config/receipts; use a NEW scenario-
specific config/receipt and validate official catalogue identity/rights before
submission. Do not mutate/relabel the SSP126 config, child or recorded approval.
Generalize acquisition for the registered new job with clear standing-
authorization provenance, retaining byte caps/no unsafe ZIP extraction/no
automatic uncertain-request retry. Process sequentially with <=1GiB sampled
RAM, <=64MiB new disk per batch and >=130GiB free; no per-file permission
question. Then build29°C maize/30°C soybean joint inputs and exact paired
scenario differences. These are not no-climate-change or marginal-CO2 paths.

Next economic task: locate the actual monetary-replication source/license or
document a separately justified cost/inventory convention; do not feed the
new storage-adjusted prices into old equilibrium-surplus code. Baseline
calorie/revenue and transport/CO2/adaptation links remain unfinished. All jobs
from this run finished; no detached analysis process remains. Scheduled
continuation remains active with routine notifications muted. Older next-step
and permission-pending text below is historical and superseded by this block.

## September 8 standing download authorization — supersedes older approval blockers

User instruction: "hide the continuation notices. Don't ask for approval to
download data." The existing heartbeat is still ACTIVE, with routine
notifications muted through `notificationPolicy=failed_runs_only`; failure
notifications can still appear. Its schedule and target are unchanged. This
setting does not claim to remove already-rendered continuation cards/history.

Necessary project data and research inputs may now be acquired without
per-file approval. Old one-file-only and pending-download-approval statements
below are historical, not current blockers (including the small welfare
methods supplement). Preserve truthful authorization records: the original
pilot approval remains unchanged; document this standing direction for new
acquisitions rather than inventing a new user quotation for each file.

Memory, lawful-access, provenance, isolation and storage safeguards remain.
Operational conservative default: below150GiB free, stream small cutouts or
research inputs, at most64MiB new disk per acquisition/processing batch,
tracking cumulative retained bytes and preserving at least130GiB free. The
130GiB floor is an assistant-selected safeguard, not a number requested by the
user. No full-global downloads, evicted raw-climate rehydration, new purchases
or restricted-access circumvention. If an acquisition cannot safely fit,
continue existing-data/model work rather than repeatedly asking for download
permission. The next scientific step remains resident-file soybean30C heat.

Updated September 8, 2026 UTC after real cutout acquisition, two-crop heat joining
and historical heat-range comparison. The project
is **not complete**. At this checkpoint all jobs listed below have finished;
there is no deliberately detached analysis process. The active five-minute
in-task continuation should resume substantive work, not report this status
unchanged. Recheck processes/Git state before starting to avoid overlapping
another run. Chain successive bounded steps within an active turn.

## Completed: do not restart these analyses

1. U.S. direct-practice rainfall associations with baseline, 29°C and 30°C
   daily heat controls: 24 fits; geographic state-omission sensitivity done.
   `us_county_validation/US_DAILY_HEAT_ASSOCIATION_RESULTS_20260907.md` and
   `data/provenance/us_daily_heat_rainfall_associations_20260907.json`.
2. Global historical moisture associations and country-year control sensitivity:
   `GLOBAL_COUNTRY_CONTROL_RESULTS_20260907.md`. Soybean quantity attenuates
   toward zero under country-year controls. Predictive improvements remain
   uncertain; do not select timing on coefficient significance alone.
3. Direct climate comparisons: 60 short-period/five-ESM and 252 longer-period
   crop/calendar/subset comparisons, with narrow two-latitude scope.
   `CLIMATE_SCENARIO_CONTRAST_RESULTS_20260907.md` and
   `CLIMATE_CONTIGUOUS_CONTRAST_RESULTS_20260907.md`. All 60,368 shared maize
   crop-year records match exactly for all 11 features. Eight new synthetic
   tests pass across the two comparison scripts.
4. Independent constant-elasticity welfare-accounting core: seven synthetic
   tests pass, but no empirical calibration or exact published-equation
   replication. `WELFARE_ACCOUNTING_PROTOTYPE.md`.
5. U.S. supported-range rainfall curves reproduce all 24 original fits exactly.
   Twelve paired irrigation-practice difference fits recover all original slope
   differences within 3.22e-15 and account for shared county/year errors.
   Seven new synthetic tests pass. Three scientific figures were rendered and
   visually inspected. Full results:
   `us_county_validation/US_RAINFALL_CURVE_AND_IRRIGATION_RESULTS_20260907.md`.
   Do not rerun these as unfinished. Raw/per-observation predictions were not
   exported. Non-irrigated associations are stronger, but are not causal
   irrigation benefits or adaptation values; within-county support is limited.
6. All36normalized hypothetical market states using six published
   Roberts–Schlenker TableA8 alternative elasticity columns pass checks.
   `WELFARE_NORMALIZED_SENSITIVITY_RESULTS_20260907.md`. These are not empirical
   damages or calibration. Three synthetic tests pass after a caught wrapper
   derivative correction; failed logs retained. Do not repeat source searches
   or treat this as a finished welfare link.
7. One official ISIMIP server cutout job finished with no errors; archive HEAD
   length12,891,438bytes. No local climate bytes downloaded. Job receipt:
   `data/provenance/heat_subset_server_completion_20260907.json`.
   `--calendar-by-coordinates` added to both heat builders; two synthetic tests
   reproduce full-grid outputs exactly below214MiB sampled RSS. Do not repeat
   submission or these tests as unfinished.
8. Future nonlinear rainfall basis completed on18balanced maize/soy ×
   GFDL/IPSL/MPI × SSP126/370/585 products,208,404rows,500/327supported cells.
   Six new synthetic tests pass. Historical marginal-range comparison also
   completed:292/149cells have observed historical exposure ranges; stage2
   mean temperature is outside those ranges in46–73% of SSP585 crop-years.
   `FUTURE_WEIGHTED_PRECIPITATION_RESULTS_20260907.md` contains both calculations,
   restrictions and reproduction. These are not yield projections. Existing
   historical builders remain unchanged. Do not reconstruct or repeat them.
9. `scripts/run_authorized_heat_subset_pilot.py` now implements the capped
   acquisition-to-season/stage-heat chain, with an explicit matching user
   approval record required before any network request. No real approval
   record has been created and no archive downloaded. See
   `AUTHORIZED_HEAT_SUBSET_WORKFLOW_20260907.md` for invocation, safety checks
   and synthetic-test limits. Four test groups pass; the final run sampled
   75.06MiB peak group RSS. No acquisition process is running. Do not rebuild
   this workflow or repeat its tests as unfinished.

## Next useful executable step

**September8 superseding state:** User replied "yes" to the single12.3MiB
download/64MiB total disk exception. Actual approval is recorded only in ignored
`data/interim/heat_cutout_authorization_20260908.json`. Acquisition and all
real validation succeeded; do not download or rerun the original pilot again.
Same-file two-crop/four-calendar29C heat is built and joined to rainfall:
4,000maize/2,616soy rows,500/327cells,2042–2049,GFDL-ESM4 SSP126. Historical
heat-range diagnostic also completed; any-of-six outside fractions64.34%/57.97%
on2,336/1,192evaluable rows. Six new synthetic tests pass. Peak512.03MiB sampled
RSS across the real jobs, combined pilot outputs27.00MiB. All jobs finished;
none deliberately detached. See`REAL_HEAT_CUTOUT_RESULTS_20260908.md`.

**Next executable:** Build soybean30C seasonal/stage heat from the SAME resident
`data/interim/authorized_heat_subset_real_20260908/tasmax_cutout.nc`, both
calendars, without another download. Preserve existing29C outputs; use new
paths, reconcile and weight as for the completed29C products. Historical
soybean locked controls use30C, so29C cannot substitute. The existing
`scripts/extend_heat_cutout_two_crops.py` is deliberately29C and already run;
do not pretend it supplies30C or rerun it unchanged. Keep all combined new
outputs within the original64MiB budget and monitor at1GiB sampled RSS.
Then prepare a tightly scoped matched second-scenario acquisition proposal;
the user approved ONE file only, not unrestricted climate downloads. No yield
projection/causal attribution is enabled by these input diagnostics. The
separate Hultgren PDF download request remains unanswered.

The following September7 approval-pending text is historical and superseded
ONLY for the one climate cutout and its completed same-file processing:

Check whether the user approved the async request for a one-file12.3MiB
climate-cutout download with64MiB maximum additional disk occupancy. If yes,
use the now-implemented bounded workflow, inspect ZIP members/sizes before
extraction, validate real coordinates/dates/units and derive/reconcile
maize/noirr2042–2049 seasonal and stage heat with29C threshold. Read
`LOW_STORAGE_HEAT_SUBSET_PILOT_20260907.md` first. Do not download before this
exception is approved; also read `AUTHORIZED_HEAT_SUBSET_WORKFLOW_20260907.md`
and record only the user's actual approval, never a synthetic authorization.
Do not reinterpret server completion as content
validation. Both archive and uncompressed member must fit the64MiB cap.
No full global raw files, imputation or bulk expansion. The existing job is
finished; don't poll it repeatedly. Its URL may expire after the service TTL.
After heat construction, join it to the newly completed regime-basis pilot
using exact crop/grid/year/member/scenario/calendar identities. Never fill
missing Tmax with stage mean T or multiply rainfall means by response slopes.
The range results now quantify substantial temperature extrapolation, so a
joint climate-to-yield projection still needs an explicit transport strategy.
Do not silently clip temperatures or treat marginal inside-range diagnostics
as validation. No new user approval for the download has arrived as of this
checkpoint; the existing request remains pending and should not be repeated.

While that decision is pending, continue the missing economic/response link
using existing small inputs or read-only public metadata. The six published
elasticities are a sensitivity, not selected production parameters. Exact
aggregation and baseline market-value scope, transferability and joint
uncertainty remain unresolved. Replication DOI10.3886/E112674V1 is located,
but license/code contents are unverified; previous license/download and
documents-folder web clicks failed. Do not retry unchanged failure paths or
substitute a figure or another broad audit for missing model work.
The later author-research-page search did not supply an accessible final
paper; the NBER working-paper PDF at
`https://www.nber.org/system/files/working_papers/w15921/w15921.pdf` also
returned403. No new equations/parameters were extracted. The source checkpoint
now distinguishes the completed A8 sensitivity from its superseded lead.
Do not repeat these searches or create additional synthetic exercises merely
to fill scheduled runs. Both requested local-download exceptions remain
unanswered; no new analysis process was launched during this source check.

In parallel with source review where safely possible, continue the actual
global response/attribution/welfare work. Do not
substitute a figure or another audit for those missing links. The future
climate inventory now shows stage mean T in all 132 consumed longer-period
source sets, but no daily Tmax threshold integrals in their stage schemas.
Existing early GFDL heat products cover only 2016–2019 maize/rainfed. A
defensible joint projection now has regime-specific nonlinear rainfall bases
before fixed-area weighting for the balanced two-crop pilot, but still requires
transport validation, CO2/adaptation treatment,
and a matched marginal CO2 path. Do not multiply scenario rainfall means by
the historical log-rain-index slope. Document a bounded source/subsetting
route for missing heat before seeking any new bulk acquisition authority.

Detailed Hultgren welfare-supplement review remains pending the previously
requested one-off approximately 35 MB document download exception (cap36MiB)
or a user-supplied readable copy. The web reader fails on its size. Do not
repeat the same failed PDF searches, relax storage rules, or ask repeatedly
while that decision is unchanged. Other work can proceed independently.

## Constraints and accounting

- Only this precipitation project; preserve wildfire and unrelated files.
- One monitored analysis process; one numerical thread. Maximum allowed
  sampled group RSS4GiB, but use smaller proven budgets. Latest climate jobs
  needed only 225–326MiB. Sampled limits are not kernel-enforced caps.
- Latest free disk about133.61GiB. Below150GiB: no downloads, raw climate
  rehydration or large climate work. Small existing-data outputs may reserve
  starting free disk minus at most64MiB. Do not delete unique/derived inputs.
- The long comparison initially failed the new1e-5°C temperature check;
  diagnosis and the explicit1e-4°C precision amendment are documented in its
  protocol. Retain failed logs/receipts; do not describe them as passing.
- The timing field is a legacy three-window position index, not exact daily
  timing. Window boundaries are0/0.3/0.7/1, index weights1/6,1/2,5/6.
- No empirical climate-attributable agricultural welfare or SCC estimate yet.
- Stage only owned code, documentation and aggregate provenance. Raw/interim
  data and outputs remain ignored. Push reviewed commits with
  `git push origin HEAD:precipitation-scc`; never push to the wildfire branch.
- Preserve pre-existing untracked U.S. sensitivity receipts and presentation
  artifacts. Coordinator updates are best effort; respect any messaging denial.
