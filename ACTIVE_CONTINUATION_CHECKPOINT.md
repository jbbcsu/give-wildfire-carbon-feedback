# Active continuation checkpoint

Updated September 7, 2026 after the approval-gated cutout workflow implementation. The project
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
