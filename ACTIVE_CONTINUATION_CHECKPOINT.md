# Active continuation checkpoint

Updated September 7, 2026 after U.S. curves and paired irrigation contrasts. The project
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

## Next useful executable step

Advance the published market-elasticity route in
`WELFARE_ELASTICITY_SOURCE_CHECKPOINT_20260907.md`. The Roberts–Schlenker AER
publisher page is verified and has replication-package/appendix links. Follow
those links with read-only web tools, inspect exact version, license, equations
and parameter uncertainty, and evaluate compatibility with the independent
constant-elasticity core. Do not use search-snippet numbers as calibration or
assume a working paper matches the published version. The separate NBER
summary returned403; do not repeat that failed request. This is an independent
route while the Hultgren document exception remains pending. If a verified
published equation/parameter mapping is available, implement a narrowly
tested, clearly labeled sensitivity without consuming unvalidated yield
shocks or promoting SCC. Otherwise record the exact remaining evidence gap.

In parallel with source review where safely possible, continue the actual
global response/attribution/welfare work. Do not
substitute a figure or another audit for those missing links. The future
climate inventory now shows stage mean T in all 132 consumed longer-period
source sets, but no daily Tmax threshold integrals in their stage schemas.
Existing early GFDL heat products cover only 2016–2019 maize/rainfed. A
defensible joint projection also requires regime-specific nonlinear bases
before fixed-area weighting, transport validation, CO2/adaptation treatment,
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
- Latest free disk about133.77GiB. Below150GiB: no downloads, raw climate
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
