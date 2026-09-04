# Completion review and execution plan — 4 September 2026

## Assessment

The project has substantial reusable data engineering and real preliminary
results. It does not yet have an empirically calibrated global agricultural
welfare replacement or a precipitation SCC. The recent sequence of commits
has favored additional support audits over closing the response, climate,
and welfare links. Stop treating each new diagnostic as a reason to add
another prerequisite. Finish a bounded analysis, retaining adverse results.

This is a repository and saved-evidence review, not an independent rerun of
every result or a new literature review. Reviewed heads: precipitation
`8e6f13f`, fisheries `c6a6926`. Existing untracked presentation and fisheries
export files belong to other work and are excluded from this review.

## Evidence that is usable now

| Track | Saved evidence | What it establishes |
|---|---|---|
| U.S. reported non-irrigated corn | 7,013 county-years / 361 counties; fitted +100 mm contrasts +11.07%, +7.72%, +3.59% at lower/median/upper precipitation quartiles | Regional historical associations, conditional on the existing controls |
| U.S. reported non-irrigated soy | 4,844 county-years / 255 counties; quantity and timing associations; timing improves the registered geographic/terminal/extreme prediction tests | A promising regional timing result requiring heat and sampling robustness |
| National high-rainfed-share counties | 15,660 corn and 14,553 soy observations in the PDSI regressions; PDSI -2 versus zero fitted contrasts about -8.3% and -7.9% | Selected all-practice county moisture-stress associations; no isolated rainfall effect |
| Global maize/soy | Continuous 1982–2016 candidates exist. Saved 209,036-pair diagnostic has seasonal-total RMSE improvements below 1%; drought rankings vary by metric and stress | Usable feature infrastructure and mixed predictive evidence; full continuous response estimation remains a priority |
| Climate | Daily-derived quantity, stage shares, dry spells, extremes and temperatures; bounded two-latitude climate products across models/scenarios; 88 centered templates in the contiguous pilot | Engineering and local scenario diagnostics, not global agricultural projections |
| Fisheries | Complete 20-file FishMIP matrix with control comparisons; large raw declines shrink substantially after control adjustment | Biophysical scenario evidence with material structural uncertainty |
| GIVE | Replacement harness runs with synthetic zero responses and removes the legacy agriculture connection | Integration feasibility, not empirical welfare or SCC |

Evidence sources: `US_DIRECT_PRACTICE_PRECIPITATION_PRELIMINARY_RESULTS.md`,
`us_county_validation/US_NATIONAL_ALL_PRACTICE_PDSI_PRELIMINARY_RESULTS.md`,
`GLOBAL_DIRECT_SCPDSI_DIAGNOSTIC_RESULTS.md`, `RESULTS_STATUS.md`, and
`../ocean_fisheries_scc/README.md`. The U.S. independent-validation receipt
records agreement across 324 numeric fields within 1.04e-13; this demonstrates
computational reproduction of the specified estimator, not identification.

## Problems to resolve, in order of consequence

1. **Separate completion requirements by deliverable.** Historical response
   estimation does not require a validated future-climate emulator. A U.S.
   empirical paper can finish independently of global welfare integration.
   Preserve hard scientific checks, but do not couple unrelated gates.
2. **Global outcome support.** GDHY gridded outcomes must be reviewed for
   shared source statistics and construction-induced dependence. Grid-cell
   counts are not counts of independent observations. Specify clustering and
   a national-statistics or independent subnational sensitivity accordingly.
3. **Climate architecture.** The pooled dependence diagnostic fails for MRI;
   its maximum discrepancy is 0.192318 versus the frozen 0.15 threshold, and
   scenario matching does not remove the discrepancy. Eight 21-year windows
   shifted one year apart overlap heavily. A count of 51 templates is a
   computational design requirement, not proof of statistical sufficiency.
   Also, applying a nonlinear yield function to smoothed mean weather differs
   from averaging annual yield responses. Quantify that distinction before
   promoting the smoothed route.
4. **Identification and transport.** Fixed effects and predictive skill do
   not by themselves justify causal or global extrapolation. Specify the
   weather-shock estimand, concurrent heat treatment, omitted-driver risks,
   geographic support, and long-run adaptation interpretation explicitly.
5. **Welfare is unfinished.** Yield percentages cannot simply be multiplied
   by crop revenues and called welfare. A global crop subset cannot replace
   all agriculture without an explicit residual-sector accounting solution.
6. **Resource enforcement.** `run_command_with_resource_receipt.py` records
   child peak RSS after completion; it does not terminate excessive-memory
   jobs. The corrected GMST streams by file, but a wrapper does not cap Codex
   app memory. Historical attribution of the freeze to one process remains
   probable, not proven. Current available disk is about 134 GiB, below the
   150 GiB reserve; no bulk acquisition is appropriate now.
7. **Manuscript structure.** The main manuscript has 1,045 lines and Methods
   1,559, with extensive engineering chronology. Consolidate into a research
   argument, moving run histories into provenance. Some status documents
   still carry August dates despite September additions.

## Work package A: produce the September 9 evidence package

Dates are targets, not a guarantee of statistical significance or SCC output.
No presentation is required unless requested.

### September 4: freeze deliverables and protect the machine

- One concise results table per track, bound to the saved input/result hashes.
  Confirm each quoted number against its result file and resolve stale notices.
- Add a monitored job runner with a process-tree memory budget and free-disk
  check. Test termination using small synthetic allocations. Use a single
  heavy worker, bounded logs, atomic outputs and resumable partitions.
- Do not rerun the unbounded calculation or automatically restore evicted raw
  blocks. Use existing derived inputs. Freeze additional-sector expansion.

### September 5–6: U.S. agricultural results, the closest completed analysis

- Reproduce the regional corn/soy estimates; retain total quantity as the corn
  reference and test timing for soy with the same support and heat controls.
- Run a finite sensitivity matrix: nonlinear/extreme heat; fixed-calendar
  alternative; reporting-period restriction; geographic and time holdouts;
  county clustering plus a spatial-dependence sensitivity. Record all models,
  including worse predictions and nulls. Previously used holdouts remain
  development evidence; do not relabel them independent confirmation.
- Compare rainfall and PDSI on identical observations. Explain the drought
  model's joint water/temperature interpretation. Add SPEI only if required
  inputs and a leakage-safe implementation can finish within this window.
- Resolve county coverage with a documented exclusion/geometry rule without
  changing thresholds to obtain desired results. One problematic county must
  not indefinitely block valid counties. Report exclusion geography and
  selection explicitly; call the national panel selected, not representative.
- Deliver response curves with uncertainty, a coverage map, and an out-of-
  sample comparison table. Recheck nonlinear percentage transformations and
  support of each illustrative rainfall redistribution.

### September 6–7: global historical evidence and fisheries

- Use the continuous maize/soy panel for one frozen response comparison:
  heat plus rainfall total; added timing/extremes; competing drought family.
  Partition by crop and validation fold; avoid a dense global dummy matrix.
  Run held-out time and geographically separated tests with source-appropriate
  clustering. Report the effective sample and outcome provenance.
- Preserve the current two-latitude climate figures as explicitly local
  diagnostics. They cannot be labelled global climate/agricultural results.
- Fisheries: present forced and control trajectories together, model/scenario
  contrasts and their structural spread. Stop adding variations on which of
  two structural axes is larger. Use existing literature audit to identify
  the shortest defensible economic bridge: bioeconomic profit/management and
  seafood nutrition are distinct pathways with distinct incidence.
- Deliver a fisheries results note and short methods outline. Without a
  calibrated bridge, do not supply new fisheries dollars or an SCC number.

### September 8: independent reproduction and editorial pass

- Reproduce the final selected tables with one independent calculation of
  sample counts, transformations and uncertainty. Review temperature and
  irrigation interpretation, units, geography and missingness.
- Write a concise preliminary-results memo with figures and limitations,
  giving the exact remaining steps to SCC. Archive outputs and commit reviewed
  code/docs. September 9 is a preliminary-results deadline, not a deadline
  for an unsupported global SCC estimate.

## Work package B: finish the standalone studies after September 9

1. **U.S. paper:** complete the response and sensitivity package above; add
   climate projections only on validated exposure support. Write the main
   result around whether quantity, timing, or drought adds explanatory value
   and how results differ by reported irrigation practice. Completion means
   reproducible figures/tables, uncertainty, data availability, Methods and a
   claim-by-claim review—not simply a populated manuscript template.
2. **Global agriculture:** lock crop/outcome coverage and estimate response
   draws. Explain whether a causal interpretation is defensible and precisely
   what assumptions it needs; otherwise finish a clearly labelled empirical
   sensitivity study while the identification gap remains open.
3. **Climate bridge:** first evaluate the fitted yield response on coherent
   existing annual scenario feature vectors; these preserve realized feature
   relationships. For broad/global results expand spatial support in streamed
   blocks when storage permits. Compare a response-level warming emulator to
   the current feature-level route. Treat this as a new, versioned design
   motivated by observed failures; preserve old adverse tests and reserve
   independent validation. Scenario contrasts alone do not identify a pulse
   derivative. Validate marginal FAIR response, residual variability,
   extrapolation, zero pulse and decreasing-pulse convergence separately.
4. **Adaptation:** define fixed technology explicitly. Estimate trend
   adaptation from observed variation only with an identification argument;
   otherwise report externally calibrated scenarios. Define upper adaptation
   as a constrained, feasible sensitivity including costs. Never use arbitrary
   scaling factors as if estimated adaptation parameters.
5. **Welfare/GIVE:** select and document a crop-market welfare bridge with
   trade, prices and producer/consumer incidence. Map crop and country coverage
   to GIVE. Compare the original baseline agriculture with the replacement on
   identical draws; report both total-agriculture SCC and the replacement
   difference. A precipitation attribution requires coherent conditional
   climate counterfactuals and an explicit convention for interactions.
6. **Fisheries economics:** examine the already identified Blue-SCC benchmark
   and underlying bioeconomic/nutrition inputs. Resolve reuse rights and
   baseline compatibility; distinguish profit, revenue, surplus and health.
   EEZ allocation is required only if the selected estimand needs it. A global
   biophysical diagnostic need not wait for EEZ boundaries. Carry management,
   trade, substitution and nutrition assumptions into uncertainty explicitly.
7. **Publication:** make each main paper a compact question–method–result–
   implication narrative. Methods must reproduce acquisition, feature
   construction, fitting, uncertainty and integration; run logs belong in
   provenance. Finish with an independent critical review before submission.

## Decisions and stopping rules

Existing authorization suffices for the historical fits, resource fixes,
bounded validation and manuscript reorganization. No new hardware is needed
for that work. A welfare-model choice, a materially different adaptation
assumption, or a newly required licensed source should come to the user as a
concrete recommendation with alternatives, not an open-ended blocker.

Retain old preregistrations and failed results. A revised method may be tested
under a new version with its post-result motivation disclosed; it may not
retroactively pass the old protocol. Limit routine audits to those that change
an estimand, estimate, uncertainty statement, or reproducibility claim. Report
progress in those terms rather than counts of receipts or commits.
