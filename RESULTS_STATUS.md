# Analysis status and claim ledger

Entries are chronological snapshots, newest first. An older entry's
"in progress" or "not yet estimated" describes its date, not the current
state; use the newest relevant entry and its linked result receipt.

## September 23 published global maize response reproduced

A 345,639,713-byte maize regression dataset omitted from the current Hultgren
et al. replication tree was recovered from the repository's public Git history
and hash-bound to commit `dae5fe8d0d4a260328e4baa45b547368bd6790b3` and blob
`da2ac691b32db1b98dea95b8f0ff4256659c8a96`. The raw Stata data remain ignored
and are not redistributed because no repository license was located. Running
the published 49-term model reproduces the exact 377,824-observation sample,
cluster counts, fixed effects, regressor order, and coefficient vector (relative
L2 error `2.42e-14`); covariance relative L2 error is `2.65e-6`. A bounded
50,000-row chunk audit over all 412,282 source rows confirms that the three
phase-specific linear and quadratic precipitation terms sum to their respective
full-season terms within single-precision tolerance. This establishes the
published historical maize response and phase-basis arithmetic. It does not
validate future weather transformation, moderator trajectories, damages, or an
SCC increment. See `HULTGREN_MAIZE_RESPONSE_SOURCE_RESULTS_20260923.md` and the
strict provenance receipt.

## September 22 five-ESM late-century crop-calendar drought exposure

All 15 five-ESM by three-SSP 2091--2100 daily climate cases now pass
case-level climate and crop-window validation. Frozen observational
1982--2011 parameters convert monthly precipitation minus Hargreaves--Samani
reference evapotranspiration to SPEI-1/3/6 without refitting the future.
GGCMI calendars and fixed MIRCA-OS v2 hectares produce maize/soybean season,
stage and preplant summaries for harvest years 2092--2099. An independent
matrix implementation reproduced 1,350 case means, 900 named-model contrasts
and 180 cross-model records in 7,065 checks with zero saved-precision
disagreement.

For the primary rainfed crop-season SPEI-3 diagnostic, SSP3-7.0/SSP5-8.5
minus SSP1-2.6 five-model mean differences are -0.449/-0.662 for maize and
-0.326/-0.542 for soybean. All five named ESMs are negative for each of these
four contrasts. Across five windows, three SPEI scales and three fixed area
bases, at least four of five models are negative in every one of 180
crop--scenario cells. These signs are not probabilities or confidence
intervals. Scenario exposure is not anthropogenic attribution, a marginal
CO2-pulse response, yield loss, damage, or SCC. No coefficient is applied
because the global drought-response promotion gate remains closed. See
`FIVE_ESM_LATE_DROUGHT_EXPOSURE_RESULTS_20260922.md`.

## September17 contiguous global rainfed-maize source and centered features

The GFDL-ESM4 SSP1-2.6 2032--2059 full-grid, daily-derived maize/rainfed
feature panel passes an independent 28-year audit: 67,420 calendar cells,
1,887,760 season rows, 5,663,280 stage rows and 252 new raw-daily
cell-season reconstructions. A separate centered 21-year source-feature
operation also passes all 36 tile receipts and an independent global
audit: eight 2042--49 centers, 539,360 season and 1,618,080 stage rows,
with 168 independent annual-feature mean reconstructions. Peak sampled
audit RSS was 177 MB (annual) and 413 MB (centered); the largest
feature tile used 273 MB. Failed first audit/parity attempts and their
specific empty-tile/schema corrections are retained, not hidden.
These heavily overlapping one-ESM/one-scenario source windows are **not**
an identified GMT-to-precipitation response, yield effect, damage, or
SCC result. See
`GLOBAL_CONTIGUOUS_GFDL_28YR_AND_CENTERED_RESULTS_20260917.md`.

## September17 GFDL within-SSP1-2.6 two-window crop-weather diagnostic

GFDL-ESM4 rainfed-maize 2042--2049 and 2092--2099 full-grid panels
pass exact 144-frame generic/bespoke anchor parity, both independent
eight-year source audits, and a 45/45 independent weather-arithmetic
audit. Equal-cell late-minus-mid means are +10.656 mm season rain,
+0.800 wet days, -0.071 maximum dry-spell days and +1.299 mm Rx5day.
Same-realization mean GMST is -0.02364 K later-minus-mid: the tiny
negative temperature contrast alongside positive rainfall illustrates
why dividing short-window rainfall differences by GMST is invalid.
The preregistered same-SSP UKESM comparison passes exact metadata
alignment and its own 315-statistic audit; UKESM season rain is
+7.922 mm and Rx5day +1.410 mm, but its GMST change is +0.370 K.
All nine equal-cell mean weather-feature signs match across these
two ESMs; no pooled estimate, forced per-K response, crop-yield
effect, damage or SCC follows. See
`GLOBAL_DIRECT_DAILY_GFDL_TWO_WINDOW_WEATHER_RESULTS_20260917.md`.

## September17 MRI within-SSP5-8.5 two-window crop-weather diagnostic

MRI-ESM2-0 rainfed-maize 2042--2049 and 2092--2099 full-grid daily panels
pass independent eight-year source/calendar/hash audits, 21 fixed raw-cell
checks per year, and a separate 45/45 weather-arithmetic checker. Equal-cell
late-minus-mid means are +16.063 mm season rainfall, -0.205 wet days,
+0.698 maximum dry-spell days, +4.945 mm Rx5day, and +2.382 C season
temperature. Spatial wet-day median is +0.125 days, opposite its mean;
5th/95th spatial rainfall differences are -124.215/+155.553 mm, not
confidence bounds. Same-realization mean GMST rises 2.249 K. None of
these differences identifies a forced per-K response, yield, damage or
SCC. A pre-result inventory correction recorded GFDL SSP1-2.6 as another
resident two-window candidate; MRI was chosen for generic-pipeline
convenience, not because it was uniquely eligible. See
`GLOBAL_DIRECT_DAILY_MRI_TWO_WINDOW_WEATHER_RESULTS_20260917.md`.
The separate GFDL generic 2042/2092 anchors pass exact 144-frame parity
with their previously audited bespoke versions; remaining years and audits
are in progress. Its different SSP is not an MRI replication.

## September17 three-ESM late-window crop-weather sign-stability check

MPI-ESM1-2-HR joins UKESM/IPSL for all three 2092--2099 SSP windows
on 67,420 global rainfed-maize calendar cells. All 72 yearly panels,
nine eight-year source audits, per-ESM 315/90/90 summary arithmetic
checks, and the three-ESM 114/114 merge check pass. For SSP5-8.5
minus SSP1-2.6, seasonal rainfall is +7.231/+23.543/**-1.180** mm
(UKESM/IPSL/MPI): the two-ESM positive-total sign fails the third
model. Rx5day is +6.288/+7.748/+3.089 mm; wet days and stage rain
have mixed signs. These short one-window weather contrasts are not
forced precipitation-per-K, crop-yield effects, damages, or SCC.
See `GLOBAL_DIRECT_DAILY_THREE_ESM_LATE_WEATHER_RESULTS_20260917.md`.

## September17 two-ESM late-window crop-weather robustness

IPSL-CM6A-LR now joins UKESM1-0-LL for SSP1-2.6/3-7.0/5-8.5
2092--2099 global rainfed-maize calendar features. All 48
ESM×scenario×year full-grid panels and six separate eight-year
cross-year audits pass; the IPSL grouped-table arithmetic check
reproduced 90/90 statistics and the hash-bound two-ESM merger audit
112/112. Under late-century SSP5-8.5 minus SSP1-2.6, equal-cell
season rainfall is +7.231/+23.543 mm (UKESM/IPSL) and Rx5day
+6.288/+7.748 mm, but wet-day differences are -1.056/+0.221 and
early-stage rain -0.938/+1.560 mm: signs disagree for the latter two.
This is two-ESM, short-window weather evidence, not a forced GMT
response, crop-yield effect, damage or SCC. See
`GLOBAL_DIRECT_DAILY_TWO_ESM_LATE_WEATHER_RESULTS_20260917.md`.

## September17 UKESM six-window global crop-weather diagnostic

All three SSP1-2.6/3-7.0/5-8.5 × two 2042--49/2092--99 eight-year
UKESM rainfed-maize windows now have full-grid, daily-source-checked
season/stage features and separate cross-year audits. A pre-registered,
equal-calendar-cell comparison distinguishes seasonal total, stage
rainfall, wet days, dry spells, extreme rain, and temperature. The
independent grouped-table auditor reproduced 315/315 descriptive
statistics. In late-century SSP5-8.5 minus SSP1-2.6, mean seasonal
rain is +7.231 mm, wet days -1.056 days, and Rx5day +6.288 mm; the
spatial distribution is wide. These are one-ESM, short-window
weather-only contrasts, not precipitation-per-K, causal yield/damage,
or SCC. The failed script runs and passed retries are retained.
Details: `GLOBAL_DIRECT_DAILY_UKESM_SIX_WINDOW_WEATHER_RESULTS_20260917.md`.

## September17 UKESM two eight-year full-grid crop-weather windows

UKESM SSP1-2.6 harvest years 2042--2049 and 2092--2099 now pass
source-bound 36-tile, 21-raw-cell-per-year independent checks and
separate cross-year hash/calendar audits. Together: 1,078,720
crop-season and 3,236,160 within-season stage *weather* rows.
The 2042--2049 auditor first failed on an implementation shadowing
error, then passed a separately receipted corrected rerun without
source/feature changes. The eight-year simultaneous tile memory
failure also remains disclosed; one-year workers stayed under the
512 MiB guard. See
`GLOBAL_DIRECT_DAILY_UKESM_TWO_EIGHT_YEAR_WINDOWS_RESULTS_20260917.md`.
No fitted GMT response, yields, damage or SCC follows from the
two-window one-ESM/one-scenario coverage.

## September17 UKESM mid-/end-century source-only anchors and multiyear weather

All UKESM1-0-LL 2042 SSP1-2.6/3-7.0/5-8.5 full-grid daily
rainfed-maize panels passed source hashes, 36 tiles each, and 21
independent raw-cell recomputations per panel. The 2042 matched-cell
scenario rainfall differences are +2.04/-4.06 mm versus SSP1-2.6,
and a separate 92-check numeric reconstruction passes. Six 2042/2092
feature anchors match their SHA-pinned same-realization annual-GMST
parquets and source receipts; this is support alignment, **not a
precipitation-per-K fit**. An eight-year UKESM SSP1-2.6 2092--2099
panel (539,360 season rows, 1,618,080 stages) passed independent
per-year and cross-year audits; a simultaneous eight-year tile
previously exceeded 512 MiB and was stopped, so safe one-year
workers were used. See `GLOBAL_DIRECT_DAILY_UKESM_TWO_WINDOW_ANCHOR_RESULTS_20260917.md`
and `GLOBAL_DIRECT_DAILY_UKESM_MULTYEAR_ENGINEERING_STATUS_20260917.md`.
No yield, damage or SCC is inferred.

## September17 five-ESM × three-SSP daily crop-weather source cohort

All 15 ISIMIP3b 2092 rainfed-maize ESM/SSP panels now pass source
hashes, 36 bounded tiles and 21 fixed independent raw-cell checks per
panel. Cohort audit rehashed 30 raw files and all feature partitions;
exact calendar masks and resource receipts pass. Total 1,011,300
seasonal cells and 3,033,900 stages; maximum sampled builder RSS
247,218,176 bytes and 137 GiB disk free. Two source-receipt schema
stops were disclosed and normalized against declared, hash-pinned
metadata. This is input engineering for **one year**, not a fitted GMT
response, yields, damages or SCC. See
`GLOBAL_DIRECT_DAILY_FIVE_ESM_2092_COHORT_RESULTS_20260917.md`.

## September17 UKESM late-century scenario weather comparison: descriptive only

Full-grid UKESM1-0-LL SSP1-2.6/3-7.0/5-8.5 harvest-year 2092 daily
rainfed-maize features pass source hashes, 36/36 bounded tiles per
scenario, exact crop-calendar masks and 21 independent raw-cell checks
per scenario. On 67,420 equal-weighted calendar cells, the mean seasonal
rain differences relative to SSP1-2.6 are +9.60/+26.23 mm, while only
50.2%/52.2% of cells are wetter; the SSP5-8.5 dry-spell mean difference
is near zero. A separate 92-check keyed-merge arithmetic reconstruction
passes. These are one-year scenario weather differences, not GMT causal
responses, yields, damages or SCC. See
`GLOBAL_DIRECT_DAILY_UKESM_2092_THREE_SCENARIO_RESULTS_20260917.md`.

## September17 full-grid rainfed-maize climate features: input only

The GFDL-ESM4 SSP1-2.6 daily `pr`/`tas` source produces independently
checked full-grid `mai_noirr` features for harvest years 2032--2039,
2042 and 2092: ten years, 674,200 crop-calendar cell-year rows and
2,022,600 stage rows across three source decades, still only one ESM and
one scenario. Each year passed 36 bounded tiles and 21 fixed raw daily
cell recomputations; exact calendar-mask and physical checks passed for
both the eight-year panel and later anchors. Maximum sampled builder RSS
was 255,983,616 bytes, with 137 GiB disk free after the work. These are
weather-input engineering results, **not** an estimated GMT response,
yield, agricultural damage or SCC. See
`GLOBAL_DIRECT_DAILY_GFDL_2032_2039_MAIZE_PANEL_RESULTS_20260917.md`
and `GLOBAL_DIRECT_DAILY_GFDL_THREE_WINDOW_ANCHOR_RESULTS_20260917.md`.

## September16 fixed-forecast U.S. state-composition check

The post-result 2017 <=10% all-practice NASS/NOAA terminal forecast
decomposition reproduces exact parent scores and passes 498 independent
state/score checks. Soybean's joint-pattern gain remains positive after
omitting any one state from scoring (minimum +0.00589 log-yield RMSE), but
only 18/28 state scores favor patterns and North Dakota worsens. Corn's
pooled increment remains near zero and its leave-one-state-out range crosses
zero. This is neither a fresh geographic holdout nor a causal/global/SCC
result. See `US_COUNTY_AVERAGE_STATE_COMPOSITION_RESULTS_20260916.md`.

## September16 GMT-to-precipitation literature feasibility qualification

Published RIME-X, MESMER-M-TP, Kemsley and STITCHES methods cover important
GMT-to-indicator, monthly, wet/dry daily, and archived daily-sequence
functions. They do not automatically satisfy the joint crop-feature/pulse
contract. Current RIME-X template distinctness and five-track catalogue
shortfalls, plus failed MRI dependence stability, prohibit promotion even
if the remaining five-track files are acquired. See the updated
`CLIMATE_PRECIPITATION_EMULATOR_AUDIT.md` and original gate receipts.

## September16 historical direct-practice weather-route sensitivity

The old 11,857 exact NASS irrigated/non-irrigated corn/soy pairs were
refitted with the same county/state-year FE and clustered design using
the new NOAA county-area-average crop-year weather. The previous primary
corn +100mm irrigated/non-irrigated yield-ratio association shifts
−7.550%→−7.525%; soybean primary quantity-plus-timing shifts
−4.324%→−4.306%. A separate QR/cluster-sandwich implementation passed
151 checks. This is post-result measurement robustness of a selected
regional historical association, not causal irrigation, national yield,
climate attribution or SCC. See
`US_PAIRED_PRACTICE_WEATHER_ROUTE_RESULTS_20260916.md`.

## September16 matched U.S. weather-estimator measurement audit

All 11,861 old regional crop/county/year weather keys match the new NOAA
county-average features and identical crop-calendar dates. Median absolute
seasonal-rain differences are 0.621/0.713 mm for corn/soy; maximum-dry-spell
differences are 0.523/0.450 days, with p95 4.774/4.707 days. A separate
source reconstruction passed 191 checks. The two spatial estimators are
not interchangeable for nonlinear weather features, and this old regional
footprint is not national; no yield or SCC response was fit. See
`US_COUNTY_WEATHER_ESTIMATOR_COMPARISON_RESULTS_20260916.md`.

## September16 U.S. irrigation-share screen robustness independently checked

The post-result 2017 <=20/30% and 2022-vintage screens reuse the same
NASS/NOAA sources, county-FE ladder and 2020–2025 years; the fixed 2017
<=10% panel reproduces the primary exactly. Across fixed-2017 screens,
soybean quantity-to-joint-pattern RMSE changes are 0.15546→0.14781,
0.16609→0.15836, and 0.17085→0.16491; corn changes are only
0.18291→0.18224, 0.19161→0.19123, and 0.20525→0.20512. A separate
source/OLS reconstruction passed 498 checks. The 2022 screen is a
test-period composition diagnostic, not prospective validation. The
all-practice outcome is not directly observed rainfed yield; this remains
predictive and not climate/SCC evidence. Numerical runtime warnings in
repeated fits are disclosed with finite/rank/residual and independent-score
checks in `US_COUNTY_AVERAGE_IRRIGATION_SCREEN_RESULTS_20260916.md`.

## September16 PDSI competitor on exact U.S. terminal support

An explicitly post-result PDSI sensitivity retains all 4,075 terminal
county-years and compares moisture representations on identical rows.
Under the common trend, 2020–2025 corn RMSE is 0.18291 for rain total,
0.18224 for the expanded rain-pattern group, and 0.18469 for seasonal-mean
PDSI; soybean is 0.15546, 0.14781, and 0.15307 respectively. The expanded
rain group remains best for soybean under state-specific trends too.
Historical-blocked corn rankings differ from the terminal rankings, so no
stable winner is asserted there. Independent reconstruction passed 96 score
checks. PDSI contains temperature and this is predictive robustness, not
precipitation attribution, a rainfed-yield estimate, or SCC. See
`US_COUNTY_AVERAGE_PDSI_COMPETITOR_RESULTS_20260916.md`.

## September16 independently checked U.S. post-2019 predictive benchmark

On fixed 2017 <=10%-irrigated-share all-practice NASS county outcomes,
1981–2019 fitted county-FE models scored identical 2020–2025 rows. Corn
log-yield RMSE is 0.20494 no-weather, 0.18291 rain-total-plus-temperature,
0.18224 after timing/extremes; the last increment is tiny, changes sign by
year and its conditional state-bootstrap interval crosses zero. Soybean is
0.18919, 0.15546, 0.14781, with the joint timing/extreme group improving
all six terminal years and the historical blocked diagnostic. Independent
raw-feature and prediction reconstructions pass 608 and 68 checks. This is
predictive evidence only; all-practice selected yields are not observed
non-irrigated yields, rain versus temperature is not causally separated,
and no climate-change damage, global transfer or SCC has been estimated.
See `US_COUNTY_AVERAGE_TERMINAL_PREDICTION_RESULTS_20260916.md`.
An explicitly post-result state-trend sensitivity retains soybean's
incremental pattern gain (0.15742 to 0.14769) but not a substantive corn
gain (0.17633 to 0.17525); 36 independent score checks pass. This is
robustness of prediction, not a climate/SCC result.

## September16 complete NOAA nationwide daily source and calendar gate

The 1981–2025 NOAA nClimGrid-Daily county-average source acquisition is
complete: 90 six-month batches, 540 months, 2,160 daily-variable CSVs plus
540 source-version texts, and 2,362,010,369 source bytes. All batches passed
exact URL/HTTP identity, SHA, 3,107-county schema, daily calendar, physical
and bounded-resource checks; raw files remain Git-ignored. The 2010 NASS crop
calendar extension to 2025 reproduced the preexisting 1981–2022 calendar
exactly; yearwise outcome-blind weather features are being constructed.
No yield association, climate-attributable effect, valuation or SCC follows
from source acquisition.

## September16 nationwide daily-weather route passed pilot and entered batches

The fixed three-month NOAA nClimGrid-Daily county-average pilot passed for
January1981, leap February2024 and July2025: four variables, 3,107 identical
county keys, source identities and calendar/physical checks. The first
January run failed an over-tight analyst midpoint tolerance; the disclosed
source-only amendment passed at 0.020°C, with 0.015°C observed. The first
2020 six-month production batch passed its 512MiB/64MiB/130GiB guards.
Sequential, resumable 1981–2025 acquisition is in progress. This route is
not numerically equivalent to previous polygon-weighted weather, and no
outcome relationship has been fit. See
`US_NCLIMGRID_COUNTY_AVERAGE_PILOT_RESULTS_20260916.md`.

## September16 post-2019 U.S. county outcome support acquired and verified

The fixed 2020–2025 NASS all-practice corn/soy county snapshot has 12 source
responses and 16,544 raw API rows; key-only availability audit and 316
independent checks pass. Under the fixed 2017 <=10% irrigated-acreage screen,
2025 positive real-county outcomes number 310 corn and 299 soybean nationally,
but only 70/32 overlap the existing regional weather geography. The actual
practice-specific series has just 1–3 positive paired counties per crop-year
after 2019. Therefore a direct-practice recent holdout is not credible;
all-practice high-rainfed-share validation is a separate proxy estimand and
requires a consistent nationwide weather route. No 2020–2025 weather/yield
effect, welfare or SCC has been estimated. See
`US_2020_2025_NASS_HOLDOUT_SUPPORT_RESULTS_20260916.md`.

## September16 exact-corner global raw-versus-polynomial fidelity checked

The original EPIC-TAMU maize C360/N200/A0 baseline and uniform
T+3°C/W−50% simulations were compared with the published polynomial on a
fixed, physically comparable rainfed production subset. On the unchanged
all-source denominator, last-30 raw/polynomial contributions are −50.941/
−50.624 percentage points (81.200% comparable production); first-30 are
−57.835/−57.505 points (93.632% comparable). An independent vector-basis
reconstruction passed 87 checks. Missing raw cells, zero baselines and
negative polynomial yields remain excluded-but-accounted, not clipped or
reweighted. This is not precipitation-only, actual future climate, daily
distribution, money damage or SCC. See
`EPIC_RAW_GLOBAL_FIDELITY_RESULTS_20260916.md`.

## September16 original simulation global support independently audited

Fixed MapSPAM all-source rainfed maize production covers 490.057 million
tonnes. Original EPIC-TAMU baseline/stress simulations are complete together
over 83.285% of that fixed weight in the preregistered last-30 window, but
95.718% in the first-30 sensitivity. The 31st stored growing-season record
has a large missing-value increase, although the published protocol describes
30-year outputs; its cause and the authors' fitting window are unresolved.
The prior emulator `common_response` footprint (95.030%) is not raw-model
support. Independent slab traversal passed 543 checks and reconciled all 75
Morocco cells. No global damage or SCC follows from a coverage audit. See
`EPIC_RAW_GLOBAL_MASK_RESULTS_20260916.md`.

## September16 original simulation comparison reveals spatial-support gap

Both pinned EPIC-TAMU maize A0 source members are recovered and coordinate-
audited. A frozen75-cell Morocco comparison reads only selected yield series;
4,650 original values and6,450 independent checks pass. Eight cells (19.316%
of fixed baseline production weight) are missing in **both** raw simulation
states for all31 records; these exactly coincide with the eight cells where
the published polynomial predicts negative yield at the T+3/W−50% corner
and with the earlier projected-input flags. On the remaining67 cells, the
last-30-record raw versus polynomial supported contributions are −52.157
versus −47.511 percentage points on the unchanged full75-cell denominator.
This is a uniform-perturbation source-model fidelity test, not a Morocco
damage estimate, observational validation, rainfall-timing response or SCC.
The raw spatial mask mismatch must be audited beyond Morocco before any
global benchmark is qualified. See `EPIC_RAW_MOROCCO_COMPARISON_RESULTS_20260916.md`.

## September16 original baseline yield file accessible, not analyzed

The source baseline NetCDF member was reassembled and hash-pinned from60
individually verified small ranges, without downloading the2.7GB archive.
Header inspection confirms31 annual records and a compressed yield variable;
no yield value was read, fitted window inferred, or crop result changed. Full
archive MD5 remains unverified. See
`EPIC_RAW_BASELINE_MEMBER_RESULTS_20260916.md`.

## September16 original simulation transfer constraint

A3.917MB member-range request timed out at the source (504). A separately
capped4KiB request from the same pinned offset returned exact206 and HDF5
signature. A chunked route may be possible, but no full member or yield
array was acquired and no crop conclusion follows. Failed attempt retained;
see `EPIC_RAW_MEMBER_TRANSFER_STATUS_20260916.md`.

## September15 header index locates matched experimental source files

A capped128-header index locates C360/N200/A0 baseline and T+3/W−50%
simulation members without downloading their bodies or the2.7GB archive.
Six synthetic checks pass; exact range/tar safeguards apply to each request.
Index remains partial, source yields/time conventions uninspected and full
archive checksum unverified. No new yield, damage or SCC result. See
`GGCMI_TAR_HEADER_INDEX_RESULTS_20260915.md`.

## September15 original simulation access route verified

Official Table4 and exact archive metadata identify EPIC-TAMU maize outputs
at Zenodo2582349. A capped512-byte probe verifies tar-header range access,
offering a potential bounded-storage extraction route without downloading
the2.7GB archive. No yield member body, training-state comparison, refit,
crop-response validation, welfare or SCC. See
`GGCMI_RAW_OUTPUT_ACCESS_RESULTS_20260915.md`.

## September15 remediation assessment; no corrected benchmark

Source review distinguishes polynomial coefficient assets from raw GGCMI
simulation outputs advertised separately in the protocol's Table4. The exact
EPIC-TAMU output release/layout is not yet verified. Clipping, constrained
refit, raw-simulation validation and published alternatives are distinct
choices; none has been silently adopted. No new empirical result or SCC.
See `CROP_BENCHMARK_REMEDIATION_MEMO_20260915.md`.

## September15 invalid crop-model outcome traced, not corrected

Morocco's two calendar entries reproduce exactly from75 saved common-support
cells and published coefficients (600 corner comparisons;608 independent
checks). Eight cells yield negative future production despite inputs inside
the registered T/W application bounds. No arithmetic/join discrepancy was
found; the polynomial response remains physically unqualified for valuation.
No clipping, dropping, refit, empirical damage or SCC. See
`MOROCCO_NEGATIVE_CORNER_TRACE_RESULTS_20260915.md`.

## September15 welfare-input readiness and invalid benchmark flag

32 maize cases/3,360 country-case-regime rows reconcile to the resident
baseline ledger;3 tests and364 independent checks pass. Annual pulse-draw
and adaptation-cost inputs are absent from these summaries. Two Morocco
EPIC/IPSL/SSP585 rainfed entries imply nonpositive joint production and cannot
enter a log-supply mapping; this is a benchmark qualification failure, not
an estimated real crop loss. No clipping or monetization. See
`WELFARE_INPUT_READINESS_RESULTS_20260915.md`.

## September15 independent welfare design, not empirical results

The proposed fully anticipated benchmark now has an explicit mathematical
specification, paired surplus differences, two alternative yield-to-supply
mappings and within-market irrigation aggregation. It distinguishes a
precipitation contribution from total-agriculture replacement and retains
adaptation/coverage/attribution gaps. It is not adopted or calibrated and does
not replicate the unresolved published storage/surplus route. No new numerical
damage or SCC. See `FULLY_ANTICIPATED_WELFARE_SPECIFICATION_20260915.md`.

## September15 price convention resolved; welfare not calculated

Nine affected test groups validate a source-pinned GDP-wide price rebase:
central0.8357992263240843 and a2015 midpoint sensitivity. Only the price-basis
gate is now resolved. Source is a state-government reproduction of BEA's
March2022 series, not an exact archived2021 BEA file; pairwise GIVE constants
match. The FAOSTAT farm-gate/GDP price-concept approximation is disclosed.
No ledger conversion or empiricalmoney/SCC. Expectation, realized surplus and
adaptation-accounting gates remain closed. See
`PRICE_BASIS_REGISTRY_RESULTS_20260915.md`.

## September14 welfare scenario registry

Twenty-seven configuration identities now cover country/continent/global
markets, three published elasticity assumption pairs and fixed/trend/upper
adaptation cases. Three test groups pass. Empirical execution remains
programmatically disabled while expectation, surplus and adaptation
accounting gates are open. These are scenario labels, not estimates. See
`WELFARE_SCENARIO_REGISTRY_RESULTS_20260914.md`.

## September14 baseline value proxy ledger

A source-pinned150-country/231-regime ledger allocates complete1999--2001
FAOSTAT maize value to fixed MapSPAM rainfed/irrigated production shares while
retaining physical-response support gaps. Three synthetic tests and2,118
independent checks pass. The complete-value baseline is143.163billion constant
2014--2016USD;130.471billion (91.135%) lies on common response support under
this production-proportional proxy. Five codes remain explicitly unmapped to
FUND. This is baseline accounting, not regime-observed value, welfare damage,
USD2005, climate attribution or SCC. See
`WELFARE_BASELINE_LEDGER_RESULTS_20260914.md`.

## September8 annual-money engineering boundary

Seven Python contract test groups and27 native-Mimi assertions passed. The
actual, source-pinned GIVE damage aggregator preserves artificial money signs,
applies the expected billion-to-dollar scale, and does not multiply this money
by GDP again. No full GIVE run, empirical valuation or SCC estimate. Separate
cross-language transport also passed14Julia assertions plus Python overwrite
and axis-rejection checks. See
`MONETARY_ADAPTER_ENGINEERING_RESULTS_20260908.md` for scope and failed/passing
receipts. Existing fractional-loss components remain unchanged.

September14 continuation: the full archived GIVE ordinary-path wiring control
also passed20 assertions. It preserves nonagricultural topology and an altered
sector flag, leaves the caller model unchanged, maps artificial regional money
to the expected global/domestic aggregates, and leaves mortality/energy outputs
unchanged in a zero-money rerun. This completes the synthetic software boundary,
not empirical welfare, climate attribution, discounting or SCC calculation.

## September8 preliminary package updated

The brief now leads with a current, plain-language synthesis. A new separate
291-claim source-bound extension includes all 32 physical benchmark cases,
geographic illustrations, coverage and selection results. Four traceability
tests pass. The earlier 50-claim historical and 148-claim SPEI registries remain
unchanged. See `PRELIMINARY_EVIDENCE_PACKAGE_20260908.md`.

The final journal-linked Liu proof was retrieved after diagnosing its larger
size; it does not resolve the model-specific feature contract. All identified
journal-linked alternatives have now been inspected for this question. The
author query remains unsent, and the annual model remains disabled. This is a
source-resolution constraint, not proof that no other implementation exists.

The subsequent already-monetized annual input contract and source-pinned
adapter test are now implemented, as recorded above. No empirical monetary
damages have been created.

## September8 baseline economic-input coverage complete

All-three-year FAOSTAT value coverage is 97.898% of common rainfed production
and 98.736% of common irrigated production. Belgium/Luxembourg have two years;
missing and unmapped categories remain separate, with no published zeros in
this footprint. Independent 2,418 checks pass, maximum scaled error 3.66e-16.
This is physical-production coverage of national value inputs, not a value
weight or monetary damage. No imputation or model promotion. Report:
`EPIC_CARAIB_ECONOMIC_INPUT_RESULTS_20260908.md`.
The subsequent physical-response selection diagnostic is also complete:
32 cases, 1,984 independent checks, maximum scaled error 5.00e-16. The
complete-value-country restriction changes rainfed precipitation responses by
−0.0357 to +0.0766 percentage points, with no monetary weights or welfare
interpretation. See `ECONOMIC_COVERAGE_RESPONSE_SELECTION_RESULTS_20260908.md`.

## September8 geographic comparison complete; welfare source search advancing

The new EPIC/CARAIB country comparison reuses 39,289 validated country-cell
quantity records and produces 3,360 country/case responses. Independent 52,074
checks pass (max2.17e−15). Prespecified GFDL126 EPIC rainfall contributions from
the United States and China are +2.315/+0.815 global percentage points; the
global total is +3.462%. In GFDL585 the U.S. net +0.026 points masks
+0.667/−0.641 across-cell contributions. Country/source coverage exclusions
remain explicit. No empirical damages, welfare or SCC is inferred.
Report: `GGCMI_EPIC_CARAIB_GEOGRAPHIC_RESULTS_20260908.md`.

Next work moves to the missing economic link rather than adding more crop-model
benchmarks. The pinned Hultgren public replication tree now has a complete
1,039-entry/11-page metadata index. No filenames match explicit welfare/market/
monetization/elasticity/license terms. This is not evidence of nonpublication.
The subsequent 108-unique-file source index and four candidate-context reviews
are complete. They did not locate the monetary-market implementation. This is
not a nonpublication claim. Read `HULTGREN_MONETIZATION_SEARCH_RESULTS_20260908.md`.
An author-clarification draft remains unsent. Next executable local step:
`EPIC_CARAIB_ECONOMIC_INPUT_COVERAGE_STAGE_20260908.md`; no welfare weights yet.

## September8 global EPIC/CARAIB comparison and external weighting complete

Supersedes the older next-stage notes below. Four EPIC global cases, independent
spatial transfer checks, exact common-area comparison and identical external
production weighting are complete. No analysis worker remains active at this
checkpoint. Full results: `GGCMI_EPIC_CARAIB_GLOBAL_RESULTS_20260908.md`.
On identical external weights, rainfall contributions in the four harvest-year
cases span −0.098% to +3.462% for EPIC and −0.024% to +0.339% for CARAIB.
Joint warming-plus-rainfall responses are negative in all eight model/case rows.
Common external production coverage is 95.03% rainfed / 85.67% irrigated.
Independent audits pass 762 common-area and 2,648 external-weight checks.
These conditional physical-production benchmarks do not validate empirical
response, daily extremes, adaptation, economic welfare or SCC.

Next justified calculation: geographic decomposition using the already
source-validated country/cell MapSPAM ledger, with the new common support.
Do not rerun raw source aggregation or older CARAIB/JULES geography.

## September8 same-forcing spatial benchmark and own global support complete

EPIC-TAMU sparse author/raw/corner checks pass. On82common positive-baseline
rainfed nodes, hypothetical−10%rain gives median−9.66%EPIC-TAMU versus−1.11%
CARAIB at unchangedT. No global inference. Own-model global coverage also
passes258797ledger rows,58429raw regime/cells and14811author-baseline signs.
Supported2000area94.03%rainfed/85.71%irrigated atN200; source/input coverage
is not response validation. Both result notes and manuscript/SI are updated.
Next: `GGCMI_EPIC_TAMU_GLOBAL_CLIMATE_STAGE_20260908.md`, separate source-
domain evaluator qualification before existing-climate coupling. No new
download, model-primary promotion, agricultural welfare or SCC claim.

## September8 EPIC-TAMU parameters and fixed-point benchmark complete

Source MD5/SHA256, exact34/19interface,24author-reference evaluations, six
derivative checks and30record/sixcorner comparison audit pass. At one fixed
point, hypothetical10%lessrain gives−18.85%EPIC-TAMU versus−1.17%CARAIB rainfed
yield, relative to each model's baseline. This is a model benchmark, not
observational evidence, global damage or SCC. Common nominal weather source
does not remove nitrogen/model differences. Details:
`GGCMI_EPIC_TAMU_POINT_RESULTS_20260908.md`. Acquisition used two bounded
chunks and<32MiBRSS, no duplicate parameter file or raw climate hydration.
Next registered step: `GGCMI_EPIC_TAMU_SPARSE_STAGE_20260908.md`.

## September8 fixed preplant comparison and moisture synthesis complete

Preplant historical diagnostics pass64effective fit/covariance records and
92contrasts, retaining the two original numerical-verifier failures and their
exact-value precision repairs. Predictive diagnostics pass170fits and all50
available maize intervals; every interval includes zero. Soybean retains
unsupported country-bootstrap coverage and all17models exceed zero-change
error. Positive historical preplant associations do not establish forecasting,
climate damage or SCC. See `SPEI_PREPLANT_RESULTS_20260908.md` and
`GLOBAL_MOISTURE_EVIDENCE_SYNTHESIS_20260908.md`. Current prespecified SPEI
window sensitivities are done, with no model promotion. Next bounded source-
qualified crop-model comparison is specified in
`GGCMI_SAME_FORCING_BENCHMARK_STAGE_20260908.md`; acquisition not started.

## September 8 month-end prediction sensitivity complete

All170fits and independent audits passed. Maize:48423testpairs/99countries,
56conditional intervals, six excluding zero only for comparisons within/between
SPEI specifications. Every drought-versus-quantity interval includes zero.
Soybean:24789testpairs/21countries; fixed-bootstrap support remains insufficient
and all17estimated models have higher error than zero-change. No scale,
allocation, production-model or SCC promotion. Full table/all nonzero intervals:
`SPEI_MONTH_END_PREDICTION_RESULTS_20260908.md`.
Next: fixed preplant90 diagnostics under
`SPEI_PREPLANT_DIAGNOSTIC_STAGE_20260908.md`, not implemented or run yet.

## September 8 prediction and full SPEI evidence registry complete

Subsequent month-end historical sensitivity also passed: 64 fit/covariance
records, 68 contrasts, exact primary-loader parity and four synthetic tests.
Maize associations are similar across allocation conventions. Soybean's
6-month month-end result depends on clustering, not a robust new discovery.
See `SPEI_MONTH_END_ASSOCIATION_RESULTS_20260908.md`. Next executable stage:
`SPEI_MONTH_END_PREDICTION_STAGE_20260908.md`, implementation still needed.

The primary SPEI country-separated prediction comparison and independent audit
pass. All 26 maize conditional RMSE contrast intervals include zero. Soybean's
singleton-country scoring fold prevents the prescribed bootstrap; all eleven
estimated models perform worse than zero-change on both aggregate scores.
Positive associations do not establish incremental prediction gains. No model
promotion or causal/future/welfare/SCC result. Full results:
`SPEI_COUNTRY_PREDICTION_RESULTS_20260908.md`. The separate 148-claim SPEI
registry and all 70 available intervals pass exact source validation.
This supersedes the prediction-next statement in the older section below.

## September8 first exact-support global SPEI–yield associations

Fortyfit/covariance records and44contrasts completed and independently verified
on352,288maize/157,003soybean historical differences. Seasonal SPEI+1unit
associations for maize are+1.668%,+2.127%,+2.510%at1/3/6months, with conditional
country-proxy intervals excluding zero. Soybean seasonal intervals all include
zero. These are competing moisture specifications with common heat and country-
year controls, not isolated precipitation effects or evidence of predictive
superiority. No scale/model promotion, future yield projection, welfare or SCC.
`SPEI_HISTORICAL_ASSOCIATION_RESULTS_20260908.md`.
All master support/source-loss audits passed; see
`SPEI_MASTER_SUPPORT_RESULTS_20260908.md`. Next: the unchanged country-separated
terminal prediction test under `SPEI_COUNTRY_PREDICTION_STAGE_20260908.md`.

## September8 global crop-window and lossless wide SPEI inputs complete

All61global crop-window blocks and both final manifest audits pass. The wide
layout preserves1,825,770candidate crop-years/696,835observed flags with
109,546,200exact inverse field comparisons. Fixed calendars/positive-regime
weights, source exclusions and CDFclips are retained. This supersedes older
statements below that global crop-window construction remains unfinished.
Exact heat/outcome/common-support preparation is now the active data stage.
No SPEI-yield effect, predictive advantage, climate damage or SCC is claimed.
`SPEI_GLOBAL_CROP_FEATURE_RESULTS_20260908.md`.

## September8 historical crop-footprint SPEI candidates complete

Memory-safe day-wise preprocessing completed39years/468months for31,208frozen
native maize/soy cells. Candidate SPEI1/3/6 now constructed in61bounded blocks:
all1,123,488 distribution fits valid; expected leading missingness only; CDF
clips retained. All198reference cells reconcile,1,425,600array comparisons
pass with zero SPEI difference. The60continuation fit/validation jobs took
148.82s total and used at most159.91MiB sampled RSS perjob. No new yield effect,
predictor promotion, climate damage or SCC result is claimed. Crop-window
allocation and final comparative estimation remain unfinished.
`SPEI_GLOBAL_CANDIDATE_INDEX_RESULTS_20260908.md`.

## September8 SPEI calendar and crop-window pipeline verified

64-cell construction and7,200 anchor comparisons pass. The complete historical
candidate footprint (1,825,770crop-years) has source-month/calendar coverage
audited without reading yield values. Within the test tile, all132,588 complete
regime feature rows pass independent daily-expansion checks; all67,200combined
feature rows reconcile. Preplant1982 and numerical clipping remain explicit.
Every new construction/validation job used less than317MiB sampled RSS.
This is engineering progress only: no global production SPEI, fitted drought
response, predictive promotion, causal damage or SCC result.
`SPEI_CALENDAR_AND_TILE_RESULTS_20260908.md`.

## September8 spatial climate cancellation and source-compatibility review

All16 monthly ledgers: positive/negative area shares and pooled rainfall
contributions independently verified with189,944 checks. GFDL585 rainfed
harvest-year net+0.051% comprises+2.801/−2.750pp contributions;45.946% of area
has less seasonal rainfall. Across4cases, annual/seasonal signs differ on
19.932–22.165% of area. TwoGCM seasonal signs disagree on41.604% (126) and
46.902% (585). Climate-only descriptive shares, not probabilities/damages.
`MONTHLY_SPATIAL_CANCELLATION_RESULTS_20260908.md`.

OSCAR beta forcings acquired with checksums;292beta regions cannot silently
replace311current regions. Units/reference/member gaps block this optional
current-model projection route. Source checks, Methods SI and an UNSENT author
inquiry are saved. `OSCAR_FORCING_FEASIBILITY_RESULTS_20260908.md`.

## September 8 global monthly climate quantity/pattern distinction

New climate-only results cover 99.309% of mapped rainfed and 99.781% of irrigated
maize area without crop-response-domain filtering. Rainfed pooled seasonal
amount changes: +2.794/+0.051/+2.161/+2.008% for GFDL126/585, IPSL126/585;
area-mean monthly redistribution indices 0.0451/0.0498/0.0361/0.0441. Thus the
near-zero pooled amount case does not have an unchanged monthly distribution.
Five synthetic tests and 13,688 independent numerical checks pass. Not daily
drought, identified forced effects, crop losses, welfare or SCC. No distribution
predictor is promoted. `MONTHLY_PRECIPITATION_PATTERN_RESULTS_20260908.md`.

## September 8 OSCAR-crop engineering contract

133,356 arithmetic comparisons and 389,376 independent support/count checks
pass; 17,795 source parameter combinations qualified before extreme flags.
Only audited source lambdas ran, not the upstream simulator. No climate scenario
or yield/SCC projection followed. `OSCAR_FUNCTION_CONTRACT_RESULTS_20260908.md`.

## September 8 OSCAR-crop parameter interface prepared

Nine small source-hashed parameter files (about 4.37 MB) and the frozen source
interface are acquired; read-only inspection succeeds in the existing environment.
No upstream code or yield predictions were run. Exact baseline/unit and
nonpositive-response discrepancies are documented in
`OSCAR_CROP_ASSET_REVIEW_20260908.md`. This advances an already selected aggregate
benchmark; it does not solve daily drought, causal attribution or SCC linkage.

## September 8 geographic benchmark decomposition

Fixed-source production was allocated by source country within half-degree
cells without choosing a single country for border cells. All 148 rainfed/83
irrigated source-country coverage records and 3,440 supported case summaries
are retained. Independent source/corner accounting passes 186,113 checks.
In the first prespecified GFDL126 harvest-year case, the U.S. contributes
+0.213pp to CARAIB's +0.333% global rainfed P result and +5.943pp to JULES's
+9.456%; China contributes +0.085/+2.579pp. These are model-configuration
production sensitivities, not NASS estimates or country damages. Lower
coverage (e.g., Indonesia 77.29%) remains explicit. No welfare/SCC promotion.
`MAPSPAM_GEOGRAPHIC_DIAGNOSTIC_RESULTS_20260908.md`.

## September 8 annual distribution-aware model: not prediction-ready

The published Liu annual CARAIB model exists and has been safely inspected
without unpickling. Its54 actual features disagree with generic55-column
documentation; crop-month window and exact ordering remain unresolved. Do not
guess/drop columns. The419MB serialized model was not retained or loaded;
metadata inspection stayed near122MiB peak. No new ML was trained or claimed.
`LIU_ANNUAL_EMULATOR_ASSET_REVIEW_20260908.md`. Public code/schema clarification
is needed for this optional annual track; other work continues.

## September 8 external-production weighting sensitivity

Identical MapSPAM production weights preserve the CARAIB/JULES disagreement:
rainfed precipitation contributions range−0.028% to+0.333% in CARAIB and+0.346%
to+9.456% in JULES across the fixed cases. This is NOT independent observed-yield
validation: MapSPAM is modeled disaggregation. Common source-production coverage
is98.018% rainfed/95.519% irrigated, with exclusions unrenormalized.164,052
source-grid and676 independent weighted-result checks pass; no downloads.
`MAPSPAM_GLOBAL_WEIGHT_DIAGNOSTIC_RESULTS_20260908.md`.
Important source qualification: crop-model configurations also differ in
historical forcing; do not call their contrast purely structural uncertainty.
`CROP_MODEL_BASELINE_FORCING_QUALIFICATION_20260908.md`. No economic promotion.

## September 8 two-crop-model global benchmark complete

The independent JULES branch now has all four actual monthly climate cases,
not just sparse perturbations. On the same rainfed cells (97.039% of mapped
hectares), precipitation contributions are +4.181%, +0.052%, +2.261%, +2.351%
for JULES versus CARAIB +0.179%, −0.048%, +0.116%, +0.148% (GFDL126/585,
IPSL126/585, harvest-year). Denominators are explicitly model-specific positive
baseline production, NOT observed production. Regional gains/losses offset;
joint warming+precipitation responses are negative in all eight cases.
These are structural quantity-at-mean-climate benchmarks, not empirical global
losses, daily drought/timing effects or SCC. No model selected on magnitude.
See `GGCMI_TWO_MODEL_GLOBAL_RESULTS_20260908.md`. JULES additional checks:
15,288 author-R corners,528 aggregate checks,18,560 independent climate checks;
peak370.14MiB. Empirical weighting and annual nonlinear sensitivity remain next.

## September 8 independent crop-model qualification

JULES source acquisition now succeeds through the same public record's file
route; original API failures were not a data-permission blocker. Its registered
common-node sparse benchmark shows substantially stronger rainfall responses
than CARAIB: median −17.06% versus −1.03% for hypothetical −10% rain at +2 °C.
These are NOT global losses. All 1,824 author-R and 936 support checks pass.
This specifically cautions against treating the CARAIB global precipitation
term below as general evidence that agricultural precipitation damages are small.
See `GGCMI_JULES_SPARSE_COMPARISON_RESULTS_20260908.md`.

## September 8 first global climate-to-maize process benchmark

All four raw-CMIP6/CARAIB cases and both calendar conventions are now coupled
and independently checked. On a fixed common support covering 97.05% of mapped
rainfed maize hectares, harvest-year precipitation order-average contributions
are +0.179%, −0.048%, +0.116%, +0.148% of supported modeled baseline production
(GFDL126/585, IPSL126/585). Temperature contributions are −6.37% to −12.05%.
These are quantity-focused, fixed-C360/A0 responses at mean climate, NOT observed
global losses, a timing/drought result, welfare or SCC. Opposite SSP585 signs,
spatial cancellation, excluded hectares and raw negative yields are retained.
21,280 author-R, 576 aggregate and 18,080 independent climate-transfer checks
pass; peak 411 MiB. `GGCMI_GLOBAL_MONTHLY_BENCHMARK_RESULTS_20260908.md`.

## September 8 cross-year calendar and global monthly access

The source-faithful calendar interface now has explicit harvest-year support:
six tests, 1,248 exact author-R weights and 80 area reconciliations pass.
22.6913% of mapped rainfed maize hectares (6.4989% irrigated) need preceding-year
weather in the primary exposure map. These are calendar shares, not damages.
`GGCMI_CALENDAR_YEAR_ALIGNMENT_RESULTS_20260908.md` documents the result.

Published PEEPS already supports monthly pattern scaling; no novelty claim for
that feature. A bounded public-cloud route now has twelve verified raw-CMIP6
monthly stores and their coordinate axes, with all required baseline/future
months. Source-specific licensing and calendars are retained. These are not
ISIMIP bias-adjusted data. The subsequent first actual global monthly climate
reduction (IPSL historical precipitation) has completed at 201.19 MiB peak,
retaining 5.92 MB and passing 240 independent scalar checks. Remaining stores
were chained serially and are now ALL COMPLETE: twelve global monthly products,
78.79 MiB derived arrays retained, 375.61 MiB maximum peak RSS. All sixteen source
MD5 checks and 2,160 independent saved-array Decimal checks pass. No global
crop-response calculation is implied. `PANGEO_MONTHLY_REDUCTION_RESULTS_20260908.md`.
See `PUBLISHED_MONTHLY_CLIMATE_ROUTE_20260908.md`. No user decision needed.

## September 8 global crop-area coverage, not global damages

Existing MIRCA-OS v2 rasters are now joined to the CARAIB benchmark globally.
Year-2000 supported positive-baseline/calendar/coefficient coverage is 98.7764%
of mapped rainfed maize area and 99.2437% of irrigated area; all excluded
denominators and four alternative vintages are retained. 258,797 ledger rows,
10,348 author-R baseline/sign checks and 100 independent area aggregates pass.
No downloads; 260.36 MiB peak. This advances exposure support only, NOT response
validation, actual global climate coupling, damages or SCC. Details:
`GGCMI_CROP_AREA_SUPPORT_RESULTS_20260908.md`.

The second JULES download attempt returned HTTP504 with no payload. Stop
immediate identical retries; this is a source-service constraint, not missing
download permission. Generalized model-selector code is prepared but JULES
has not been evaluated. Existing-data research continues independently.

## September 8 sparse spatial process-model diagnostic

The fixed 468-node lattice gives 111 rainfed/115 irrigated eligible CARAIB
maize nodes; 15 in each regime have nonpositive baseline yields. Hypothetical
±10% rainfall/+2 °C responses show spatial heterogeneity and some negative
raw corners or very large relative changes; none are clipped. These are not
actual future climate projections or global damages. All 1,808 author-R
corner checks, 936 raw eligibility rereads and 112 summary checks pass.
No downloads; 59.22 MiB sampled peak. See `GGCMI_SPATIAL_BENCHMARK_RESULTS_20260908.md`.
Harvested-area support and independent-model/empirical validation remain open.

## September 8 temperature–precipitation interaction accounting

All four fixed climate cases × two calendars × two irrigation regimes now
have jointly evaluated temperature/rainfall corners. Phase 2 rainfed joint
T+P responses are -6.5488%, -12.8555%, -8.1074% and -10.8043% (GFDL126/585,
IPSL126/585); order-averaged rainfall contributions are +1.1516%, -0.9528%,
+0.5569% and +0.7600%. These are SINGLE-POINT CARAIB structural responses,
not global/observed impacts or SCC. CO2 remains fixed; daily timing is excluded.
Five unit tests, 64 author-R comparisons, prior W-only parity and 256 independent
accounting checks pass. No downloads or clipping. See
`GGCMI_POINT_INTERACTION_RESULTS_20260908.md`. Not in frozen 50-claim registry.

## September 8 two-model/two-scenario point comparison

The registered matrix is complete: quantity-only rainfed contributions at
the single fixed CARAIB maize point are GFDL SSP126 +1.1436%, GFDL SSP585
-0.9911%, IPSL SSP126 +0.5580%, IPSL SSP585 +0.7748%. Opposite signs under
SSP585 are retained. These are structural point benchmarks, not net climate
impacts, global estimates or SCC. A 5.37MB point archive replaces additional
global-file downloads; the chained calculation used 166.47MiB sampled RSS.
7,306 exact sentinel values, 3,600 raw monthly comparisons, all period
aggregates and author-R arithmetic pass. Full limits/results:
`GGCMI_POINT_CLIMATE_MATRIX_RESULTS_20260908.md`. Not in frozen50claimregistry.

## September 8 actual climate-to-crop point coupling

Actual climate coupling is complete at one fixed point: GFDL SSP126 gives
+11.2384% calendar-weighted mean rainfall (2031–2060 versus own-model
1981–2010), implying a +1.14358% uniform-amount-only CARAIB rainfed maize
contribution with temperature/CO2 fixed. This is a local process-model
benchmark, NOT an observed effect, net climate impact, global damage or SCC.
It excludes altered rainfall timing. No downloads; 136.31 MiB sampled RSS.
Independent raw-month/aggregate checks and author-R arithmetic pass.
See `GGCMI_CLIMATE_POINT_ALIGNMENT_RESULTS_20260908.md`. These later point
results are documented separately, not added to the frozen 50-claim package.

## September 8 author-bound process-model point benchmark

The earlier CARAIB ordering blocker is resolved by the recovered Müller
author code, not by inference. Nine unit tests and 384 additional synthetic
reference comparisons pass. One preselected real CARAIB maize A0 point now
evaluates correctly: hypothetical uniform -10% precipitation gives -1.1664%
rainfed yield relative to that model's baseline; +10% gives +1.0264%.
This is NOT a climate projection, observed agricultural effect, global
estimate, irrigation treatment effect or SCC. Author/R arithmetic and
derivative checks pass. See `GGCMI_CARAIB_POINT_RESULTS_20260908.md`.
Immediately acquired the matching small Phase 2 calendar archive and checked
it against resident Phase 3 calendars; their planting dates differ even at
the fixed point. Real climate-to-model coupling still requires explicit
calendar/baseline alignment. Prior engineering status below is historical.

## September 8 published-model interface validation

Published osiris reference arithmetic is now reproduced in an isolated
34-term rainfed/19-term irrigated evaluator: six synthetic unit tests and
660 Python/base-R comparisons pass. These are engineering results only.
The resident CARAIB 20/10 parameter layout remains explicitly unsupported;
no actual process-model yield or SCC was calculated. Raw HDF5 dimensions
are resolved, baseline precipitation multiplier is source-bound to one,
and the precise remaining issue is no-nitrogen coefficient ordering.
See `GGCMI_REFERENCE_INTERFACE_PROTOCOL_20260908.md` and the updated
`PUBLISHED_CROP_EMULATOR_BENCHMARK_20260908.md`. Public author-archive
timeouts/rate limiting are recorded; no repeat-download approval is needed.

## September 8 whole-country validation supplement

Country-held-out terminal prediction is complete: fifty numerical fits,
nine supported crop-fold score cells, one unsupported soybean fold (one
country/three pairs). Maize quantity's small improvement has descriptive
intervals crossing zero; soybean quantity is worse than zero change on the
supported folds. Independent aggregate arithmetic and country-separation
checks pass. See `GLOBAL_COUNTRY_HELDOUT_RESULTS_20260908.md`. The next
distinct benchmark uses published crop emulators, not another custom climate
emulator or automatic promotion of the existing global regression.

## September 8 direct support and traceable preliminary package

The direct future joint-weather support diagnostic and independent numerical
check are complete; no response was fitted on the very small common subset.
Source-linked package `PRELIMINARY_EVIDENCE_PACKAGE_20260908.md` now documents
50 selected claims from six saved JSON sources, with exact paths/hashes,
cohorts, intervals where available and scientific limitations. Global added
heat-day controls retain the maize association and uncertain soybean result.
This package is local, not a new GitHub publication or empirical SCC estimate.

## September 8 subsequent predictive qualification

Source-matched blocked prediction, naive-baseline audit, temporal component
decomposition and separately refitted constant/linear-time sensitivities are
complete. Original264/new528 predictive fits pass numerical gates; ten small
geographic folds remain unsupported. Simpler time control improves corn
forecasting, but soybean and timing transfer remain mixed. These are repeated-
validation development diagnostics, NOT causal response or SCC promotion.
See `US_PREDICTIVE_TREND_SENSITIVITY_RESULTS_20260908.md` and the active checkpoint.

## Current September 8 update (supersedes historical chronology below)

Regional paired climate inputs/comparisons COMPLETE: 54 validated daily
cutouts; 6,092 corn/4,308 soy county-years; 345/252 counties. Source-matched
historical yield diagnostic COMPLETE: 32 registered fits, four synthetic tests
and all 32 numerical replications passed. See
`US_SOURCE_MATCHED_RESPONSE_RESULTS_20260908.md` and its prepared local aggregate.
These remain exploratory associations, not independently validated response
functions, counterclim yield impacts, global damages or SCC. Quantity stays
primary; in-sample timing fit cannot reopen promotion. Earlier 'missing Tmax'
and active-job descriptions below are historical, not current blockers.

Updated: 2026-09-07. This file records completed computational milestones; it
does not report final response estimates or SCC values.

Latest substantive continuation:18future fixed-MIRCA nonlinear climate-basis
tables constructed,208,404rows across maize/soybean and a balanced three-ESM,
three-scenario pilot. Six new synthetic tests pass. The ensuing historical
range comparison shows substantial stage-temperature extrapolation and
missing historical coverage, not projected crop losses. Both jobs completed
below510MiB sampled RSS with less than19MiB derived-data storage. See
`FUTURE_WEIGHTED_PRECIPITATION_RESULTS_20260907.md`. No response or SCC gate
is promoted; aligned future Tmax remains missing.

Latest data-access milestone: the official ISIMIP server completed one daily
Tmax latitude-band cutout, with12,891,438bytes reported by HEAD instead of the
2,064,668,768byte global parent. No climate bytes were downloaded locally.
Exact-coordinate calendar handling now reproduces synthetic full-grid seasonal
and stage heat outputs exactly; two tests passed below214MiB sampled RSS.
Real content/feature validation awaits a one-file storage exception. See
`LOW_STORAGE_HEAT_SUBSET_PILOT_20260907.md`.

Latest economic implementation: six published alternative point-estimate
elasticity pairs evaluated over36hypothetical states; three synthetic tests
and all rounding, market-clearing, surplus and derivative checks pass after
a caught wrapper correction. This is normalized sensitivity only, not an
empirical welfare calibration or climate damage estimate. See
`WELFARE_NORMALIZED_SENSITIVITY_RESULTS_20260907.md`.

Latest U.S. milestone: supported-range rainfall curves reproduce all 24 saved
fits exactly; 12 paired irrigation-practice difference fits account for shared
county/year errors. Non-irrigated dry-weather associations are substantially
larger in these selected counties, but marginal within-county support is
limited and irrigation effects remain noncausal. Seven new synthetic tests
pass. See `us_county_validation/US_RAINFALL_CURVE_AND_IRRIGATION_RESULTS_20260907.md`.

Latest climate milestone: 60 direct five-ESM scenario/period/subset comparisons
completed on the retained two-latitude maize-calendar pilot. Late-century
SSP5-8.5 minus SSP1-2.6 lengthens band-average maximum dry spells in all five
models, while total-rainfall differences disagree in sign. No global coverage,
yield impact or SCC is implied. See `CLIMATE_SCENARIO_CONTRAST_RESULTS_20260907.md`.

The immediate follow-up added 252 longer-period (2032–2059) comparisons across
six crop-season definitions and both calendars, with the incomplete ESM matrix
explicit. All 60,368 overlapping maize crop-year records agree exactly with the
short assembly. Stage mean temperatures exist; aligned future Tmax integrals
are missing from the consumed products. See
`CLIMATE_CONTIGUOUS_CONTRAST_RESULTS_20260907.md`. Climate-to-yield and SCC
requirements are not bypassed.

Latest sensitivity: country-year controls now estimated on identical mapped
support, 352,301 maize and 157,003 soybean pairs. The soybean quantity
association attenuates to near zero; maize stays positive but smaller.
All 16 fits and two covariance variants pass computational checks, without
causal/predictive/SCC promotion. See `GLOBAL_COUNTRY_CONTROL_RESULTS_20260907.md`.

New historical association milestone: 16 global maize/soy training-period
fits completed, each with 10- and 20-degree cluster-covariance variants.
All original training counts and current implementation hashes verify.
Soybean quantity/drought intervals include zero with annual intercepts and
20-degree blocks; no production response is promoted. See
`GLOBAL_HISTORICAL_ASSOCIATION_RESULTS_20260907.md`. The next independent
economic-link task is specified in
`PUBLISHED_WELFARE_ROUTE_ASSESSMENT_20260907.md`; SCC remains unavailable.

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
| Continuous-panel geographic/source-cluster audit | Five outcome-blind folds exclude each held-out 10-degree source block from training while preserving the 404,671/57,767 maize and 166,870/26,004 soybean temporal train/test support. Pooled quantity-minus-controls RMSE is -0.001040 [-0.002109, +0.000135] for maize and -0.000950 [-0.002301, +0.000535] for soybean; soybean distribution-minus-quantity is -0.001012 [-0.002518, +0.000734]. All cross zero. Soybean seasonal/stage scPDSI minus quantity is +0.002253 [+0.001349, +0.003119] and +0.001869 [+0.000235, +0.003278]. The 5,000-draw paired block bootstrap spans 123/55 terminal source blocks and reproduces byte-for-byte under a 377 MiB peak sampled RSS. | Exploratory retrospective prediction and descriptive source-cluster uncertainty only. Fits are fixed, grid-year pairs are equally weighted, block resampling does not define a random population or resolve all spatial/GDHY dependence, and no significance or model-promotion claim is permitted. Coefficients, causal response, future projection, FAIR, damage, welfare, and SCC use remain closed. |
| MIRCA-OS v2 irrigation weights | The 284,005,995-byte annual harvested-area archive is MD5/SHA-512 verified; 40 publisher-supplied 0.5° GeoTIFFs for four crops and five vintages pass grid, finiteness, nonnegativity, uniqueness, and unit-share gates. Fixed-2000 maize and soybean weights cover 97.79% and 97.99% of observed-yield cells in the existing 1982--89 panels. | Independent exposure-weight input only. Exact maize/soybean mappings are eligible for allocation; annual rice/wheat maps remain blocked from season-specific outcomes. No response or SCC input. |
| MIRCA rice-season source gate | The 1,537,240,142-byte official monthly archive is object-identity/SHA-512 pinned and all 30 Rice1--Rice3 filenames exist. Metadata pass 21/30: all nine 2005--2015 rainfed files declare year 2020 and are blocked. The six 2000 files pass full input checks, but their maximum-over-month reconstruction exceeds annual Rice by 64,247.23 irrigated ha and 5,302.04 rainfed ha, so both reconciliations fail and no table is emitted. | Failed source-consistency gate only; rice weights remain blocked pending publisher clarification/correction, and neither discrepancy is relaxed or converted into an effect estimate. |
| Rainfed/irrigated outcome-allocation gate | Synthetic failure modes plus real fixed-2000 maize/soybean source/coverage allocations pass. The one-outcome tables retain 117,679/120,325 maize and 47,922/48,900 soybean observations; 2,646 and 978 unmatched outcomes are explicitly excluded without infill or renormalization. | The legacy tables weighted primitive weather before constructing nonlinear terms, so they are not valid response inputs. Only their source, support, exclusion, and one-row-per-outcome audits stand. Production must construct every nonlinear regime basis before area weighting. |
| U.S. county outcome, irrigation, and historical-weather gate | The key-safe Quick Stats fallback retained 7,253 real-FIPS 2018--2022 all-practice corn county-years. The direct-practice screen retains 7,079 corn, 4,845 soybean, and 9,672 all-classes-wheat crop-county-year pairs, but only regional support. All 468 monthly 1981--2019 nClimGrid objects (27,857,685,556 bytes), 419 eligible corn/soy county weights, and 39 harvest-year partitions pass identity/content/schema/calendar/coverage gates. Exact assembly and recomputation produce 23,722 paired-practice corn/soy rows (SHA-256 `205a94ae...c46d7`) and 20,228 common direct-weather/PDSI consecutive-year changes. After validation, the 25.944-GiB reproducible raw grid cache was evicted on 21 September 2026; the complete URL/HTTP/checksum receipt, official daily county-average source, derived panels, and student-share file remain. A second isolated all-practice smoke validates Acadia Parish, Louisiana (22001) in 2019: 119 polygon/grid weights, five monthly weather objects, and one soybean crop-county-year feature row. | Input, construction, and common-support evidence only. Direct-practice support remains regional, the Louisiana result is one engineering row rather than national validation, all-wheat class weights are unresolved, eight historical-boundary cases need sensitivity treatment, and a predictive comparison cannot supply a causal response. No global transfer, damage, or SCC input is created. |
| U.S. all-practice national county-weight expansion | The registered all-county launcher validates and resumes 932 of 2,628 isolated county-weight receipts, then fails closed at Trigg County, Kentucky (21221). Exact recomputation gives full geometric grid coverage but only 0.907267979 weather-valid area relative to declared land, below the fixed 0.95 gate; 209,051,009 m2 of polygon intersection is masked. The same 77 valid cells and area terms recur exactly in January 1981, July 2000, and January 2019, and separate `prcp`, `tavg`, `tmin`, and `tmax` masks reproduce that exact result. Sixteen masked whole-cell intersections total 2.030 times declared county water; even assigning all water to them leaves at least 106,051,904 m2 beyond declared water. A hash-bound scan revalidates all 932 completed receipts and weight hashes: 60 have positive masked area, the minimum completed land-relative ratio is 0.960832366, only one is below 0.97, and seven are below 1.0. | Reproducible structural-coverage blocker only. Completed receipts are 35.46% of registered counties across 16 states, but reflect FIPS-ordered execution plus earlier smokes and are not representative. Trigg is below every completed ratio, yet the threshold is unchanged, no Trigg partition is written, and no partial national feature panel, response, damage, or SCC input is authorized. Resolve the common cell mask against fractional land/water geometry and preregister any corrected denominator, exclusion, or sensitivity rule before resuming. |
| U.S. corn/soy competing-moisture predictive diagnostic | On 20,228 exact-support consecutive-year changes, distribution fails the frozen uniform eligible-state gate for irrigated corn (1/5 states) and non-irrigated corn (4/5; South Dakota reverses), but passes for irrigated and non-irrigated soybean (3/3 each). Non-irrigated corn PDSI is the most stable drought competitor: seasonal and stage PDSI beat quantity-only in all five eligible states and in terminal/extreme tests. Non-irrigated soybean distribution also improves quantity-only in every eligible state, terminal, and extreme test; irrigated-soy distribution reverses in the terminal test. A clean-room raw-level QR audit reproduces all 120 metrics within `2.00e-15` and every discrete gate exactly. A separate hash-bound 5,000-draw county bootstrap exactly reconstructs all fits and reports 62 conditional RMSE/MAE comparisons; the tracked aggregate receipt SHA-256 is `192655a3...2c457e`. | Regional historical prediction only. Direct-practice county support shrinks to 63/25 corn/soy levels in 2018 and 3/1 in 2019; nothing is filled. The 2019-exclusion check is a no-op because no 2019 difference survives the registered same-county terminal rule. A post hoc balanced 2012--2018 check retains only 13/8 corn/soy counties and is point-only; distribution-versus-quantity rankings do not flip. The bootstrap is conditional on fitted models/splits, not refit, model-selection, population, causal, damage, welfare, or SCC uncertainty, and it does not revise the frozen promotion rule. |
| U.S. competing-moisture Tmax-control sensitivity | The same 20,228 observations and locked splits were evaluated under original controls and six additional stage-average Tmax/squared-level controls, yielding 240 aggregate metrics. The original-control soybean promotions reproduce, but neither soybean practice passes the frozen geographic materiality rule with the richer controls; corn fails under both. Non-irrigated soybean distribution still improves RMSE in AR, KS, and NE under richer controls, but Nebraska is 0.001085 below its materiality floor. A preregistered aggregate-artifact audit verifies all metric keys, eight summaries, full-rank retained designs, endpoint-purge/sample accounting, source hashes, terminal values, and promotion arithmetic with zero discrepancy at saved precision. | Exploratory temperature-control sensitivity on previously examined splits, not fresh confirmation. Stage-average Tmax is not daily extreme-heat exposure. The audit does not reopen inputs or independently refit, and no precipitation attribution, causal effect, damage, welfare, or SCC use is authorized. |
| U.S. daily-heat expansion and moisture sensitivity | Cell-first daily Tmax exceedance and above-threshold counts at 29/30 C cover all 11,861 corn/soy county/crop/year keys (419 counties, 1981--2019) in 149 hash-bound batches. All 64 pilot values reconcile. A full-year attempt was stopped above 1 GiB; the frozen 64-county amendment completed with a 453.1 MiB maximum batch peak. The 360-metric sensitivity reproduces the original baseline exactly; neither daily-heat variant retains the original irrigated or non-irrigated soybean distribution promotion, and corn continues to fail. | Complete historical heat input and exploratory reused-split prediction sensitivity only. Thresholds are inherited sensitivity bases, polygon weather is shared across practices, and no coefficient, causal response, model promotion, projection, damage, welfare, or SCC use is authorized. |
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
| Predeclared later-century ISIMIP3b support expansion | The live official API validates a full 5-ESM x 3-SSP x 2-variable x 2-period Cartesian product: 30 version-`20210512` datasets and 60 public, unrestricted CC0 files totaling 124,935,312,957 bytes. The fixed blocks are 2041--2050 and 2091--2100; eligible engineering harvest years are 2042--2049 and 2092--2099 so cross-year seasons never cross an unacquired boundary. All 60 files pass exact catalogue bytes/SHA-512, decoded 3,652-day global-grid, same-realization GMST, and bounded-feature gates; each block produces 5,488 maize/rainfed seasonal and 16,464 stage rows with exact additive reconciliation. Matched UKESM SSP5-8.5-minus-SSP1-2.6 end-century means are +5.918 C, +29.61 mm seasonal rain, +2.46 wet days, +0.93 maximum-dry-spell days, +2.44 mm Rx1day, and +4.68 mm Rx5day. The complete UKESM end-century whole-scenario audit improves 17/33 comparisons, with median/maximum RMSE ratios 0.99958/1.06170 and 16.51% of values outside exact two-scenario support. The complete five-ESM midcentury product improves 32/55 comparisons, with median/maximum ratios 0.99969/1.08533 and 6.47% outside exact four-ESM support. The matching end-century product improves 30/55, with median/maximum ratios 0.99982/1.01357 and 7.14% outside exact support. The expanded 2,376,990-row training join places every paired FAIR feature level within its bounded envelope; only 44 mapped temperature rows (MPI in 2012) are below support, while pairing, identity, direct/centered, and decreasing-pulse gates pass. | All 60 complete-file gates and thirty bounded feature blocks pass, and registered whole-scenario and whole-ESM engineering audits are complete. Climate comparisons are descriptive and the mixed holdout results do not authorize production. FAIR support covers only the bounded aggregate affine one-crop/two-latitude surface; response, damage, welfare, and SCC gates remain open. The blocks are noncontiguous, and FAIR after 2100 remains outside direct ISIMIP daily-feature support despite the bounded envelope. |
| U.S. national reported-zero support | The exact 1981--2019 all-practice corn source contains 499 reported zero-yield county-years across 150 counties, 18 states, and 217 consecutive spells; the longest spell is 10 years and 118 zero rows have an adjacent positive observation. Every zero lies in 1998--2009, leaving 17 declared years before and 10 after with none, and the top five states contain 73.55% of zero rows (state-row HHI 0.1552). The fixed geography gate retains 419 rows. Only 45 zero rows have a usable fixed-2017 irrigation share; 7/8/8 meet the 10/20/30% high-rainfed selectors. Among adjacent-positive rows, those counts fall to 111 geography-eligible, 15 irrigation-share-eligible, and 4/5/5 high-rainfed. | Descriptive zero-outcome support only. The temporal/state concentration prevents interpreting reported zeroes as a generic crop-failure signal. Nothing is replaced, log-transformed, or modeled; all-practice zeroes are not direct rainfed outcomes. A two-part or other zero-retaining outcome model remains unselected, and no response, damage, or SCC claim is authorized. |
| U.S. national cross-crop selector overlap | Under the fixed 2017 primary 10% irrigation-share selector, corn and soybean share 9,715 reported county-years across 264 counties, 66.30% of the smaller selected crop panel; annual overlap ranges from 161 to 263 counties and county-set Jaccard is 0.475. The 20%/30% sensitivities contain 12,968/14,559 common county-years. | Key-only support audit. A joint crop validation must use the intersection rather than marginal support. No yield magnitude, irrigation effect, response, damage, or SCC result. |
| U.S. joint-crop temporal support | The fixed 10% corn/soy intersection spans 264 counties and 22 states. Median coverage and median longest consecutive run are both 38 of 39 years; 105 counties in 17 states are complete, while the minimum is eight years. | Key-only support, not a mandate to select the complete subset. Missingness, geography, clustering, and overlap remain explicit design issues; no yield magnitude, response, damage, or SCC result. |
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

The separately preregistered 88-template dependence-stability diagnostic reads
only checksum-bound centered derived files and compares median within-template
Spearman matrices under four represented whole-ESM and three whole-scenario
exclusions. Six exclusions pass the fixed tolerances, but MRI-ESM2-0 fails the
maximum gate: wet frequency versus Rx1 conditional on Rx5 differs by 0.192318,
above 0.15. Its mean absolute difference is 0.043330, and no strong pair changes
sign. All three scenario exclusions pass. The failure is retained without
retuning; this is structural stability evidence only, not a joint fit or a
response, damage, welfare, or SCC input.

A separately preregistered decomposition preserves that failed pair and the
0.15 gate. Matching the other ESMs to MRI's observed SSP1-2.6/SSP3-7.0 mix
reduces the absolute median-correlation difference from 0.192318 to 0.173654,
so the missing MRI SSP5-8.5 cell is not sufficient to explain the failure.
SSP-specific differences are 0.163224 and 0.204990, and all eight center-year
differences remain above 0.15. Ten of twelve crop/regime differences exceed
0.15; the exceptions are irrigated- and rainfed-calendar winter wheat at
0.070128 and 0.084917. These are diagnostic correlations, not evidence for an
irrigation treatment or a fitted dependence, response, damage, welfare, or SCC
model.

A preregistered no-fit pool decision audit reads only the completed-matrix,
stability, and MRI-decomposition receipts. The 88-template pooled sample clears
the numeric 51-template threshold but fails the complete balanced-matrix and
adverse-stability gates. Under the frozen eight-center-year design, a complete
ESM-conditional pool contains only 24 templates, a 27-template shortfall. Zero
pools are authorized for dependence fitting or any FAIR, response, damage,
welfare, or SCC use.

The corrected compatibility-first audit reduces the 88 overlapping nominal
templates to an upper bound of 11 pairwise-nonoverlapping templates, or 15 in
the complete five-ESM/three-scenario matrix. A separately preregistered
metadata-only feasibility calculation shows that the smallest design under a
four-window and at-most-two-members-per-ESM-family rule has seven member
tracks. Its 84 compatible templates leave 72 after a whole-member holdout, 60
after the worst whole-family holdout, and 56 after a whole-scenario holdout;
six tracks leave only 48 at the limiting gates. Candidate members, catalogue
availability, bytes, storage, independence, and performance remain unverified,
so no acquisition, fit, FAIR, response, damage, welfare, or SCC gate opens.

The preregistered official-catalogue screen now resolves the candidate-count
gate without reading climate content. Queries across all three SSPs and daily
`pr`/`tas`, with no forcing or member pre-filter, return exactly five complete
ESM-member tracks: GFDL-ESM4, IPSL-CM6A-LR, MPI-ESM1-2-HR, MRI-ESM2-0, and
UKESM1-0-LL. Their four-window source support comprises 30 datasets and 270
public, unrestricted CC0 version-`20210512` files totaling 536,861,000,440
catalogue bytes. Five is below the locked seven-track minimum, so the catalogue
track gate fails. No final ensemble is selected, no climate payload is
downloaded, and storage, independence, MRI stability, fitting, FAIR, response,
damage, welfare, and SCC gates remain closed.

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
The complete five-ESM midcentury product has 905,520 rows and 55 whole-ESM
comparisons. GMST adjustment improves 32/55 over the cell-mean benchmark;
median/maximum RMSE ratios are 0.99969/1.08533, and 58,580 values (6.47%) are
outside exact four-ESM support. The final UKESM SSP5-8.5 2091--2100 pair
brings coverage to 60/60 files and thirty bounded feature blocks. Against the
matched SSP1-2.6 cell, its means change by +5.918 C, +29.61 mm seasonal rain,
+2.46 wet days, +0.93 maximum-dry-spell days, +2.44 mm Rx1day, and +4.68 mm
Rx5day. The UKESM end-century whole-scenario audit improves 17/33 comparisons,
with median/maximum RMSE ratios 0.99958/1.06170 and 29,898 values (16.51%)
outside exact two-scenario support. The complete five-ESM end-century product
has 905,520 rows and 55 comparisons: GMST adjustment improves 30/55, the
median/maximum ratios are 0.99982/1.01357, and 64,665 values (7.14%) are
outside exact four-ESM support. Acquisition and registered whole-scenario and
whole-ESM engineering are complete; FAIR baseline/pulse feature support and
all production gates remain open.
The deterministic early/mid/end-century join contains 2,376,990 bounded
feature rows across 23 training years. Applying the existing matched FAIR
temperature paths produces 127,160 paired rows. All 63,580 feature levels per
alignment method are within the enlarged bounded envelope, and 63,536/63,580
temperature rows are within support; only MPI in 2012 is below its temperature
range. Common-random-number pairing, zero-pulse and pre-divergence identity,
direct/centered agreement, and decreasing-pulse convergence all pass. This is
a bounded aggregate engineering result, not promotion of the adverse affine
response surface; production, damage, welfare, and SCC gates remain closed.

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

The checksum-bound UKESM midcentury multi-crop support audit covers six
crop/regime cells. Five have 5,488 seasonal rows; second-season rice has 3,264.
All have three stage rows per season and exact reconciliation. Mean SSP5-8.5-
minus-SSP1-2.6 seasonal rainfall ranges from -38.27 mm (winter wheat) to
+19.05 mm (second-season rice), maximum-dry-spell changes range from +0.46 to
+9.56 days across rainfed crops, and Rx5day changes range from -3.26 to
+10.37 mm. Soybean irrigated-calendar minus rainfed-calendar exposure is
-16.94 mm rain/-0.83 dry-spell days under SSP1-2.6 and -12.43 mm/-0.80 days
under SSP5-8.5. These are bounded climate/calendar diagnostics, not yield,
irrigation-treatment, damage, or SCC estimates.

The preregistered pathway-aware ridge candidate has now been evaluated under
nested whole-ESM and whole-scenario folds. It improves 71/88 feature-by-
holdout comparisons and passes the median RMSE-ratio criterion at 0.99443, but
fails the locked maximum criterion at 1.00703. It also produces 85 negative
predictions for nonnegative features. Whole-ESM folds improve in 40/55 and
whole-scenario folds in 31/33. The maximum, every-feature, and physical-bounds
promotion gates therefore fail; the candidate is not run through the actual
FAIR pulse path and no response, damage, or SCC input is authorized.

The separately preregistered physical-link successor also fails promotion. It
uses positive log links, bounded logits, and a joint centered-log-ratio stage
composition, with all nested selection and evaluation on the inverse-transformed
physical scale. Only 34/88 comparisons improve; median and maximum RMSE ratios
are 1.00775 and 1.13855. Whole-ESM and whole-scenario folds each improve in 17
comparisons. Bounds pass with zero negative/above-one predictions and maximum
stage-sum error `3.33e-16`, but no stage-share or concentration-HHI comparison
beats the benchmark. Predictive gates fail, FAIR pulse evaluation is withheld,
and no response, damage, welfare, or SCC input is authorized.

The exact-key rejected-candidate comparison finds the physical-link form
better than the identity-link form in only 9/88 comparisons. It rescues zero
identity-link benchmark failures and loses 37 identity-link successes; the two
forms jointly beat the cell mean in only the 34 comparisons retained by the
physical-link model. Physical-domain repair is therefore not predictive
repair, and no adaptive relinking or FAIR pulse evaluation follows.

The preregistered metadata-only fallback audit fixes MESMER-M-TP, the Kemsley
Markov--gamma daily method, MESMER-X Rx1day, and STITCHES. Six method-level
capabilities have published support, but only the monthly precipitation
backbone is established end to end. The fixed daily generator has no
identified pinned public executable source, and fourteen of fifteen chain
requirements remain unresolved. The recorded status is
`fallback_not_executable_no_fit`; no component was substituted, no archive or
climate payload was downloaded, and no emulator, FAIR, response, damage,
welfare, or SCC gate was promoted.

The subsequent metadata/method-only daily-pair interface is preregistered but
not implemented. It requires counter-based or equivalently keyed occurrence,
amount, and spatial innovations whose keys exclude path role, pulse size, and
path-specific climate values. Baseline and all pulse sizes must share exact
monthly innovation digests, while each path separately conserves its monthly
precipitation total and preserves its generated wet/dry occurrence pattern.
Zero-pulse and pre-divergence daily identity, direct-daily benchmarks,
crop-stage reconciliation, whole-ESM/scenario holdouts, and shrinking-pulse
normalized-feature convergence remain mandatory. This specification creates
no generated daily values and does not relax the missing-code no-fit blocker.

The preregistered future-output schema has now been implemented as a
schema/numerical-identity validator without a generator. A tiny in-memory
synthetic bundle contains 32 monthly records across leap Gregorian, noleap,
360-day, and all-zero months, with four matched scales per month. It passes
exact keys, canonical daily-output and monthly-input hashes, common innovation
digests, separate baseline/pulse conservation, and zero/pre-divergence identity
with zero maximum mass error. The monthly-input hash is invariant to record
order, innovation digests, and daily values, but changes to a monthly target or
support flag are rejected. Fourteen deliberate corruptions now fail. This is
software-validation evidence only; it creates no real daily climate path and
opens no fit, FAIR, response, damage, welfare, or SCC gate.

The formerly label-only parameter identity now has a separately preregistered,
synthetic-only canonical object and validator. Each future monthly output key
must have exactly one named record containing two first-order wet-state
transition probabilities, wet-amount gamma shape and scale, component hashes
for spatial dependence and joint temperature--precipitation coupling, and the
same support flag. The receipt and every output record must carry the SHA-256 of
the full record-order-invariant object, and the generator code identity and key
sets must match exactly. A two-record unit fixture rejects ten corruptions; the
existing 32-record four-calendar fixture links one-to-one. These checks bind
metadata and numbers but do not validate their estimation or scientific use;
the unavailable pinned generator remains a hard no-fit blocker and all
downstream gates remain closed.
