# Methods Supporting Information

## September8 paired empirical weather-support diagnostic

The prospective `PAIRED_WEATHER_SUPPORT_PROTOCOL_20260908.md` fixes exact
observed-positive-yield keys (8,465 maize / 4,321 soy rows), three feature sets,
cell-specific factual standardization, marginal ranges, and a descriptive
nearest-neighbor threshold from the factual leave-one-year-out 95th percentile.
Distance is RMS standardized coordinate difference, not Mahalanobis distance;
no covariance inversion, response fitting, trimming, imputation or causal
promotion occurs. The 12-feature distribution set excludes seven maize cells
with a zero-rain regime in either complete path. Constant coordinates and
finite-sample reference exceedances are explicitly reported. All six synthetic
tests and the real diagnostic passed. Hash-bound aggregate, denominators and
resources: `data/provenance/paired_weather_support_20260908.json`.
The diagnostic is not an out-of-sample prediction test or a confidence-level
test. `JOINT_RESPONSE_RESEARCH_DESIGN_20260908.md` specifies the next separate
research-contract requirements without overriding earlier locked gates.

## September8 paired historical counterclimate implementation

The source-bound observational wrapper constructs both published paths from
daily pr/tas/tasmax and the same four calendars and fixed irrigation weights.
Unlike a free-running GCM comparison, factual/counterclim cell-years are paired
because counterclim is derived from the factual sequence. Exact daily axes,
crop coverage and precision-reconciled factual feature parity precede any
contrast. Core features retain500maize/327soy cells; shape comparisons retain
488/325cells after predeclared zero-regime exclusions on both paths. Cell-year
differences are averaged within cell then equally across cells; spatial
quantiles are dispersion, not uncertainty intervals. Predeclared periods are
1982–2010,1982–1991and2001–2010. Both inputs use float64 precipitation sums.

The static noncrop mask and legacy numerical precision required explicit
documented amendments, not silent imputation/tolerance changes. Original
failures remain in the aggregate audit. Eighteen targeted tests pass, along
with exact reconstructed raw-daily primitive sums and reassembled legacy
features. Resources,full denominators,reproduction commands and limitations:
`FACTUAL_COUNTERCLIM_RESULTS_20260908.md` and
`data/provenance/factual_counterclim_pilot_20260908.json`. This validates climate
inputs only; anthropogenic attribution and crop-response transport remain open.

## September8 independent historical model implementation

The historical wrapper and comparator now accept explicit`--model gfdl/ipsl`,
binding model-specific source datasets, paths and protocol hashes. Cross-model
relabeling is rejected by tests; product crop/member/scenario/period are also
checked before comparison. The prospective IPSL protocol applies the same
calendar, fixed-weight, stage, observed-support and distributional comparison
design as GFDL without changing completed GFDL outputs. All nine independently
registered IPSL daily files and both crop builds passed;8targeted tests passed.
Peak sampled RAM746.70MiB, new raw+derived248.85MiB. Complete denominators,
shape exclusions, baseline contrasts, checks and source hashes:
`IPSL_HISTORICAL_CLIMATE_BENCHMARK_RESULTS_20260908.md` and
`data/provenance/ipsl_historical_climate_benchmark_20260908.json`.
No correction, yield prediction, welfare or SCC follows from this comparison.

## September8 published counterfactual-method assessment

ATTRICI supplies a published historical detrending route with seasonally varying
precipitation occurrence/intensity; it does not establish anthropogenic forcing
attribution ([Mengel et al.,2021](https://gmd.copernicus.org/articles/14/5269/2021/index.html)).
The project-specific feasibility, threshold, sequence-dependence and transport
checks are specified in `ATTRICI_METHOD_ASSESSMENT_20260908.md`. No counterclim
product or inferred crop effect has been used yet. This is an alternative to
evaluate, not a replacement for failed validation criteria.

## September8 model-historical distribution benchmark

Source clarification: pr is total water-equivalent precipitation, including
snow, not liquid rainfall alone. The observed GSWP3-W5E5 product and model
adjustment nominally share W5E5 v2.0 for the study period; they are not paired
weather sequences. Primary-source details and review scope are recorded in
`OBSERVED_CLIMATE_REFERENCE_CHECK_20260908.md`.

The prospective`HISTORICAL_CLIMATE_BENCHMARK_PROTOCOL_20260908.md` now has a
completed GFDL implementation. Nine registered pr/tas/tasmax cutouts span
1981–2010, with exact dates/grids/units/nonnegative rain checks and consistent
daily mean/max temperatures. One latitude row per child limits RAM while
preserving the same half-degree grid. Both crop/irrigation calendars produce
29complete harvest years, then existing validated within-regime nonlinear
bases are combined using fixed MIRCA2000 shares. No outcome values are created.

Comparison with historical observed-source exposures uses exact shared cells
and positive-observed-yield availability, not observed/simulated yearwise
weather errors. Per-cell means and temporal quantiles are computed separately
for each source before equally averaging cell differences. A second historical
model calculation restricts years to observed availability solely to assess
sampling composition. Four shape features exclude any cell with a zero-rain
regime in the relevant observed/historical/future comparison; denominators
are reported per scenario. Future-minus-observed mean differences reconcile
to future-minus-model-history plus model-history-minus-observed differences;
this algebra is not a causal decomposition. Marginal heat ranges are also
recomputed against the model's own29year history on the observed-supported
cohort. No bias correction or response transport is performed. Results and
execution details:`HISTORICAL_CLIMATE_BENCHMARK_RESULTS_20260908.md`; aggregate
receipts:`data/provenance/historical_climate_benchmark_20260908.json`.

## September8 full-period heat extension and exact overlap

`FULL_PERIOD_HEAT_PROTOCOL_20260908.md` registers2032–2059harvest years and
ordered2031–2040/2041–2050/2051–2060Tmax files. The independent IPSL extension
has its own prospective protocol. Eight missing public CC0 source-bound
cutouts were acquired; four middle-decade cutouts reused. Source identity,
Gregorian leap-day counts, exact common grid and adjoining timestamps must
pass before calendar-specific construction. Every crop/scenario uses both
irrigation calendars, fixed MIRCA2000 shares,29°Cmaize/30°Csoy thresholds and
0/.3/.7/1stage fractions. Nonlinear terms are built before area weighting.
Season/stage heat sums reconcile; rainfall/heat keys and weighted stage Tmean
match exactly. All26,464overlapping old rows match across every column.

Eight joint tables contain92,624rows on500maize/327soy cells, two latitudes
only. Paired means first average annual differences within cell then give
cells equal weight. Spatial quantiles are dispersion, not uncertainty intervals.
Historical positive-yield1982–2010heat ranges cover292maize/149soy cells;
six marginal heat fields use1e-10absolute comparison tolerance. Missing ranges
are reported, never imputed. These do not establish joint or causal transport.

Full results, source access, observed resource use and preserved synthetic-
fixture/server-wait events are in `FULL_PERIOD_HEAT_RESULTS_20260908.md`;
aggregate receipts and hashes are in `data/provenance/full_period_heat_20260908.json`.
One monitored job/thread,1024MiB sampled RAM and64MiB incremental disk per
batch were used, protecting130GiB free. Existing inputs are separately counted
from new processing outputs. The next baseline comparison must use historical
model distributions, not assume simulated weather is paired with observed
annual weather (`RESPONSE_TRANSPORT_NEXT_STAGE_20260908.md`).

## September 8 independent-model and temporal-window check

Two separately source-bound IPSL cutouts provide the same model/member,
calendar, threshold, geography and years within each scenario pair. The heat
wrapper now validates explicit ESM/forcing/member/scenario as well as variable,
bias adjustment and time frequency. Config and child-file hashes remain
bound to acquisition; pairing additionally compares calendar hashes and fixed
irrigation weights. Existing GFDL defaults and outputs are preserved.

After seeing opposing short-window rainfall signs, a transparently exploratory
diagnostic evaluates2032–2039,2042–2049and2052–2059using the existing balanced
GFDL/IPSL/MPI rainfall products. It reuses the unchanged paired-comparison
arithmetic and previously saved28year reference values, without refitting or
selecting models. Four shared rainfall statistics in the midperiod overlap
match all completed GFDL/IPSL crop comparisons exactly. No heat is imputed for
MPI and no causal decomposition of forced change versus variability is claimed.
The two prospective calculation protocols, numerical checks and all results
are indexed in`IPSL_AND_WINDOW_RESULTS_20260908.md`.

## September 8 matched SSP585 acquisition and joint-climate comparison

Under standing download authorization, a new catalogue-bound SSP585 contract
and request were created without mutating SSP126 files. The generalized
acquisition rechecks the source and request payload; requires a finished job;
binds its capped archive URL/size/ETag before streaming; and reuses safe ZIP,
date/grid/unit/finite-value validators. The generalized heat wrapper verifies
config hash, scenario/model/member identity before constructing any new crop
inputs. Seasonal/stage/calendar reconciliation and fixed-weight allocation
remain unchanged. Four regime products supply maize29°C and soybean30°C
heat on exact retained rainfall support.

The registered comparison uses exact crop/grid/year keys, same fixed weights,
eight complete years, the same model/member and crop-specific thresholds.
Higher-minus-lower feature differences are averaged within cells before equal
cell averaging. Reported cell percentiles are dispersion, not statistical
uncertainty. Independent historical heat-range checks retain the existing
minimum-year/tolerance rules and explicitly missing ranges. Five new archive/
comparison tests pass; four existing join tests pass after wrapper changes.
`PAIRED_HEAT_CLIMATE_PROTOCOL_20260908.md` and its companion results report
record limits and reproduction. None of these calculations estimates yields,
isolates forced precipitation change, or computes a marginal-CO2 damage path.

## September 8 soybean30°C completion and valuation source review

The future heat wrapper now accepts an explicit29/30°C threshold and crop
subset while preserving its original29°C default. New soybean30°C outputs
were computed from the resident file, not by transforming29°C integrals.
Exact keys, calendar fields, stage lengths and seasonal/stage reconciliation
are required before the same fixed MIRCA weighting. The original29°C products
are preserved. A separate real-data comparison checks unchanged rainfall/
temperature fields and cross-threshold degree-day/count inequalities. The
range protocol was extended prospectively to30°C, retaining historical period,
missing-range treatment and numerical tolerance. Results and reproduction:
`SOY_HEAT30_RESULTS_20260908.md`.

The public publisher welfare supplement was streamed in256KiB chunks with
exact34,800,087byte length and PDF-header checks, and independently hashed.
Complete Section K (PDF79–88; printed SI-76–85) was text-extracted and visually
inspected. Its market scenarios and storage coefficient are explicitly
source-located in`config/hultgren_k6_market_scenarios_20260908.json`; none is
a newly estimated or production-selected coefficient. The independent
`src/anticipated_weather_market.py` implements anticipated equilibrium,
unanticipated production, arithmetic price-level shrinkage and final demand
quantity. Expected supply is an input, not an invented13/15year smoother.
Four synthetic test groups cover direct equations, fully anticipated limits
against the independent market core, storage endpoints and invalid domains.
It exports no surplus, damages, adaptation adjustments or SCC. Published
ambiguities and missing cost/inventory/aggregation conventions remain recorded
in`HULTGREN_WELFARE_SOURCE_REVIEW_20260908.md`.

## September 8 real acquisition, two-crop join and heat-range check

The separately authorized single-file workflow has now run successfully on
real climate data. Archive/NetCDF identity, dates, coordinates, units and all
daily values pass validation. Four resident calendars are hash-verified and
processed sequentially; the completed maize/noirr product is reused. Existing
heat-basis validation checks calendar identity, stage duration and seasonal
reconciliation before fixed MIRCA2000 weighting. Exact weighted stage mean
temperatures and crop/grid/year keys match prior rainfall products. New exports
are climate-only, with no synthetic outcomes or response estimates.

`HEAT_CUTOUT_TWO_CROP_PROTOCOL_20260908.md` and
`FUTURE_HEAT_RANGE_PROTOCOL_20260908.md` were registered before their respective
calculations. The latter streams historical heat in8192row batches, uses only
1982–2010 positive-observed-yield rows, requires at least two years per cell,
and compares six stage29°C metrics using fixed1e-10 absolute boundary tolerance.
Missing ranges remain unclassified. It is neither the exact common drought
response sample nor a joint-support/causal-transport test; soybean29°C is not
the locked30°C response control. Six new synthetic tests and all real jobs
pass. Full results, original receipts, source/code hashes and reproduction are
indexed in`REAL_HEAT_CUTOUT_RESULTS_20260908.md`. The older pending-acquisition
description immediately below records the pre-execution state only.

## Bounded acquisition-to-heat execution

`scripts/run_authorized_heat_subset_pilot.py` now implements the single-cutout
chain; before September8 it had not acquired real climate output. A separately recorded actual
user approval must match the job, config hash and64MiB disk cap before any
network request. It revalidates source metadata, rejects changed archive
length/ETag and redirects, streams256KiB blocks, verifies safe ZIP members and
space for archive plus extracted data, and then checks exact dates, grid,
units and finite daily temperatures. Sequential seasonal/stage construction,
validation and reconciliation must also match the retained rainfall calendar
keys exactly. Source/code/output hashes and partial failures are preserved.
Four synthetic test groups pass with network access disabled; they are not
evidence of real server-content validity. Operational reproduction and the
remaining real-data approval boundary are in
`AUTHORIZED_HEAT_SUBSET_WORKFLOW_20260907.md`.

## Future nonlinear rainfall basis and marginal-range comparison

The registered future input construction reuses unchanged historical
`build_regime_candidate_basis` and fixed-share allocation arithmetic on
hash-verified season/stage derivatives. Every future outcome is explicitly
missing in the utility's required schema; no outcome is simulated and outcome
fields are dropped before writing climate-only products. Missing MIRCA cells
are counted and excluded, with no renormalization. Both calendar regimes and
all28harvest years must be present. Basis-before-weighting Jensen checks,
calendar reconciliation and exact scenario keys pass for all18products.
Six direct predictors, stage3share, seasonal rain, three stage temperatures
and the weighted zero-rain flag are preserved. Share/HHI scenario contrasts
exclude cells with any positive-weight zero-rain regime-year in either path.

Historical ranges use only1982–2010 direct-basis rows with positive observed
yields at the same two latitudes. Per-feature cell minima/maxima require
two usable years; actual retained cells have28–29. Undefined zero-rain shapes
are excluded independently of quantities. Every future feature is compared
with its own cell range using fixed absolute boundary tolerance1e-10;
missing ranges, undefined future shapes, below/above counts and the union on
common evaluable rows are reported separately. No significance threshold,
trimming, causal claim or extrapolation repair is inferred from these ranges.
This is not the exact common heat/drought fit sample and does not test joint
climate support. Two separately registered protocols, six synthetic tests,
all products/comparisons and reproduction instructions are documented in
`FUTURE_WEIGHTED_PRECIPITATION_RESULTS_20260907.md`.

## Normalized economic sensitivity and server-cutout heat route

The registered economic sensitivity uses all six rounded point-estimate
columns of Roberts–Schlenker TableA8 (FAS alternative, not the main FAO
baseline), positive supply elasticity and the negative of signed demand
elasticity. For Qs=exp(s)P^es and Qd=P^-ed with baseline value1, the two
predeclared mappings are s=log(a) and s=(1+es)log(a). All36combinations of
column, mapping and a in{0.99,1,1.01} are retained. Rounded printed reciprocal
elasticity multipliers must overlap the intervals induced by rounded inputs;
parameters are not adjusted to force exact agreement. Market clearing,
surplus-component accounting and nonzero-state analytic/finite-difference
derivatives are checked. No independent-normal parameter draws are invented
from marginal standard errors. Source verification limits, the caught and
corrected wrapper derivative error, complete results and reproduction are in
`WELFARE_NORMALIZED_SENSITIVITY_RESULTS_20260907.md`. No actual crop shock,
currency conversion or empirical welfare calibration enters this calculation.

The separate low-storage pilot validates one public ISIMIP3b dataset/file
contract before requesting `select_bbox` on the official server. The request
preserves daily resolution and all longitudes in a one-degree latitude band;
it does not compute spatial means. A completed server job and archive HEAD
length establish availability, not content validity. Real local acquisition
and inspection remain pending. Exact-coordinate calendar selection is opt-in
in both heat builders and never interpolates; synthetic full-grid/cutout
outputs agree exactly across a leap-year-crossing season, two heat thresholds
and three stages. Two tests pass in4.77seconds under a1GiB sampled monitor,
with213.25MiB sampled peak group RSS. The parent catalogue hash cannot verify
the subset bytes; future acquisition must record a distinct child hash and
server-derived lineage. Full storage, date, coordinate, license and feature
checks are specified in `LOW_STORAGE_HEAT_SUBSET_PILOT_20260907.md`.

## U.S. supported-range curves and paired practice contrasts

The curve protocol freezes the existing 24 fits and exports the complete 2×2
rainfall-coefficient covariance only after exact sample and coefficient/SE
reproduction. With p=P/100 and median p0, the contrast vector is
(p-p0, (p-p0)(p+p0)); its covariance quadratic form supplies the log-contrast
SE. Values are transformed with100*expm1 and pointwise normal intervals.
Curves span pooled 5th–95th rainfall percentiles with fixed median reference.
Each point additionally records the share of counties whose observed min–max
range contains both that point and the reference; this is not joint-support
validation. No per-observation predictions or model selection are performed.

The exploratory paired extension was registered after viewing separate curves,
before estimating paired uncertainty. Exact county/year practice pairs and
identical raw designs are required. Regressing log(Y_irrigated/Y_non_irrigated)
on the same fixed effects/design yields the difference in original slopes;
all 12 identities agree within 3.22e-15. County-cluster covariance comes from
paired residuals, retaining their cross-practice dependence. Exponentiated
contrasts describe changes in the fitted yield ratio, not causal effects of
irrigation or adoption values. Both analyses preserve the existing conditional
covariance convention and its limitations. Seven synthetic tests pass, including
direct covariance algebra and pairing failures. Protocols, source hashes,
complete results, figure reproduction and restrictions are documented in
`us_county_validation/US_RAINFALL_CURVE_AND_IRRIGATION_RESULTS_20260907.md`.

## Direct climate-feature scenario comparison

The longer-period extension in `CLIMATE_CONTIGUOUS_CONTRAST_PROTOCOL_20260907.md`
uses 2032–2059 annual features once each, not overlapping smoothed windows.
Source matrix, configs, audits and consumed season/stage files are hash-checked
before one crop/calendar scenario pair is read. GFDL, IPSL and MPI form the
common SSP3-7.0/SSP5-8.5 comparison set; MRI's SSP3-7.0 result is separate.
No missing model/scenario is filled. All six crop-season definitions and both
calendars are retained; precipitation features are not irrigation treatments.
The initial 1e-5 °C temperature-reconciliation check failed on a 1.00336e-5 °C
discrepancy. The protocol transparently records the float32-precision diagnosis,
revised 1e-4 °C numerical tolerance, synthetic boundary tests, and failed runs.
Actual maximum residuals are retained, not silently corrected. The short and
long source assemblies agree exactly over 60,368 common maize crop-year
records for every feature. Stage mean temperatures are present, but aligned
midcentury Tmax threshold integrals are absent from these consumed schemas.
Results therefore do not feed a joint agricultural response. Full reproduction
and the complete aggregate artifact are in
`CLIMATE_CONTIGUOUS_CONTRAST_RESULTS_20260907.md`.

`CLIMATE_SCENARIO_CONTRAST_PROTOCOL_20260907.md` prespecifies direct SSP3-7.0
and SSP5-8.5 minus SSP1-2.6 differences, without fitting an emulator or using
outcomes. For five ESM/member pairs, exact cell/year matches are averaged
within 2042–2049 or 2092–2099 and then equally across calendar-support cells
at 39.25°N and 39.75°N. USA/CHN singleton-country-proxy subsets remain
cross-sections, not national coverage. The 11-feature table is hash-pinned;
one ESM is read at a time in 8,192-row batches. Composition, finiteness,
support, scenario/member and GMST identity checks must pass. Shape summaries
exclude cells with any zero-rain season on either path, with counts retained.
The legacy timing index uses weights (1/6, 1/2, 5/6) on shares from windows
with boundaries (0, 0.3, 0.7, 1); it is not an exact day-based centroid.
HHI describes three-window concentration, not daily concentration or measured
phenology. Model medians/ranges are
descriptive, not confidence intervals. Eight-year windows, internal variability,
joint forcing differences and unequal agricultural relevance limit inference.
The calculation does not feed historical coefficients, welfare or SCC.
`CLIMATE_SCENARIO_CONTRAST_RESULTS_20260907.md` provides reproduction commands,
test outcomes, resource use and the complete aggregate-result artifact.

## Country-specific annual-shock sensitivity

The separate `GLOBAL_COUNTRY_CONTROL_PROTOCOL_20260907.md` registers a
conservative, outcome-independent label assignment from retained MapSPAM
footprint coordinates: a half-degree cell receives a country proxy only when
all included five-minute cells agree. Country codes are checked against the
retained official sources; ambiguous and absent cells are not guessed.
This is not independent administrative geometry, and the circa-2000
agricultural-footprint selection is a limitation.

On identical mapped training differences, global-year or country-year
intercepts are absorbed by group-demeaning outcome and regressors. OLS slopes
and cluster-score covariance are compared with explicit dummy-variable
synthetic calculations. CR1 uses G/(G-1)*(N-1)/(N-H-K), counting H absorbed
groups and K slopes. Country and 20-degree clusters are separate conditional
sensitivities. Singleton groups remain zero-contribution demeaned rows;
nominal cluster counts do not imply equal information or independence.
No terminal outcomes, welfare weights, climate projections or coefficient
draw exports enter this fit. `GLOBAL_COUNTRY_CONTROL_RESULTS_20260907.md`
records every fit, support loss, limitation and reproduction path.

## Uncalibrated economic-accounting implementation

The independent closed-market constant-elasticity accounting module in
`src/constant_elasticity_market.py` has passed seven synthetic tests, including
numerical integration and stable infinitesimal supply changes. It does not
consume empirical yield responses or emissions. Definitions, independently
derived equations, alternative yield-to-supply conventions and calibration
gaps are specified in `WELFARE_ACCOUNTING_PROTOTYPE.md`. The exact published
valuation equations have not yet been verified, and this is not a replication
claim or a welfare/SCC result. No adaptation-cost or currency conversion is
silently supplied, and GIVE's agriculture producer has not been changed.

## September 7 exploratory global association supplement

`GLOBAL_HISTORICAL_ASSOCIATION_PROTOCOL_20260907.md` defines a separate
descriptive extension; it does not release predictive coefficients for SCC.
The estimator streams the same source-hash-verified common-support tables,
retains consecutive log-yield differences ending in 1983–2010, and compares
four separate moisture families under quadratic time controls and annual
intercepts. Six stage temperature/heat terms are common to every fit.
For each 10- or 20-degree spatial cluster, it accumulates X'X and X'y, solves
the scale-normalized pooled system, then computes cluster scores
X_g'y_g − X_g'X_g beta. CR1 covariance multiplies the sandwich by
G/(G−1) × (N−1)/(N−K). Partial log contrasts c'beta use variance c'Vc;
normal intervals are transformed monotonically by 100 × (exp(x)−1).
The two block definitions alter covariance, not fitted point contrasts.

This construction preserves basis-before-irrigation-weighting and does not
duplicate GDHY outcomes. It uses neither terminal test outcomes nor spatial
holdout scores for model selection. Full definitions, all 32 covariance
records, sample counts, limitations, run resources and reproducibility paths
are in `GLOBAL_HISTORICAL_ASSOCIATION_RESULTS_20260907.md`. Tests compare
sufficient-statistic algebra with direct synthetic OLS/cluster covariance,
reject rank failures and terminal-year inputs, and verify contrast design.
No future response bundle or monetary result is emitted.

## S1. Reproducibility scope

This document specifies a reproducible replacement for the temperature-indexed
agriculture pathway in GIVE. Raw data are excluded from Git; exact records are
stored in `data/provenance/`. The project has no wildfire inputs or code
dependencies.

### September 4 regional robustness additions

The source-hash-validated regional panel was fitted under original controls,
additional stage-average daily maximum-temperature linear/quadratic controls,
and a 2000–2018 period restriction. Both rainfall forms and both irrigation
practices were retained for corn/soybeans (24 fits). Protocol and scripts:
`us_county_validation/US_REPORTING_HEAT_SENSITIVITY_20260904.md` and
`us_county_validation/scripts/run_reporting_heat_sensitivity.py`.
An independent QR coefficient/covariance audit checked these 24 fits using
the same residualized design; it was not an independent sample replication.

For non-irrigated crops, a subsequent exploratory state-influence check
retained the previously selected crop-specific forms and omitted each state
under original and added Tmax controls (30 omissions plus four references).
Quantity contrasts use the unchanged full-sample median rainfall. This is
coefficient influence analysis, not held-out prediction or spatial inference.
See `us_county_validation/US_STATE_INFLUENCE_PROTOCOL_20260904.md` and
`us_county_validation/scripts/run_state_influence.py`. No omission-fit
uncertainty claims are made. Every omission and failure status is preserved.
Both analyses use existing inputs, sequential fits and the sampled job-group
memory monitor described in `LOW_MEMORY_WORKFLOW.md`.

### September 5 competing-moisture predictive sensitivity

The hash-verified common first-difference panel and original validation splits
were reused for an exploratory maximum-temperature sensitivity. Differences
of stage-average Tmax levels and of their squared levels were added to every
model family; no direct rainfall and PDSI features were stacked. Training-only
scaling and purging of shared outcome endpoints were retained. The 240
aggregate metrics cover both original and modified controls. These previously
examined splits are not independent confirmation. See
`us_county_validation/US_MOISTURE_TMAX_PROTOCOL_20260905.md` and
`us_county_validation/scripts/evaluate_moisture_tmax_sensitivity.py`.
The verified result weakens the earlier soybean distribution-promotion claim;
all split outcomes, including failed materiality criteria, are retained.
A preregistered pure-standard-library follow-up independently validates the
tracked aggregate JSON and its written claims without reopening raw/interim
panels or refitting. It requires exact 240-row metric support, eight summaries,
full-rank retained designs, endpoint-purge and sample-count reconciliation,
source hashes, and direct recomputation of every promotion comparison. The
saved reconciliation error is zero at artifact precision. This checks internal
aggregate-result integrity, not sample construction, exposure construction,
model fitting, or causal identification.

### September 6 continuous temporal benchmark

The retained assembly-hash-verified global maize/soy tables were read in
8,192-row batches and joined in ten-degree latitude bands on exact
crop/grid/year keys. Matched positive yields and consecutive years define
the common first-difference support. Training ends in 2010; terminal test
differences start in 2012, avoiding a shared 2011 outcome endpoint. Test
cells must have training differences. All models include stage mean
temperatures, crop-specific stage Tmax degree days, and deterministic year
terms; moisture families remain separate. Scale-normalized accumulated
cross-products yield aggregate test loss without storing global predictions.
See `GLOBAL_CONTINUOUS_TEMPORAL_PROTOCOL_20260906.md` and
`scripts/global_continuous_temporal_benchmark.py`. Full-record scPDSI
calibration makes this retrospective. No spatial inference or causal
interpretation is authorized by this diagnostic.

### September 7 geographic/source-cluster audit

Before evaluation, we froze five outcome-blind folds defined from 10-degree
latitude/longitude source blocks. Each fold is trained on 1983--2010
consecutive differences outside its blocks and scored on 2012--2016
differences inside them; 2011 endpoints remain purged, and terminal cells must
have at least one earlier consecutive difference. The five feature
specifications and exact three-family common support are unchanged. We read
one derived Parquet file at a time in separate historical and terminal blocks,
accumulate scale-normalized training cross-products, and suppress coefficients
and row predictions. Paired 5,000-draw PCG64 resampling retains all losses
within each selected 10-degree block and resamples blocks within folds. The
resulting percentile ranges are descriptive uncertainty conditional on the
five fixed fits, not causal confidence intervals or a full spatial-dependence
model. The aggregate result is byte-reproducible and used 394,936,320 bytes
peak sampled process-group RSS. See
`GLOBAL_CONTINUOUS_GEOGRAPHIC_CLUSTER_PROTOCOL_20260907.md` and
`scripts/global_continuous_geographic_cluster_audit.py`.

### September 7 U.S. daily heat-control construction

A single-county/year pilot first constructed daily Tmax exceedance in
Celsius-days and above-threshold days at 29 and 30 C, applying thresholds
cell-first before county-polygon weighting. All original stage Tmax means
and stage/season totals reconcile. The basis was then expanded to all 11,861
corn/soy county/crop/year keys in the 1981--2019 direct-practice support. The
1 GiB monitor stopped the full-year route in 1984; a frozen amendment used 149
disjoint groups of at most 64 counties, with a 453.1 MiB maximum peak. Exact
keys, calendars, hashes, weights and all 64 pilot values reconcile. An
exploratory sensitivity added stage heat sums and counts at 29 and 30 C
separately to every moisture model on the unchanged 20,228 differences.
Neither threshold retains the original soybean distribution promotion. See
`us_county_validation/US_DAILY_HEAT_EXPANSION_RESULTS_20260907.md`. These are
not hourly degree days, crop-pixel exposures or estimated damage responses.

## S2. Data acquisition and provenance

**September 7 daily-heat association update:** a separate exploratory
24-cell matrix preserves the original regional 1981–2018 county/state-year
fixed-effect model, adds stage heat-exceedance sums/counts with linear and
quadratic terms at either 29 or 30 C, and retains both crop/practice and
rainfall forms. Identical support is enforced. QR/triangular-solve covariance
reproduces baseline coefficients/SEs; county-cluster normal intervals remain
conditional, not full spatial/causal uncertainty. A subsequent 34-cell
non-irrigated state-influence matrix evaluates at unchanged full-sample
median rainfall. Protocols, aggregate outputs and tests are documented in
`us_county_validation/US_DAILY_HEAT_ASSOCIATION_RESULTS_20260907.md`.

The outcome panel uses GDHY v1.2/v1.3 (Iizumi and Sakai, 2020), with the
downloaded archive checksum in its TOML record. Daily historical climate uses
ISIMIP3a GSWP3-W5E5; projections use ISIMIP3b CMIP6 bias-adjusted daily
fields. Crop calendars use GGCMI Phase 3 2015soc files (DOI
10.5281/zenodo.5062513). Capture the ISIMIP API response, file version,
license/terms, SHA-512, retrieval date, and URL for every file. Climate files
are multi-gigabyte global arrays and must be streamed/chunked; do not commit
them. The tracked ISIMIP3a record now pins all 16 historical files by name,
URL, byte length, and SHA-512; the recursive verifier checks conventional and
nested historical/projection records. Daily builders accept only explicit
precipitation-flux/mm-per-day and Kelvin/Celsius unit sets and reject blank or
unknown units and nonpositive wet-day thresholds. See `data/input_manifest.csv`.

Fixed irrigation-exposure weights use MIRCA-OS v2 (March 2026) annual
irrigated and rainfed harvested-area maps. The source archive, CC-BY-4.0
license, HydroShare resource, byte length, MD5, and SHA-512 are pinned in
`data/provenance/mirca_os_v2_irrigation_shares.toml`. Use the publisher's
30-arcminute GeoTIFFs only after verifying one 360-by-720 EPSG:4326 grid,
0.5° cell centres, finite nonnegative hectares, unique crop/system/vintage
files, and unit-summing shares. Raw rasters and derived tables remain ignored.

The U.S. validation outcome source is the dated USDA NASS Quick Stats crops
bulk snapshot `qs.crops_20260821.txt.gz`. Acquisition pins the declared byte
length, ETag, and last-modified value; downloads verified HTTP ranges and
refuses to continue a partial file if source identity changes; and records a
streaming SHA-512 only after completion. Raw records and the acquisition
sidecar are excluded from Git. Commodity, practice, geography, unit, and
suppression filters are fixed only after schema inspection and are recorded in
the processed-panel manifest.

The executable county-input status gate records that the local bulk NASS
archive is still incomplete, while bounded credential-safe API acquisition is
operational. Exact 2018--2022 all-practice corn yields are acquired. A separate
all-years, all-classes screen acquired paired `IRRIGATED` and
`NON-IRRIGATED` yield series for corn, soybean, and wheat, plus exact
2012/2017/2022 Census irrigated and total harvested-acre records. The
practice-yield support is regional rather than national. The 2017 Census share
is the pre-outcome national selector, with 2012/2022 vintages as sensitivities;
missing or suppressed irrigated acreage is excluded, never zero-filled.
For counties with numeric shares in all three vintages, a descriptive
outcome-free audit reports 2017--2022 10%-selector agreement of 92.28% for
corn, 92.64% for soybeans, and 84.16% for wheat. The corresponding correlations
are 0.938, 0.954, and 0.834. The primary 2017 selector is unchanged, while
wheat requires explicit vintage sensitivity; no irrigation effect, response,
damage, or SCC claim follows from this diagnostic.
A counts-only selector audit then reads only crop, county, year, fixed-share,
and eligibility fields from the locked 1981--2019 national panel. The
10/20/30% thresholds retain 20.80%/26.15%/29.30% of reported corn county-years
and 23.65%/27.97%/30.16% of reported soybean county-years. At 10%, annual
retained support spans 296--424 corn and 283--391 soybean counties. The audit
does not read yield magnitudes, change the primary 2017 selector, identify an
irrigation effect, or authorize response, damage, welfare, or SCC use.
A key-only companion audit intersects the two crop panels without reading
yield magnitudes. At the primary 10% selector it retains 9,715 common
corn/soybean county-years across 264 counties, or 66.30% of the smaller
selected crop panel. Annual overlap ranges from 161 to 263 counties and the
county-set Jaccard index is 0.475. The 20% and 30% sensitivities retain 12,968
and 14,559 common county-years. These counts define feasible joint-crop support
only; they do not identify an irrigation effect or response.
The companion outcome-blind state-FIPS audit retains 28 of 41 reported corn
states and 28 of 31 reported soybean states at the 10% selector. Top-five-state
county-year shares are 42.96% and 42.15%, respectively. This result fixes
state/region-blocked holdouts as a necessary national validation gate without
reading yield magnitudes or altering the selector.
All API queries, counts, checksums, and coverage appear in
`data/provenance/nass_irrigation_practice_screen.toml`. No county response is
estimated until the full county-polygon primary exposure, CDL sensitivity,
daily primary/robustness weather coverage, complete calendars, geography
crosswalks, and predeclared validation records pass.

For 1981--2019, the fail-closed direct-practice builder requires positive
numeric yields for both practices in the same crop--county--year. It retains
7,079 corn, 4,845 soybean, and 9,672 all-classes-wheat pairs (43,192 long
rows). The 807 unique GEOIDs all match 2019 TIGER. Screening against pinned
official Census county-change pages flags eight counties for historical-
boundary resolution and two name/code-only reviews; absence from these
substantial-change pages is not interpreted as proof of boundary stability.

The primary U.S. weather candidate is NOAA NCEI nClimGrid-Daily v1.0.0.
`data/provenance/nclimgrid_daily_198101.toml` pins the January 1981 object to
59,955,310 bytes; `data/provenance/nclimgrid_daily_1981_cuming_smoke.toml`
pins the six May--October objects used in a bounded crop-season smoke. Each
record preserves live HTTP identity, SHA-512, embedded product version and
license statement, increasing 596-by-1,385 grid, exact chronology, and all
four required fields (`prcp`, `tmin`, `tmax`, and `tavg`) with units. Each date
denotes the 24-hour period ending in the early morning. NCEI notes that v1
inputs can change without a version bump; every monthly object is pinned
independently. The real Cuming construction is an exposure-engineering check,
not a response estimate or precipitation trend.

The isolated all-practice route was also exercised for Acadia Parish,
Louisiana (GEOID 22001) in 2019. The hash-bound receipt retains 119 positive
polygon/grid intersections, five monthly weather inputs, and one supported
soybean crop-county-year feature row. This geographically distinct check
validates plumbing and lineage only; it is not a national sample or a climate--
yield estimate.

For the partial national weight checkpoint, a separate audit rereads every
completed receipt, verifies all 932 corresponding Parquet hashes and frozen
contract identities, and summarizes land-relative weather-valid coverage
without resuming construction. Completed receipts cover 35.46% of the 2,628
registered counties across 16 states; 60 have positive masked area. The
minimum completed ratio is 0.960832366, one is below 0.97, and seven are below
1.0. The partial set reflects FIPS-ordered execution plus earlier bounded
smokes and is not a representative national sample. Consequently, Trigg's
lower 0.907267979 ratio remains a fail-closed source-geometry question rather
than grounds for a post-result threshold change or silent county exclusion.
The follow-up source audit pins the official 2019 Census TIGER/Line Trigg
County area-water archive (625,481 bytes; SHA-512 recorded in provenance).
Its 2,123 features' `AWATER` values sum exactly to the county's 102,999,105 m2.
Within each polygon, the audit applies its published
`AWATER/(ALAND+AWATER)` fraction to exact EPSG:5070 county/grid intersections.
The 16 masked cells contain an estimated 81,538,947 m2 water and 127,512,062
m2 land; weather-valid fractional-land coverage is 0.888503097 and remains
below the unchanged 0.95 gate. No output partition is emitted.
For an outcome-free source sensitivity, we separately hash-bind NOAA's four
January 1981, July 2000, and January 2019 county area-average files,
product-version receipts, and official numeric NCEI-to-FIPS state crosswalk.
Every sampled variable/month contains the same 3,107 county rows. Numeric code
15221 maps to Trigg FIPS 21221; all sampled Trigg real-day values are finite,
satisfy `TMIN <= TAVG <= TMAX`, and reproduce the rounded temperature midpoint
within 0.005 C. July 2000 also validates Adair County, Iowa (19001), under the
same mapping and value gates. These samples validate a source-computed county
route but do not replace the
registered polygon estimator; boundary
vintage, full-period identity, and feature-equivalence gates remain open.
We then compare the official county averages directly with the fixed 2019
TIGER polygon-weight proxy for two preregistered counties (Cuming County,
Nebraska, and Fresno County, California) in April 1990, February and July 2000,
July 2012, and January, June, and December 2019. Each month requires
exact common 3,107-county support, complete daily
chronology, finite values, declared units and physical bounds, fixed positive
unit-sum polygon weights, and identical county identities. Hash-bound inputs
and daily difference metrics are recorded for every county-variable cell.
The largest monthly precipitation-total difference is 0.9926 mm; a near-zero
Fresno precipitation series in July 2012 has the lowest correlation (0.98533),
while temperature correlations otherwise remain above 0.99999 apart from an
April minimum of 0.999993. A hash-bound series gate requires all 56 selected
county-variable-month cells. Fifty-five have nonzero maximum differences; the
remaining dry Fresno July-2000 rainfall pair is an exact constant match with
undefined correlation. These are measurement-route sensitivities, not an
equivalence test, estimator selection, response estimate, or SCC input.

A complete bounded acquisition now records all 468 canonical monthly objects
for 1981--2019, totaling exactly 27,857,685,556 bytes (25.944 GiB). Before each
object entered the atomic local manifest, the utility required the frozen HTTP
identity and exact byte length, computed a local SHA-512, and validated the
NetCDF schema, four required fields, embedded product metadata, day-label
semantics, and exact daily date coverage. Every resume invocation revalidated
all already manifested objects; a changed upstream identity, local hash,
schema, or calendar failed closed. The raw files and working manifest remain
Git-ignored. These checks establish a reproducible historical-weather input,
not a county exposure, predictive relationship, causal response, or SCC term.

The first U.S. weather-file smoke is the official NKN annual gridMET 2018
precipitation object. `data/provenance/gridmet_pr_2018.toml` pins its mutable
direct URL to 65,031,749 bytes, a complete 365-day 2018 calendar, the decoded
585-by-1,386 grid, millimetre units, ETag, Last-Modified value, and SHA-512.
The publisher states that copyright and related rights are waived to the
extent possible but does not name an SPDX license, so the record uses
`NOASSERTION`; raw data remain gitignored. Any changed HTTP identity or local
hash fails closed. Because the publisher cautions that source changes create
inhomogeneities in gridMET precipitation, gridMET is a historical robustness
product here, not a stand-alone basis for precipitation intensity/frequency
trends. Timing and extreme-response conclusions require agreement across the
declared primary and robustness weather products.

The U.S. model comparison gives climatic-water-balance indices equal standing,
not an appendix-only role. Crop-calendar PDSI/scPDSI and leakage-safe SPEI at
pre-registered accumulation windows are evaluated as alternative moisture-
stress representations under the same county, temporal, and drought-severity
outer holdouts as the direct-weather reference. SPEI calibration parameters
are estimated in training data or a fixed predeclared historical period and
are never refit on holdouts. PDSI/SPEI specifications replace the direct
precipitation-water terms unless a separate attribution design is frozen;
their effects or damages are not added to direct-precipitation effects.
Irrigation-stratified reporting is required because an index derived from
meteorological supply does not observe applied irrigation water.
[Dai (2011)](https://doi.org/10.1029/2010JD015541) documents PDSI variants,
while [Vicente-Serrano, Begueria, and Lopez-Moreno
(2010)](https://doi.org/10.1175/2009JCLI2909.1) defines the multi-scalar SPEI
framework. [Kuwayama et al.
(2019)](https://doi.org/10.1093/ajae/aay037) supplies the primary U.S.
observed-drought agricultural benchmark. These sources support definitions and
comparison design, not transport of their estimated responses into the global
model.

The primary SPEI route is computed rather than imported. U.S. construction
uses the acquired nClimGrid-Daily `prcp`, `tmin`, and `tmax`; global
construction uses source-consistent ISIMIP3a GSWP3-W5E5 `pr`, `tasmin`, and
`tasmax`. Daily Hargreaves-Samani reference ET0 uses the FAO-56
extraterrestrial-radiation equations and
`Tmean=(Tmin+Tmax)/2`; it represents climatic evaporative demand, not actual
evapotranspiration, applied irrigation, or soil moisture. Complete daily
precipitation and ET0 are summed to calendar months, and right-aligned 1-, 3-,
and 6-month `P-ET0` balances are formed. For each scale, native grid cell, and
calendar month, a three-parameter log-logistic distribution is fit by unbiased
probability-weighted moments to the 30 observations in 1982--2011. Parameters
are frozen before the 2012 terminal block. Missing calibration months,
degenerate fits, nonfinite values, or unreported tail-probability clipping fail
closed. The three scales remain separate models and are never stacked or
selected by SCC magnitude.

NOAA's current nClimGrid-Monthly SPEI uses a declared 1895--2014 calibration
and Thornthwaite PET, so it overlaps the terminal period and is retained only
as a retrospective U.S. implementation check. SPEIbase 2.11 uses CRU TS 4.09,
FAO-56 Penman-Monteith PET, and the SPEI package, but its public generation
repository still documents version 2.10 and does not expose a verified v2.11
reference subset; it is a retrospective global PET/implementation check rather
than the primary terminal-score field. Crop-window means day-weight monthly
values over overlapping calendar days and are explicitly retrospective at
partial boundary months; a month-end-inside-window sensitivity avoids
post-window boundary weather at the cost of dropping partial months. Before
any outcome fit, a master intersection must make direct precipitation,
PDSI/scPDSI, and all three SPEI scales share identical outcomes, calendars,
controls, weights, split labels, and first-difference endpoints.

The fixed-calendar source is the exact checksummed USDA NASS 2010 *Field Crops
Usual Planting and Harvesting Dates* report. NASS defines published begin/end
dates as approximately 5/95 percent completion and most-active intervals as
approximately 15/85 percent completion. The selected engineering default uses
the floor midpoint of each most-active planting/harvest boundary; the broader
published begin-to-end envelope is a sensitivity. Final causal-model calendar
selection remains validation-dependent, and annual Crop Progress timing is a
realized-timing/adaptation sensitivity. All-classes wheat is never assigned one
generic calendar: winter, spring, and durum feature bases remain separate
until independent class-area shares exist.

The deterministic parser validates the pinned PDF hash before reading pages 9,
25, 33, and 34, preserves all eight published date boundaries and 2009 acreage
context for 130 state/crop rows, and rejects unexpected row counts or date
tokens. Expansion over 1981--2022 produces 10,920 unique rows for two calendar
roles, 42 states, and five crop classes. Cross-year planting is resolved
sequentially relative to the harvest year; all 3,696 cross-year rows and all
same-year rows pass season order, duration, fixed-month/day, and harvest-year
checks. This is deterministic exposure alignment, not observed annual timing.

The selected full-period primary route intersects audited Census county
polygons with nClimGrid cells in EPSG:5070 and applies the intersection-area
weights only after cell-level feature construction. It is labeled a county-
average proxy because it does not isolate crop pixels. The separate fixed-2017
CDL sensitivity uses official 30 m class pixels selected by center inclusion
in the county and mapped to nClimGrid cells. The acquired source reports class
0 as background while nodata is unset; class 0 is therefore excluded
explicitly. Corn (1), soybean (5), durum wheat (22), spring wheat (23), and
winter wheat (24) are distinct, and double-crop classes are not silently
pooled.

Both spatial routes require exact five-digit NASS GEOIDs, audited Census
county-change status, in-grid nClimGrid indices, area/coverage reconciliation,
weights summing to one, and false response/SCC authorization flags. Nonlinear
temporal/extreme/response bases are constructed at the weather-cell and
calendar-class level before either polygon or crop-pixel weighting. National
CDL coverage begins in 2008; a later fixed mask applied to 1981--2007 is an
explicit retrospective measurement sensitivity, not observed crop location.
That limitation is binding for paired all-classes wheat, which has no post-
2007 support; pooled wheat response estimation remains blocked.

The bounded real spatial smoke uses Cuming County, Nebraska (GEOID 31039).
The polygon route reconciles its EPSG:5070 area to TIGER `ALAND+AWATER` at
relative error (3.05\times10^{-8}), covers the county with 120 positive
nClimGrid intersections, and normalizes weights to one. The 2017 CDL window
contains 706,394 corn pixels (635,754,600 m2) and 582,110 soybean pixels
(523,899,000 m2); all selected pixels map into 120 nClimGrid cells per crop,
and the pixel-center county-area approximation differs from polygon area by
(1.71\times10^{-5}). May--October 1981 daily features were built cell-first
under both routes and joined to four real paired-practice NASS support rows.
The executable comparison covers 18 weather features and two crop-year keys;
its largest absolute relative route difference is 0.00762. This is a one-
county/year spatial-measurement diagnostic only. It neither estimates a
climate--yield relationship nor establishes general equivalence of the routes.

### U.S. national corn/soy construction and predictive protocol

The registered direct-practice comparison contains 419 counties in 11 states,
11,861 unique crop--county--years (7,016 corn and 4,845 soybean), and 23,722
practice rows. One weather exposure is duplicated exactly across the distinct
irrigated and non-irrigated outcomes; applied irrigation water is not inferred
from nClimGrid. A fixed validity mask excludes cells that are nonfinite for any
of the four required fields on any day of January 1981 before county weights
are normalized. Of the 419 counties, 30 have at least one masked intersection.
The minimum valid/full-legal-polygon fraction is 0.529533 in a water-rich
county, but the minimum valid-area/TIGER-declared-land fraction is 0.983710;
all counties therefore pass the locked 0.95 declared-land gate. The 419
atomic county partitions contain 79,355 positive valid intersections.

For each cell and fixed state/crop calendar, the national builder constructs
seasonal precipitation total; 0--30%, 30--70%, and 70--100% precipitation
shares; timing centroid and concentration; wet-day frequency conditional on a
1 mm threshold; conditional wet-day intensity; maximum consecutive dry days;
Rx1day and Rx5day; and seasonal/stage temperature summaries. These nonlinear
bases are formed before county weighting. One atomic feature partition and
source-bound receipt is written per harvest year. All 39 partitions for
1981--2019 pass raw-month identity, calendar, grid, unit, key, finiteness,
practice-pair, and fixed-mask gates. Default assembly rehashes the raw weather
and exactly reconstructs 23,722 registered practice rows (table SHA-256
`205a94ae92c12810026c9c5d0ac0fa3760e46ebc39669e528ba20a125a0c46d7`);
a separate exact-recomputation receipt passes. This validator reuses the
registered implementation and is described as exact recomputation, not an
independent implementation.

The positive log-yield construction separately exposes the 499 reported corn
zeroes in its source table. A source/hash-bound support audit counts 150
counties, 217 consecutive spells, and a maximum 10-year spell; 419 zero rows
pass the fixed geography gate, 45 have a usable fixed-2017 irrigation share,
and 7/8/8 meet the 10/20/30% high-rainfed selectors. It also records that all
zeroes lie in 1998--2009, the five leading states contain 73.55% of zero rows,
and only 15 adjacent-positive rows have an eligible irrigation share (4/5/5
meet the three high-rainfed selectors). No zero is replaced or log-
transformed, and the audit emits no coefficient. A zero-retaining outcome
model remains a required, separately preregistered sensitivity; temporal and
state concentration prohibit interpreting reported zeroes as a generic crop-
failure signal.

The mutually exclusive moisture-family screen compares: common stage-mean
temperature controls only; controls plus seasonal precipitation total;
controls plus total and eight distribution/extreme terms; controls plus
seasonal-mean PDSI; and controls plus four preplant/stage PDSI summaries. No
model contains both direct precipitation and PDSI. Exact source validators
bind 23,722 direct-weather rows, 118,610 monthly-index window rows, and 2,808
calendar rows. Their identical common support yields 20,228 consecutive-year
changes: 5,952 per corn practice and 4,162 per soybean practice. Initial or
gapped years are not differenced, and training differences sharing either
level endpoint with a test difference are purged.

Direct-practice reporting support is strongly unbalanced over time and is
never filled. Unique corn/soy county levels are generally near 200 per crop in
the 1980s and 1990s, fall to 115/67 in 2012, 63/25 in 2018, and only 3/1 in
2019. The same-county terminal tests contain 434 corn and 262 soybean
first-difference rows per practice after endpoint purging, but are conditional
on this selected reporting support. Publication sensitivities therefore omit
the sparse 2019 endpoint and use fixed-county support windows; neither is a
model-selection input.

Models are fit separately by crop and irrigation practice. Continuous columns
and quadratic year terms are centered/scaled using training rows only. A
rank-revealing least-squares solve uses the registered relative singular-value
cutoff of (10^{-10}); numerical warnings or nonfinite singular values,
coefficients, predictions, or metrics fail closed. Aggregate RMSE, MAE,
predictive R-squared, and correlation are scored for eligible leave-one-state-
out development tests, a same-county terminal 2012--2019 test, and development-
period precipitation tails. Distribution is promoted by the frozen
development rule only when it improves RMSE in every eligible state by at
least the greater of 0.0001 and 1% of quantity-only RMSE. Terminal and extreme
tests are confirmation evidence and are not used to tune that rule. Neither
coefficients nor row predictions are emitted. The exercise is a historical,
regional predictive screen; it is not a causal yield response, nationally
representative U.S. estimate, damage function, or SCC input.

### Preliminary direct-practice fixed-effects association

A separate, coefficient-bearing diagnostic uses the same validated direct
NASS/nClimGrid levels but excludes 2019 before estimation because reported
support collapses to three corn and one soybean county levels. For crop
`c`, irrigation practice `r`, county `i`, state `s`, and harvest year `t`, the
registered association is

\[
\log Y_{icrt}=\alpha_{icr}+\lambda_{sct}+f_c(P_{ict})+
\sum_{k=1}^{3}\left(\gamma_{kcr}T_{kict}+\delta_{kcr}T_{kict}^2\right)
+\varepsilon_{icrt},
\]

where `P` is crop-calendar seasonal precipitation and `T_k` is mean
temperature in fixed 0--30%, 30--70%, and 70--100% season windows. The
quantity form uses precipitation per 100 mm and its square. The timing form
also includes early- and middle-window precipitation shares; the late share
is omitted. County fixed effects and crop-specific state-by-year fixed effects
are removed by alternating projections to a maximum-change tolerance of
`1e-10`; the within regression is solved by rank-checked least squares and
uses a finite-sample-corrected county-cluster sandwich covariance estimator.

The primary form is frozen from the preceding outer-holdout screen before
coefficient estimation: quantity for corn, quantity plus timing for soybean.
The reported quantity contrast adds 100 mm at the observed 25th, 50th, and
75th precipitation percentiles and evaluates the quadratic exactly. The timing
contrast moves 0.10 share from the omitted late window to the middle window,
holding total rain, early share, temperatures, and fixed effects constant. It
is explicitly partial and does not reconstruct co-moving dry-spell or
heavy-rain statistics. The retained sample has 7,013 observations/361 counties
per corn practice and 4,844/255 per soybean practice. No missing outcome is
filled and no row prediction is released. Because state-year absorption does
not eliminate all time-varying confounding, the resulting coefficients and
contrasts remain historical associations and are barred from causal,
national, damage, or SCC interpretation.

An independent audit rereads the hash-bound panel, reconstructs all eight
crop-by-practice-by-form samples and designs without importing production
estimation functions, reimplements the alternating fixed-effect projection,
solves by reduced QR, and separately forms the county-cluster sandwich. All
324 coefficient, standard-error, probability, contrast, fit, and cluster-count
fields agree within a maximum absolute difference of `1.04e-13` against a registered
`1e-10` tolerance.

## S3. Crop-year alignment

For every grid cell, crop, season, irrigation regime, and harvest year, read
planting and harvest dates from the selected calendar. Resolve cross-year
seasons explicitly and retain date/coverage flags. The current executable
pipeline partitions each valid season into transparent 0–30%, 30–70%, and
70–100% temporal windows; these are **not** claimed phenological stages. The
main specification will replace them with crop-specific establishment,
vegetative, reproductive, and maturity dates only after a licensed, globally
consistent phenology source is selected. Exclude unrecoverable incomplete
windows. No annual country precipitation may be used to stand in for stage
weather.

## S4. Climate features

### S4.1 Climate-to-precipitation projection

The project does not claim or train a new free-standing precipitation
emulator. Direct daily ISIMIP/CMIP fields are the reference. The primary fast
path first computes the exact crop-calendar features from version-pinned daily
ISIMIP3b historical, SSP1-2.6, SSP3-7.0, and SSP5-8.5 fields. For each retained
ESM/member and crop feature, it fits a predeclared smooth response to GMST from
the same CMIP6 realization. Matched FAIR baseline and pulse paths are then
evaluated with the same ESM/member, feature-response draw, calendar, and joint
residual realization, so weather noise is not mistaken for the one-tonne
signal. The direct response difference and centered finite-difference
derivative must converge as pulse size decreases. This is a direct-feature
emulator, not an independent climate model; scenario differences are training
information and never the marginal experiment. The complete design and
provenance contract are in `PAIRED_CLIMATE_FEATURE_DRIVER.md` and
`data/provenance/isimip3b_paired_feature_driver.toml`.

Before fitting, freeze the complete five-ESM/member by four-experiment by
four-variable catalogue product recorded in
`data/provenance/isimip3b_daily_catalog_selection.csv`. The current snapshot
contains 80 public/unrestricted CC0 version-`20210512` datasets. It is a model
selection and storage-planning record, not evidence that the 1.757 TB catalogue
has been acquired. Bounded complete-file `pr`/`tas` coverage now includes
historical plus all three SSPs for all five frozen ESM realizations. Every
available file matches its
version-`20210512` API identity, bytes, and SHA-512 and passes decoded-grid,
units, missingness, physical-value, exact daily-chronology, and historical-
boundary checks. Daily `tas` from the same ESM/member/scenario supplies
cos(latitude)-weighted annual GMST with exact 365/366-day counts, and training
rows share one explicit source and Kelvin value within each cell. Bounded
maize/rainfed smokes over two latitude rows produce 2,744 season records and
8,232 three-window records per future scenario. Additive precipitation/day-
count quantities reconcile exactly, and timing, wet-day, dry-spell, Rx1day,
and Rx5day invariants pass. MRI's exact four-scenario holdout improves 24/44
folds but has a 1.09903 worst RMSE ratio, so it is not promoted. UKESM improves
23/44 folds (median ratio 0.99985; worst 1.03248). The five-ESM joint product
has 565,950 rows and passes 55 whole-ESM and 44 whole-scenario folds; 41 and 36
improve over the cell-mean benchmark, with median ratios 0.99760 and 0.99744
and worst ratios 1.05145 and 1.01605. Independent validation passes, but it
remains only seven nonoverlapping years, one
crop/regime, and two latitude rows. ISIMIP timestamps are normalized
to dates only after complete daily-sequence validation.

Before using FAIR, a bounded numerical pairing smoke aggregates the two-
latitude feature cells, fits one linear feature-on-GMST surface for each of 55
ESM-feature combinations, and reuses the same empirical residual identifier
for baseline and pulse levels. Across 880 rows, zero-pulse and pre-divergence
identity, separate support flags, direct-versus-centered agreement, and
convergence for 0.01, 0.005, and 0.0025 K perturbations pass. Pulse support is
within the bounded aggregate training range for 851 rows, above for 19, and
below for 10. This is an artificial-Kelvin software gate, not a FAIR path or a
selected production emulator.

The actual temperature-delta input is validated separately using the pinned
core GIVE/FAIR manifest and source hashes. Deterministic marginal models for a
2020 CO2 pulse generate 2,204 matched rows spanning 1750--2300 for pulse sizes
0, 0.0001, 0.00005, and 0.000025 GtC. The baseline temperature path is
bit-identical across runs; the zero-pulse and through-2020 paths are identical;
the first nonzero response is in 2021; and normalized responses at the two
smallest pulse sizes agree within the registered tolerance. The largest
0.0001-GtC temperature response is 1.8368e-7 K.

The first alignment sensitivity is fixed in
`config/fair_esm_alignment_sensitivity_v1.toml`. It uses the exact pinned
five-ESM feature product and FAIR paths, defines a 2012--2014 historical
overlap mean separately for each ESM, and evaluates 2012--2300 under both
absolute anomaly mapping and centered-coordinate mapping. With an affine
feature surface, these are algebraic reparameterizations; 127,160 rows pass
common zero-residual, zero-pulse, pre-divergence, direct/centered, support, and
decreasing-pulse gates, with a maximum method disagreement of `4.55e-12`.
Per formulation, mapped temperature support is below/within/above for
44/3,784/59,752 rows, while feature support is below/within/above for
17,764/22,824/22,992 rows. Thus only 5.95% of temperature rows and 35.90% of
feature rows are inside the bounded seven-year training range. This sensitivity
also records model-specific support horizons: the first above-support baseline
year is 2021 for GFDL, 2027 for MPI, and 2033 for IPSL, UKESM, and MRI. It
does not select the overlap window, validate a non-affine response, supply a
stochastic residual path, or authorize production damages or SCC.

The next acquisition is preregistered in
`config/isimip3b_later_century_expansion_v1.toml`: the complete five-ESM by
three-SSP by `pr`/`tas` matrix for exactly 2041--2050 and 2091--2100. The live
version-`20210512` API snapshot pins 60 public/unrestricted CC0 files totaling
124,935,312,957 bytes. Harvest years 2042--2049 and 2092--2099 keep every
cross-year season inside one block. Metadata passage does not substitute for
full checksum/content, same-realization GMST, crop-feature reconciliation, or
whole-ESM/scenario validation; post-2100 FAIR years remain out of support.
The first registered GFDL SSP1-2.6 `pr`/`tas` pair for 2041--2050 has now
passed exact byte, SHA-512, and decoded global 0.5-degree, 3,652-day content
gates. `pr` has zero missing or negative values; `tas` has zero missing values
and produces ten annual same-realization GMST rows. The bounded two-latitude-
row maize/rainfed feature smoke yields 5,488 seasonal and 16,464 stage rows for
2042--2049 and passes exact additive reconciliation. The matching 2091--2100
pair and 2092--2099 bounded feature block pass the same gates. The GFDL
SSP3-7.0 2041--2050 pair and 2042--2049 feature block pass the identical
checks. Their exact-key comparison with SSP1-2.6 uses 5,488 seasonal rows and
finds mean SSP3-7.0-minus-SSP1-2.6 differences of +0.574 C, -18.33 mm
seasonal precipitation, -1.11 wet days, +3.20 maximum dry-spell days, -1.99 mm
Rx1day, and -4.07 mm Rx5day. The registered SSP5-8.5 2041--2050 pair and
bounded feature block pass the same content, GMST, and reconciliation gates.
The SSP3-7.0 and SSP5-8.5 2091--2100 pairs and bounded 2092--2099 feature
blocks also pass. The IPSL-CM6A-LR SSP1-2.6 2041--2050 and 2091--2100 pairs
then pass the same gates under their exact model-specific 12:00 daily timestamp
contract. The IPSL SSP3-7.0 2041--2050 and 2091--2100 pairs and bounded feature
blocks also pass. Both IPSL SSP5-8.5 pairs and bounded feature blocks also
pass, bringing the expansion to 24 of 60 file gates and twelve bounded feature
blocks. The MPI-ESM1-2-HR SSP1-2.6 2041--2050 and 2091--2100 pairs also pass
exact bytes, SHA-512, the model-specific 12:00 3,652-day content contract,
same-realization GMST, and 5,488-season/16,464-stage feature reconciliation.
This raises the registered expansion to 28 of 60 file gates and fourteen
bounded feature blocks. The MPI SSP5-8.5 2041--2050 pair then passes the same
gates. Together with the separately registered MRI SSP1-2.6 2041--2050 block,
the expansion reaches 32 of 60 file gates and sixteen bounded feature blocks
without rerunning a whole-scenario or whole-ESM response. Its exact-key
comparison with MPI SSP1-2.6 finds mean differences of +0.237 C, +17.88 mm
seasonal precipitation, +1.37 wet days, -1.00 maximum dry-spell days, +1.71 mm
Rx1day, and +6.75 mm Rx5day. The MRI SSP3-7.0 2041--2050 pair passes the same
exact-byte, checksum, noon
chronology, decoded-content, same-realization GMST, feature, and reconciliation
gates. Its exact-key SSP3-7.0-minus-SSP1-2.6 means are +0.369 C, -11.02 mm
seasonal precipitation, -1.07 wet days, +0.23 maximum dry-spell days, -0.32 mm
Rx1day, and +0.26 mm Rx5day. This raises tracked progress to 34 of 60 file
gates and seventeen bounded blocks, without completing the MRI scenario or
period matrix. The MRI SSP5-8.5 midcentury pair passes the same frozen-file, content,
same-realization GMST, feature, and reconciliation gates. Its exact-key
SSP5-8.5-minus-SSP1-2.6 means are +0.777 C, -8.81 mm seasonal precipitation,
+0.28 wet days, -2.83 maximum-dry-spell days, -1.50 mm Rx1day, and -2.68 mm
Rx5day. The generic leave-one-scenario-out audit is extended with an explicit
MRI contract and exact two-scenario support flags. Across 181,104 long feature
rows it improves 15/33 comparisons (median RMSE ratio 1.00027; maximum
1.04233), including 4/11 for held-out SSP5-8.5, while 21,236 values (11.73%)
are outside support. These gates raise tracked progress to 36/60 files and
eighteen blocks but remain engineering evidence only. MRI SSP1-2.6 and
SSP3-7.0 end-century pairs subsequently pass exact frozen-file identity, full
decoded-content, same-realization GMST, bounded feature, and stage/season
reconciliation gates. The exact-key SSP3-7.0-minus-SSP1-2.6 comparison
averages +2.928 C, +2.24 mm seasonal precipitation, -0.97 wet days, +2.41
maximum-dry-spell days, +0.25 mm Rx1day, and +1.15 mm Rx5day across 5,488
rows. The MRI SSP5-8.5 end-century pair and bounded block also pass these
gates, raising tracked progress to 42/60 files and twenty-one blocks. The
exact-key SSP5-8.5-minus-SSP1-2.6 comparison averages +4.591 C, -13.23 mm
seasonal precipitation, -2.62 wet days, +5.44 maximum-dry-spell days, +0.75
mm Rx1day, and +0.56 mm Rx5day. Its 181,104-row whole-scenario audit improves
16/33 comparisons (median RMSE ratio 1.00006; maximum 1.06514), including 9/11
for held-out SSP5-8.5, while 27,090 values (14.96%) lie outside exact support.
This mixed, adverse result leaves response, damage, SCC, whole-ESM, and FAIR
feature-support authorization false. The remaining frozen MPI-ESM1-2-HR
SSP3-7.0 mid- and end-century pairs and SSP5-8.5 end-century pair pass the
same exact file/content, same-realization GMST, bounded feature, and
reconciliation gates. The resulting tracked coverage is 48/60 files and
twenty-four blocks. Exact-key SSP3-7.0 minus SSP1-2.6 rain differences are
-4.38 mm at midcentury and -17.02 mm at end century; end-century SSP5-8.5
minus SSP1-2.6 is -13.20 mm. These are support diagnostics only; whole-ESM,
FAIR feature-support, response, damage, and SCC authorization remain false.
The deterministic MPI whole-scenario audits improve 14/33 comparisons at
midcentury (median/maximum RMSE ratios 1.00163/1.05542; 11.65% outside
support) and 15/33 at end century (1.00028/1.09814; 15.24% outside support).
These adverse holdouts do not promote the emulator.
The four-ESM whole-ESM evaluator binds exact GFDL, IPSL, MPI, and MRI source
audits and training hashes. Each period contains 724,416 rows and 44 holdouts.
Midcentury improves 27/44 comparisons (median/maximum RMSE ratios
0.99954/1.00969) with 8.34% outside three-ESM support; end century improves
12/44 (1.00040/1.06362) with 9.47% outside support. UKESM remains absent, so
the five-ESM and FAIR feature-support gates remain false.
The first later-century UKESM1-0-LL pair (SSP1-2.6, 2041--2050) uses the same
version-pinned content validators with an explicit expected hour of 00:00 UTC,
matching UKESM's catalogued daily coordinate; the validators' default noon
contract rejects this pair. Exact bytes/SHA-512, all 3,652 daily timestamps,
946,598,400 finite values per field, same-realization GMST, and the bounded
5,488-season/16,464-stage feature and zero-error reconciliation gates pass.
Coverage is 50/60 files and twenty-five blocks; the remaining UKESM cells and
complete five-ESM holdout remain required before FAIR feature support or any
response, damage, welfare, or SCC use.
The matching 2091--2100 UKESM SSP1-2.6 pair passes the same midnight,
checksum, decoded-content, same-realization GMST, bounded feature, and exact
reconciliation gates. A full rebuild reproduces the GMST and feature Parquet
files byte-for-byte. Separate fixed-slice end-century-minus-midcentury means
are reported only as descriptive climate diagnostics. Coverage is 52/60 files
and twenty-six blocks; four UKESM pairs and the complete five-ESM holdout
remain required before any production use.
The UKESM SSP3-7.0 2041--2050 pair then passes the same exact catalogue,
midnight chronology, decoded-content, same-realization GMST, bounded feature,
and reconciliation gates. Its exact-key comparison with SSP1-2.6 retains
5,488 rows and records quantity, within-season timing/concentration, wet-day,
dry-spell, Rx1day, Rx5day, and mean-temperature differences. Coverage is
54/60 files and twenty-seven blocks; the comparison is not a response or
damage estimate and does not open the five-ESM, FAIR, or SCC gates.
The corresponding UKESM SSP3-7.0 2091--2100 pair passes the identical gates
and exact-key comparison. Coverage is 56/60 files and twenty-eight blocks;
the remaining two SSP5-8.5 pairs are required before the five-ESM rerun, and
no response, damage, welfare, or SCC use is authorized.
The UKESM SSP5-8.5 2041--2050 pair passes the same exact file, explicit-
midnight, decoded-content, same-realization GMST, bounded-feature, exact-key
comparison, and reconciliation gates. Coverage is 58/60 files and twenty-nine
blocks. The 2091--2100 UKESM SSP5-8.5 pair and the complete five-ESM reruns
remain required; no response, damage, welfare, or SCC use is authorized.
The UKESM midcentury three-scenario holdout then applies the same fixed
leave-one-whole-scenario-out estimator and exact support flags to 181,104
rows. It improves 13/33 comparisons over the cell-mean benchmark, with a
maximum RMSE ratio of 1.22120 and 12.21% of held-out values outside support.
This engineering audit does not authorize the emulator or any downstream use.
The complete five-ESM midcentury join then applies the identical frozen whole-
ESM estimator to 905,520 rows and 55 comparisons. It improves 32/55 against
the cell-mean benchmark, with 6.47% of held-out values outside exact four-ESM
support. The UKESM SSP5-8.5 2091--2100 pair completes 60/60 registered file
gates and thirty bounded feature blocks. The same frozen whole-scenario audit
on the 181,104-row UKESM end-century product improves 17/33 comparisons and
places 16.51% of values outside exact two-scenario support. The complete
905,520-row five-ESM end-century join improves 30/55 comparisons; its
median/maximum RMSE ratios are 0.99982/1.01357 and 7.14% of held-out values
are outside exact four-ESM support. FAIR baseline/pulse feature-support
validation remains required before any response or damage use.
We then concatenate the exact-hash early, midcentury, and end-century bounded
products after normalizing only ESM identifier case, yielding 2,376,990 rows
over 23 training years. The previously registered FAIR alignment sensitivity
is rerun without changing its 2012--2014 reference window or pulse paths. Its
127,160 paired rows retain common residual identifiers and pass zero-pulse,
pre-divergence, direct/centered, and decreasing-pulse checks. All feature
levels are within the enlarged bounded envelope; 44 mapped temperature rows
for MPI in 2012 are below its envelope. These checks establish bounded
aggregate numerical support only, not a selected production emulator or any
response, damage, welfare, or SCC estimate.
For IPSL, the exact-key
SSP3-7.0-minus-SSP1-2.6 midcentury comparison finds
mean differences of +0.365 C, +13.22 mm seasonal precipitation, +0.93 wet days,
-1.36 maximum dry-spell days, +2.18 mm Rx1day, and +3.84 mm Rx5day. The matching
end-century differences are +4.146 C, +25.70 mm seasonal precipitation, +2.85
wet days, -2.26 maximum dry-spell days, +3.12 mm Rx1day, and +4.47 mm Rx5day.
These are climate-support diagnostics, not a response estimate. The
matched IPSL SSP5-8.5-minus-SSP1-2.6 midcentury means are +0.607 C, +19.88 mm
seasonal precipitation, +2.07 wet days, -0.77 maximum dry-spell days, +2.01
mm Rx1day, and +3.13 mm Rx5day. The IPSL three-SSP midcentury join contains
181,104 rows. Leave-one-scenario-out GMST adjustment improves 15/33
comparisons (median RMSE ratio 1.00028; maximum 1.02568), including 3/11 for
held-out SSP5-8.5; 20,529/181,104 values (11.34%) are outside the exact two-
scenario envelope. The matching IPSL end-century join improves only 10/33
comparisons (median RMSE ratio 1.00275; maximum 1.27466), including 2/11 for
held-out SSP5-8.5; 30,619/181,104 values (16.91%) are outside the exact
two-scenario envelope. The preregistered GFDL three-SSP midcentury join contains
181,104 rows across 11 feature families. Leave-one-scenario-out GMST adjustment
improves 14/33 comparisons versus the cell-mean benchmark; its median RMSE
ratio is 1.00036, maximum is 1.06410, and the SSP5-8.5 holdout improves only
1/11. Per-cell/family support flags classify 20,562/181,104 held-out values
(11.35%) outside the exact two-scenario envelope. The matching end-century
join has 181,104 rows; GMST adjustment improves 13/33 comparisons (median RMSE
ratio 1.00110; maximum 1.23350), with 27,260/181,104 values (15.05%) outside
the corresponding support envelope. These flags describe climate holdouts,
not FAIR baseline/pulse feature support. A separate audit revalidates
the existing paired FAIR paths and reclassifies temperature support against
the expanded GFDL GMST range (287.659--291.189 K). The mapped baseline is
within that temperature envelope for every year from 2012 through 2300 rather
than only 2012--2020. Whole-ESM and FAIR feature-support gates remain
open, and the adverse scenario result prohibits promotion.

Whole ESMs and whole scenarios, not random years alone, are held out. STITCHES
supplies a sequence-preserving benchmark; MESMER-M-TP plus a published daily
occurrence/amount generator is the fallback if the direct-feature response
fails distributional or convergence gates. MESMER-X remains an independent
Rx1day benchmark. RIG (Huang et al., 2026 preprint) is the closest known joint
daily global temperature--precipitation system under flexible radiative
forcing, but is not executable as of 22 August 2026 because its authors state
that code will be released upon publication. ACE2-SOM is a high-complexity
robustness model rather than the default.

Every candidate must reproduce crop-calendar totals, early/middle/late or
phenological-stage shares, wet-day frequency, consecutive dry days, Rx1day,
Rx5day, heat--precipitation dependence, and spatially synchronized crop-region
events. For SCC use, paired base/pulse runs share stochastic innovations and
must show stable, convergent feature differences as pulse size is reduced.
Aggregate growing-season precipitation results are additionally benchmarked
against OSCAR-crop v1.0; that published model does not validate daily timing
or extreme-weather effects.

Annual precipitation totals receive a second external check against the
USEPA `pattern-scaled-climate-variables` repository at reviewed commit
`dac5503549d5158e0257894012293acff45c0cb4`. Its scripts read precomputed PEEPS
annual precipitation--GMST slopes and aggregate them to 184 GIVE countries
with area, GDP, or population weights. Our exact comparison first reproduces
area-weighted annual country slopes on common units, then checks the three
overlapping primary ESMs (MPI-ESM1-2-HR, MRI-ESM2-0, and UKESM1-0-LL) and the
broader EPA ensemble distribution. Crop harvested-area/value weights remain
the agricultural default. A separate outcome-blind sensitivity may pair FAIR
draws and spatial patterns by 2100 GMST rank, following the logic of the EPA
temperature workflow; same-realization ESM/member construction remains
primary. Neither benchmark supplies daily timing, drought, crop response,
welfare, or SCC evidence.

For each stage, calculate mean temperature; precipitation total; wet-day
count; maximum consecutive dry days; Rx1day and Rx5day; and, after a specified
method, water balance. Calculate maximum-temperature days and degree-days only
for explicitly registered crop/specification thresholds. Stage heat-day and
degree-day totals must reconcile additively to the season; the stage-day-
weighted maximum-temperature mean must reconcile to the seasonal mean.
For every adjacent ordered threshold pair, require weakly decreasing hot-day
counts and require the degree-day difference to lie between the threshold gap
times the hotter-day and cooler-day counts. These algebraic checks detect
corrupt summaries but do not choose a response threshold. Convert
precipitation flux to mm/day using source time
bounds. Define thresholds and anomalies relative to a fixed historical
grid-crop-stage baseline. Store units, baseline interval, input version, and
missing-data flags. Compute nonlinear metrics before geographic aggregation.
The parsimonious direct-weather reference contains joint temperature and
crop-calendar seasonal precipitation quantity. Timing/distribution terms are
candidate extensions retained only for robust, stable incremental outer-
holdout value. SPEI and PDSI/scPDSI climatic-water-balance indices are serious
competing drought representations, as is the soil-moisture family; none is a
term automatically stacked with the underlying precipitation and temperature
variables. [Fishman
(2016)](https://doi.org/10.1088/1748-9326/11/2/024004) motivates separating
rainfall quantity from occurrence, and [Lesk, Coffel, and Horton
(2020)](https://doi.org/10.1038/s41558-020-0830-0) motivates testing rainfall-
intensity distributions; neither determines the global response form.

Predictive comparisons may give every moisture family the same predeclared
nonmoisture heat controls. Because PDSI/scPDSI and SPEI already incorporate a
temperature-dependent atmospheric-demand term, coefficients from a model that
also contains temperature or heat cannot be interpreted as an additive
precipitation-versus-temperature decomposition. A later causal attribution
design must state which drivers are held fixed and use a symmetric or other
pre-specified path decomposition; component effects are never summed across
alternative moisture families. For every future paired climate draw,
calculate the corresponding drought-index change directly, then use a
pre-specified symmetric decomposition when a precipitation versus
temperature/PET attribution is required.

For the historical climatic-index benchmark, monthly CRU scPDSI is aligned to
the same crop-year windows by day-weighting each monthly value over its exact
overlap with a stage. Retain stage mean, minimum, monthly-index day-equivalents
at or below the registered threshold, the threshold itself, and covered-day
count. These equivalents repeat a monthly index value over its overlapping
calendar days and are not observed daily drought occurrences. Require
exact grid-centre correspondence after longitude normalization, complete
monthly coverage for every stage, and a covered-day count equal to stage
length. This benchmark tests historical response and coverage only; future
SCC runs must derive their drought indices from matched baseline and pulse
climate paths and must not project observed CRU scPDSI.

The global historical implementation runs in resumable latitude partitions
with `scripts/build_stage_scpdsi_partitions.sh`, validates every partition,
and refuses to combine anything other than the declared complete partition
count. `scripts/allocate_irrigation_scpdsi_basis.py` joins complete stage
records to the rainfed and fully irrigated calendar panels, drops an entire
crop-grid-year key if either regime lacks index coverage, and records observed
and unobserved exclusions separately. Within each regime it constructs stage
and seasonal day-weighted means, minima, monthly-index threshold
day-equivalents, and threshold fractions. Only then does it apply fixed MIRCA-2000 area shares to the
single aggregate GDHY outcome. The 16-column candidate contains no raw
precipitation, temperature, CDD, or wet-extreme term and is labeled as a
non-stacked climatic-water-balance family.

Each partition manifest binds its output hash to the current raw CRU and crop-
calendar hashes, crop, regime, years, latitude slice, stage fractions, and
calendar fields. The combiner requires gap-free latitude coverage.
`scripts/validate_irrigation_scpdsi_basis.py` verifies that manifest chain plus
source-panel, derived scPDSI, weight, and audit SHA-256 values and fully
recomputes the output from the derived stage tables. This is not described as
an independent recomputation of every monthly metric from raw CRU. It requires
exact false flags for fitting, causal interpretation, future projection, and
SCC use. The convenience wrapper
`scripts/run_scpdsi_candidate_chunk.sh` composes partitioning, combination,
regime-first basis construction, weighting, and validation. The 1982--1989 run
validates 240,784 maize rows with 115,758 positive outcomes and 176,537 soybean
rows with 47,653 outcomes; the 2012--2016 run validates 150,490/59,772 and
110,336/26,601. The -2 threshold used in these runs is
a diagnostic construction setting, not a selected response threshold. These
panels permit a common-support predictive comparison under the separate,
coefficient-suppressing drought-family diagnostic contract. That design is
specified and its downstream historical predictive comparison has now been
run and validated; the panels themselves do not estimate a relationship.

`scripts/build_direct_scpdsi_common_support.py` implements that support
assembly without fitting. It takes the validated candidate tables, intersects
whole `harvest_year, lat, lon_360, crop` keys, and emits two deterministically
ordered tables rather than one stacked predictor matrix: a 54-feature
direct-weather view and a 16-feature scPDSI view with identical keys and
outcomes. The four current bundles have the following common rows/observed
outcomes and direct-only dropped rows/observed outcomes: maize 1982--1989,
240,784/115,758 and 24,744/1,921; soybean 1982--1989,
176,537/47,653 and 14,935/269; maize 2012--2016,
150,490/59,772 and 15,465/1,046; and soybean 2012--2016,
110,336/26,601 and 9,334/147. scPDSI-only drops are zero rows and zero observed
outcomes in each case.

`scripts/validate_direct_scpdsi_common_support.py` verifies input and output
SHA-256 values, validates each view independently, rereads the two immediate
candidate inputs, and exactly recomputes the views and support audit. It does
not rerun the upstream allocators from raw climate, crop-calendar, yield, or
irrigation-share sources, and it does not bind upstream validation receipts.
Running those upstream validators and retaining their receipts is therefore
an explicit external prerequisite. Boolean gates prohibit stacking, fitting,
coefficient output, causal interpretation, future projection, damage, and SCC
use. The resulting files are data-only comparison inputs, not estimates or
results. Seasonal quantity remains the parsimonious direct-weather reference;
distribution requires robust stable incremental outer-holdout value, and
direct weather, scPDSI/PDSI, SPEI, and soil-moisture families compete
mutually exclusively.

The registered direct-weather--scPDSI diagnostic binds its configuration,
four common-support view pairs, heat-control bases, upstream allocation
audits, validation receipts, and source hashes before fitting. It checks exact
common keys and outcomes, irrigation weights, the 1 mm wet-day threshold used
in direct weather, the -2 scPDSI threshold, and equality of stage-temperature
controls across families. It forms only consecutive-year log-yield
differences and never bridges a missing year. This yields 209,036
crop-grid-year pairs: 101,157 early-period and 45,633 later-period maize pairs,
and 41,678 early-period and 20,568 later-period soybean pairs.

Five mutually exclusive predictor sets are compared: nonmoisture controls;
controls plus seasonal log precipitation; controls plus seasonal mean scPDSI;
controls plus a seasonal scPDSI summary; and controls plus crop-stage scPDSI
means. Each fit standardizes continuous predictors using the training sample
and estimates ordinary least squares separately by crop. Evaluation reports
RMSE, MAE, and R-squared for five deterministic hashed, unbuffered 5-degree
spatial folds; one retrospective early-to-later split; and five crop-specific,
endpoint-purged stress subsets. Crop-grid-year pairs receive equal weight. The
protocol has no model-selection rule and emits neither coefficients nor
row-level predictions.

Across the five spatial folds, seasonal quantity has the lowest mean RMSE for
maize (0.288589, versus 0.290401 for controls and 0.288697 for the best scPDSI
specification) and soybean (0.209670, versus 0.211282 and 0.210183). It lowers
RMSE in every crop-fold comparison, but gains are below 1% and MAE results are
less uniform. The seasonal scPDSI summary is lowest-RMSE in all five maize
stress subsets; it is not the stable general winner. The validator exactly
recomputes the declared inputs, splits, refits, and aggregate metrics, and a
separate clean-room implementation reproduces all 110 metrics with zero
numerical discrepancy.

This comparison remains a nonproduction historical predictive diagnostic.
Spatial folds are unbuffered and equal-pair weighting is not a
production-weighted welfare estimand. A separate registered sensitivity pools
the five spatial-fold OOF errors and resamples crop-specific 10-degree cells
5,000 times, keeping all years and both episodes within a cell together. Maize
has 126 occupied cells (inverse-Herfindahl effective count 65.26) and soybean
56 (26.66). It reports paired percentile intervals for candidate-minus-
reference RMSE and MAE while emitting no row scores or draws. All 12
scPDSI-versus-direct intervals include zero. The sensitivity is conditional on
the fixed OOF fits: it does not refit training samples, define a random target
population, account for model selection, or model dependence beyond the cell
boundary. Because the CRU product calibrates scPDSI using the complete
1901--2025 record, the early-to-later score is retrospective rather than
prospective. Buffered or leave-region-out validation, common heat thresholds,
SPEI and soil-moisture competitors, production weighting, frozen drought-index
calibration, and causal response identification remain open gates. No result
in this diagnostic is a climate-to-drought projection, damage estimate, or SCC
input.

## S5. Estimation

Fit the candidate responses on crop-grid-year observations with grid/crop
fixed effects and flexible year effects. The reference uses joint temperature
and crop-calendar seasonal quantity; direct-pattern extensions and separate
PDSI/scPDSI, SPEI, and soil-moisture families use identical outer splits.
Pre-register feature selection, splines, and thresholds. Report null, unstable,
and worse performance, permit the parsimonious reference or a drought-index
family to lead, and never select by SCC magnitude. Pool crop seasons only with pre-specified
crop interactions or a hierarchical partial-pooling structure; a combined
panel is never authority to impose common weather slopes across maize, rice,
wheat, and soybean. Cluster or model spatial dependence. Include
irrigation-specific response-basis exposure only through the one-outcome
aggregation contract; do not create irrigation outcome strata from aggregate
GDHY yield. The outcome file is matched to the calendar at the crop-season level according to the locked crosswalk in
`data/provenance/crop_calendar_gdhy_crosswalk.md`; generic GDHY aggregate
directories are not substitutes for an identified season. GDHY does not
identify irrigated and rainfed yields separately. Early historical pilots
therefore used rainfed-calendar exposure only. Corrected minimal maize and
soybean diagnostics now construct response-basis columns within each calendar
regime and combine them with fixed MIRCA-2000 area shares into one exposure row
for the aggregate GDHY outcome. This does not estimate irrigation-stratified
yields or regime-specific response slopes, and the full production basis
remains unfitted. When both calendar regimes are available, an
independent, outcome-blind fixed-vintage crop-grid area-share source must weight their climate
features into one exposure vector for the single GDHY crop-season-grid-year
outcome. Shares are fixed across outcome years, cover every declared regime,
and sum to one. Missing shares or exposure rows are not renormalized, and the
same observed yield is never entered as separate rainfed and irrigated
observations. This historical exposure-allocation weight is distinct from the
regional baseline crop-value weights used later for welfare aggregation. CO2
is an explicitly provenanced scenario term; it cannot be separately added
after a response that already includes it.

The allocation order is part of the estimand. For regime-specific weather
history `W_r`, construct every nonlinear response-basis column `B(W_r)` first,
including log/spline/threshold terms, CDD, Rx1day/Rx5day, drought indices, and
temperature--water interactions. Then construct the one-outcome exposure
`Z = sum_r s_r B(W_r)` with fixed MIRCA area shares. Averaging primitive
weather and then applying `B` is prohibited: nonlinear transforms do not
commute with weighting, and post-aggregation interactions introduce
cross-regime products. The proposed common-slope log-yield equation is an
aggregate reduced form, not an identified decomposition of latent rainfed and
irrigated yields. Area shares are observable exposure weights; exact
log-change production weights would require independent regime-specific
baseline yields, which GDHY and MIRCA do not supply. Revenue weights enter only
the later welfare aggregation. The full equation, identification restrictions,
and sensitivity benchmarks are specified in
`IRRIGATION_AGGREGATE_ESTIMAND.md` and
`config/irrigation_aggregate_estimand.toml`. The first primitive-weighted
primitive-weather-weighted aggregate-regime diagnostic outputs violate this
order and are withdrawn. A corrected
minimal predictive rerun uses an explicit contract-aware prebuilt-basis mode;
that diagnostic mode does not freeze or fit the complete production response.
The separate direct-pattern candidate builder extends the same allocation
order to 54 basis columns covering seasonal and three-window rainfall amount,
normalized stage shares/timing/concentration, wet-day occurrence and
conditional intensity, CDD, Rx1day, Rx5day, mean temperature, and
temperature-by-log-amount terms. It rechecks stage-to-season days,
precipitation, wet-day counts, and extreme bounds before allocation. The 1 mm
wet-day definition is carried as an explicit candidate/QA setting, and the
output remains `fit_authorized=false`; heat and alternative drought families
are joined only as separately validated candidate families.

Support is audited with welfare-relevant denominators before aggregation.
`scripts/audit_mirca_welfare_support.py` reports positive MIRCA harvested area
inside cells with any observed outcome and with a consecutive-yield pair,
separately for irrigated and rainfed area. It also reports an explicitly
conditional MIRCA-area-times-same-vintage-GDHY-yield proxy and the MIRCA area
over which that proxy is undefined. Revenue coverage is not inferred without
a pinned spatial price/value source, and crops are never pooled using cell
counts or a fabricated common price. For the current 1982--1989 pair support,
area coverage is 79.017% for maize and 89.288% for soybean; this partial support
must be revisited on the complete historical panel before welfare calibration.

The machine-readable production design registry is
`config/primary_response_spec.toml`. It is explicitly not frozen and does not
authorize fitting. Every production design exercise must compare the
parsimonious seasonal-amount reference against pre-registered candidates for
crop-window amount; normalized stage distribution/timing; wet-day frequency;
conditional wet-day intensity; CDD; Rx1day; Rx5day; mean temperature;
crop-specific heat extremes; and registered temperature--precipitation
interactions. “Retain” means that each concept enters a pre-registered
candidate comparison; it does not require placing collinear encodings or
alternative drought representations in one unrestricted regression. Added
distribution terms are retained only for robust incremental held-out value.
The direct precipitation-pattern family is compared separately with serious
PDSI/scPDSI and SPEI climatic-water-balance candidates and with soil-moisture
families. The threshold registry is
empty until primary evidence or a documented training-only procedure supports
crop/specification choices.

The registered primary source is the earliest MIRCA-OS v2 vintage (2000),
held fixed across the 1981--2016 outcome panel; 2005, 2010, 2015, and 2020 are
separate fixed-vintage sensitivities, not time-varying adaptation. The 2000
maize and soybean weights match 97.79% and 97.99% of observed-yield cells in
the current 1982--1989 panels. Unmatched cells are disclosed and excluded
before estimation, never assigned a national mean or renormalized. MIRCA's
annual rice and wheat maps do not identify GDHY's two rice seasons or its
spring/winter wheat outcomes. The builder exports those provisional mappings
with `production_eligible=false`, and the allocator fails if they are supplied
to a production panel. A season-resolved crosswalk is therefore an open input
gate for rice and wheat. For rice, the only current candidate is the
publisher's 5′ monthly `Rice1`/`Rice2`/`Rice3` product, aggregated by summing
hectares and reconciled to the annual Rice map under the protocol in
`MIRCA_SEASON_CROSSWALK_GATE.md`. The archive contains all 30 expected names,
but nine 2005--2015 rainfed files incorrectly declare source year 2020 and are
blocked. The six-file 2000 implementation passes metadata, grid, month,
nonnegativity, and aggregation checks, but the seasonal
maxima exceed the released annual Rice areas by 64,247.23 irrigated ha and
5,302.04 rainfed ha. Because both predeclared reconciliations fail, no rice
weight table is promoted while publisher generation logic is investigated.
MIRCA's numeric wheat subcrops do not provide a documented spring/winter
identity, so no timing-based inference is allowed.

GDHY's aligned construction can clip a negative aligned estimate to zero.
The join preserves the original value in `gdhy_yield_raw_t_ha`, flags it in
`yield_nonpositive`, and sets the log-response outcome to missing. Negative
source values fail, and no arbitrary positive offset is introduced.

Annual source support is audited before estimation with
`scripts/audit_gdhy_annual_support.py`. A fresh official archive download and
the local archive have identical SHA-256 values, every ZIP member passes CRC,
and extracted members match independently calculated hashes. The verified
source nevertheless loses 1,791 maize-major and 596 soybean positive cells in
2015 and restores all of them in 2016. These values are neither imputed nor
relabeled. The unbalanced consecutive-positive-pair panel is primary. A
separate complete-positive-support sensitivity retains cells positive in every
declared year, records the resulting sample loss, and warns that this
conditioning can select a nonrepresentative subset. Excluding transitions that
touch the unexplained support-loss endpoints is a separate publication
sensitivity pending clarification from the data producer.

## S6. Adaptation

`fixed` keeps the observed response. `trend` and `upper` apply transparent,
crop-specific time-varying loss multipliers from
`config/adaptation_scenarios.toml` before crop aggregation; they are
sensitivity scenarios, not claims of forecasted adaptation. Adaptation cost
shares default to zero pending empirical cost estimation and are reported as a
limitation. Positive crop losses are attenuated; modeled benefits are not
erased.

## S7. Model integration and SCC

The isolated `CropResponseAggregation` component retains crop/season-specific
features and coefficients through response evaluation. It accepts exactly one
declared water-stress family, applies crop-specific adaptation, and aggregates
with fixed baseline agricultural-value shares. Production runs require those
shares to cover the complete regional agricultural value pool; partial-
coverage runs are diagnostics and cannot produce an SCC. `JointAgriculture`
then retains baseline income, population, agricultural-share, and 16-FUND-
region inputs and outputs `agcost` in billion 2005 USD/year. It replaces
`MooreAg.Agriculture`; never instantiate both. Matched baseline/pulse climate
paths propagate through the crop-specific joint response and one welfare
mapping. The global SCC is calculated from the discounted difference using
GIVE's established marginal-damage method.

The executable integration gate inspects Mimi's parameter-connection graph
before each paired marginal run. It requires exactly one internal producer for
`DamageAggregator.damage_ag`, identifies that producer as
`JointAgriculture.agcost`, and rejects an instantiated component named
`Agriculture`. Synthetic tests retain missing-source, wrong-source, and
coexistence failures. The unmodified GIVE model is a negative control and is
rejected because `Agriculture.agcost` supplies `damage_ag`. This establishes a
topological accounting condition only; it does not validate response skill,
welfare calibration, crop coverage, future support, matched identifiers, or a
paired SCC result.

The executable installer preflights the legacy agriculture component, the
regional population/GDP aggregators, baseline agricultural-value inputs, crop
order, and component start year before mutation. It then deletes the MooreAg
component and its unshared parameters, adds `CropResponseAggregation` and
`JointAgriculture`, reconnects the socioeconomic inputs and `damage_ag`, and
sets the declared sector flags explicitly. An executed control applies this
procedure to the unmodified GIVE model using synthetic zero-response inputs.
All externally supplied response and adaptation arrays use GIVE's full
1750--2300 time dimension even though the installed components begin in 2020;
the pre-2020 rows are not evaluated by those components. For every active year,
the control requires complete crop and regional outputs, unit crop-value
coverage, and zero `JointAgriculture.agcost` and aggregated agriculture damage.
It is not a paired marginal experiment or an empirical damage result.

We executed this control using the archived GIVE environment: Julia 1.6.4
x86_64 under Rosetta and the repository-level `.julia_depot_1_6`. A separate
native Apple-silicon Julia 1.8.5 attempt failed before executing the harness
because the archived dependency lock requested an Electron artifact that is
not available for `aarch64-apple-darwin`. We therefore claim successful
execution only for the archived x86_64 environment and report native-ARM
portability as an unresolved reproducibility limitation.

The paired component-output gate is applied after the crop response and
agriculture replacement components execute. For crop-level raw and adapted
loss arrays and regional loss and monetary agriculture arrays, it requires
matched dimensions, finite numeric values, and equality before the registered
first-divergence year. The modeled horizon must contain at least one year
before and at/after that year. A separately declared zero-pulse control must
agree for every modeled year. The gate does not require a nonzero response to
a nonzero pulse and therefore does not turn an integration check into an
implicit statistical-significance or extrapolation rule.

Before model wiring, the long-form response bundle is checked against the
frozen crop and FUND-region orders. Every draw/year contains the complete
region-by-crop product for baseline and pulse; FAIR, climate-member,
socioeconomic, calendar, response, adaptation, weight, and welfare identifiers
match within each pair; coefficients and adaptation settings match; weights
sum to one and remain fixed across scenario and time within a draw; and all
features are identical before the registered first-divergence year. Historical
support flags remain scenario-specific. This is a schema/conservation gate,
not evidence that a response clears empirical validation.

## S8. Uncertainty and sensitivity

Jointly sample climate model/member/scenario, weather product/bias adjustment,
crop calendar, response coefficients, crop-model structural benchmark,
socioeconomics, adaptation, welfare mapping, and discounting. Report
distributions and variance/decomposition diagnostics, not only means.

## S9. Validation and exclusion checks

Require held-out space, time, and extreme-year validation; calendar/date and
coordinate checks; coverage/no-infill checks; nonnegative precipitation and
integer-count checks; zero-feature/zero-loss tests; regional-weight
normalization; and matched draw IDs for pulse/base. FAOSTAT is an aggregation
check, not independent external validation of GDHY. The U.S. county extension
uses documented NASS yields and U.S. Drought Monitor county-week area shares
as an external observed validation layer, after an explicit crop calendar and
spatial-measurement route; it is not a source of global future climate
features. County yield is not labeled rainfed without crop-specific irrigated
area evidence: the primary sample applies a predeclared high-rainfed-share
threshold to the 2017 Census crop share, reports 2012/2022 vintages and
10/20/30 percent thresholds, and treats mixed counties separately. A distinct
regional validation uses only crop--county--years with positive numeric yields
reported under both production practices; it does not substitute for the
national aggregate panel or identify a global irrigation response.
For direct daily weather, CDD, Rx1day/Rx5day, wet-day occurrence/intensity,
timing concentration, heat, and nonlinear response terms are built within
weather-grid cell and crop-calendar class before county-polygon primary or CDL
crop-pixel sensitivity averaging. All-classes wheat is combined across winter,
spring, and durum only after independent class shares pass their gate.
Calculating these nonlinear metrics after county-mean weather aggregation is
an explicit invalid-order failure, not an alternate specification.
The competing PDSI/scPDSI and SPEI panels use the same crop calendars,
irrigation classifications, outcomes, and outer folds so their predictive
performance is directly comparable; they are not appended to the direct-
weather model by default.

The drought pathway contains two separately validated estimands. The
historical response estimand compares crop outcomes with a declared drought
exposure; the climate estimand compares that same exposure under matched
baseline and CO2-pulse climate paths. The current CRU scPDSI panels and their
direct-weather common-support views prepare only a historical predictive
comparison. They do not estimate either a causal drought--yield response or a
climate-induced drought increment. A future SCC pathway requires both links,
plus the single welfare mapping, to pass independently. It may not substitute
observed CRU scPDSI or USDM histories for the matched future drought path.

USDM county-week preparation preserves five-digit GEOIDs, rejects duplicate
keys and category shares that do not sum to 100, and requires each map date to
fall inside its declared validity interval. A documented state/crop/harvest-
year calendar then clips the weekly validity intervals to each crop season and
calculates day-weighted category shares, severity-area means, and D0+/D1+/D2+
area-equivalent days. Missing, gapped, or overlapping daily coverage fails;
planting and harvest dates are never inferred. The output remains explicitly
historical-validation-only and is not a future climate or SCC input. Before
constructing any estimation panel, a counts-only county-year coverage audit
requires an explicit NASS-commodity-to-calendar-crop mapping, a single yield
unit, unique keys, and the validation-only/SCC-ineligible exposure labels. It
retains suppressed NASS outcomes in the coverage denominator, reports overlap
for reported yields separately, and emits no yield values or response estimate.
Keep crop inundation in agriculture and exclude it from the future
infrastructure module; exclude coastal surge/SLR impacts already addressed by
CIAM.

The executable internal predictive comparison uses only outcome-independent
holdout labels. Within each crop, consecutive-year differences in log yield
are regressed on corresponding weather-feature differences, eliminating
time-invariant grid productivity. Seasonal precipitation-only, seasonal
temperature--precipitation, and three-window joint specifications are scored
on leave-one-spatial-fold-out predictions, the registered final-year block,
and pairs containing a registered climate-extreme endpoint. RMSE, MAE,
correlation, predictive R-squared, and improvement over a zero-yield-change
benchmark are reported; response coefficients are not exported. This is an
internal predictive diagnostic, not causal identification, independent
external validation, or authority to construct SCC inputs.

The diagnostic feature list is not the production registry. It omits
wet-day frequency, conditional intensity, Rx5day, heat, and the climatic-index
and soil-moisture alternatives; its three window totals only partially encode
the normalized timing/distribution estimand. In the response audits reported
before the split revision, temporal and climate-extreme labels were applied to
adjacent first-difference pairs without an endpoint purge. A test pair could
therefore share one underlying level-yield endpoint with a training pair even
though its climate labels were outcome-blind. Those numerical outputs are
legacy dependent stress tests and are stale after the hashed specification
changes. Before production model selection, purge from training every pair
containing either crop/grid/year endpoint used in the temporal or extreme test
set, document the resulting support loss, verify endpoint disjointness
mechanically, and rerun all panels. Spatial grid-block splits remain disjoint
by construction. A purged predictive pass remains noncausal and SCC-ineligible.
The revised evaluator and audit validator now enforce zero endpoint overlap
and pass synthetic tests. Corrected 1982--1989 and 2012--2016 MIRCA-2000 maize
and soybean minimal diagnostics pass under the new hash; other crop-period
panels remain stale or pending. The production cell fixed effect is
latitude--longitude--crop/season, not irrigation, because the outcome is
aggregate. The level fixed-effects versus first-difference design and the
appropriate common, crop-specific, or regional year-shock controls remain
unfrozen identification choices.

A distinct version-1 precipitation-distribution screening contract operates
on the validated 54-column basis-before-weighting tables. Every nested model
contains the same three crop-window mean-temperature controls. The reference
adds seasonal `log(1 + precipitation)` quantity; comparison models then add,
separately and jointly, (i) precipitation timing centroid and concentration
HHI, (ii) stage wet-day frequency and conditional wet-day intensity, (iii)
stage maximum-dry-spell fractions, and (iv) stage Rx1day and Rx5day. The three
stage precipitation shares are omitted when centroid and HHI are present to
avoid exact share-sum/timing redundancy. The 1 mm wet-day threshold and
0--30/30--70/70--100 percent windows are locked diagnostic QA choices, not
selected production thresholds or observed phenological stages. The source
tables remain `fit_authorized=false`; a separate contract permits transient
held-out prediction while suppressing coefficients and forbidding causal,
production-model, response-draw, damage, and SCC use. The independent
validator verifies source and specification hashes, reruns the complete
diagnostic from those locked tables, and recursively compares every reported
field with the fresh result. In the eight-year panels, the union of within-cell
95th-percentile CDD and Rx1day endpoint labels marks approximately 47% of
consecutive pairs, so it is reported as a retrospective high-tail stress split
rather than rare-event validation. Five-degree blocks are hash-assigned
without a geographic buffer and therefore do not constitute leave-region-out
extrapolation.

The later-period diagnostic is pinned separately by
`config/precipitation_distribution_diagnostic_2012_2016.lock.toml`, which
records both panel and allocation-audit SHA-256 hashes, crop, years, row counts,
and positive-outcome counts. Independent validation recomputes all model
predictions and metrics from the locked Parquet sources. The screen contains
46,434 maize and 20,682 soybean consecutive pairs. No distribution extension
improves seasonal quantity in all three holdouts for either crop: all maize
extensions worsen spatial and temporal RMSE; every soybean extension worsens
temporal RMSE. The only maize improvement is 0.000044 RMSE for timing/HHI in
the high-tail split. Soybean gains are split-specific (0.001516 for dry spells
spatially and 0.001366 for occurrence/intensity in the high-tail split). The
all-distribution model worsens temporal RMSE by 0.004826 and 0.003491 for maize
and soybean. Because the maize temporal zero-change RMSE is lower than every
fitted candidate, that adverse benchmark comparison is retained.

The 2012--2016 high-tail labels contain 66.15% of maize pairs and 66.39% of
soybean pairs and leave only 4,563 and 1,774 training pairs; they are not
rare-event validation. These short-panel screens also have no paired
confidence intervals or multiple-comparison adjustment. A separate
three-model minimal-basis complete-positive-support sensitivity retains
91.23% of maize pairs and 94.23% of soybean pairs and ranks seasonal joint
temperature--quantity first in all six crop-by-holdout comparisons. The
seven-family distribution diagnostic has not been rerun on that selected
subset. GDHY is a modeled, observation-aligned gridded yield product rather
than direct farm observations, and both later temporal transitions touch its
unexplained 2015 support discontinuity. The two panels are therefore reported
as predictive screening and sample-composition evidence only.

When daily climate coverage crosses source-file boundaries, the builders take
an ordered list of NetCDF inputs, require identical latitude/longitude grids and units,
and verify one strictly increasing daily time axis with neither duplicated nor
missing boundary dates. They retain only the years that can enter the requested
harvest-year seasons. Period panels must have an identical schema, nonoverlap
on crop-grid-year keys, and the exact declared contiguous harvest-year set.
The response audit records that set, and the validator checks it whenever an
expected start and end year are supplied. These are coverage and reproducibility
gates; they do not strengthen causal identification.

Multi-crop audit reporting is fail-closed. The audit validator binds the JSON
artifact to the SHA-256 of the frozen response specification; requires the
explicitly declared crop-season set and every crop-by-model-by-holdout result;
checks positive and reconciled level, observed, pair, split, and spatial-fold
row counts; requires finite metrics and design diagnostics; and independently
recomputes improvement over the common zero-change benchmark. It emits a
machine-readable diagnostic summary while labeling any lowest-RMSE model as
descriptive only. Missing crops, duplicate results, stale configurations,
inconsistent benchmark values, nonfinite metrics, and failed arithmetic stop
the reporting workflow.

The future-feature multi-crop support audit is separately frozen in
`config/isimip3b_ukesm_multicrop_midcentury_support_v1.toml`. It binds the
exact UKESM SSP1-2.6 and SSP5-8.5 source-provenance receipts and six crop-
calendar files by SHA-256. For each declared crop/regime it requires the exact
2042--2049 year set, declared row counts, crop and irrigation labels, three
stage IDs, finite/nonnegative precipitation features, bounded wet-day and
maximum-dry-spell counts, Rx1day/Rx5day ordering, identical scenario keys, and
independent stage-to-season reconciliation. The receipt reports paired
quantity, timing, dry-spell, and extreme-rain summaries and an exact-key
soybean calendar sensitivity. It explicitly sets whole-scenario, whole-ESM,
causal-yield, irrigation-treatment, damage, and SCC gates to false.

Before inspecting a real fit, the next feature-response family is fixed as a
ridge-regularized continuous pathway basis. It contains same-realization GMST
anomaly and one-year change, years since 2020, a quadratic GMST term, and
GMST-by-change and GMST-by-time interactions, with partially pooled ESM
intercept/slope deviations. Scenario identity is not a predictor. Penalty
selection and standardization occur only inside training folds; outer whole-
ESM and whole-scenario holdouts remain untouched. The preregistered promotion
rule requires every feature family to pass both holdout types, maximum and
median RMSE ratios no greater than 1.0 and 0.995, respectively, complete actual
FAIR baseline/pulse support, exact zero/pre-divergence identity, decreasing-
pulse convergence, and human review. The validated contract is not a fitted or
promoted response.

In the first real run, lambda selection is nested within each outer holdout and
shared across grid cells separately by feature family. First years of each
discontinuous climate block are excluded from one-year GMST changes. The 88
outer comparisons improve on the cell-mean benchmark 71 times; median and
maximum RMSE ratios are 0.99443 and 1.00703. Eighty-five predictions violate
nonnegative feature bounds. Because the locked maximum, every-feature, and
physical-bounds rules fail, actual FAIR pulse evaluation and promotion are not
performed.

Before examining a successor fit, we froze positive log links for rainfall,
count, dry-spell, and extreme features; bounded logits for timing metrics; and
a centered-log-ratio link with shared regularization for the three stage
shares. Nested selection and holdout scoring are performed after inverse
transformation on the original scale. The locked run improves 34/88
comparisons, with median/maximum RMSE ratios 1.00775/1.13855. It has zero
negative or above-one predictions and maximum stage-sum error `3.33e-16`, but
the maximum, median, and every-feature predictive criteria fail. Actual FAIR
pulse evaluation and promotion are not performed.
An exact-key comparison against the rejected identity-link candidate finds
only 9/88 lower physical-link RMSE ratios, zero rescued benchmark failures, and
37 lost identity-link successes. The comparison is diagnostic only and does
not select a third candidate.

The subsequent literature-constrained review selects RIME-X v1.0 (Schwind et
al., 2026) as a published direct-indicator benchmark, not as a promoted third
fit. The method represents indicator distributions on 0.1 K warming-level and
101-quantile maps and interpolates them onto simple-climate-model temperature
paths. Its exact paper archive and the project contract are version-pinned.
Only independently implemented synthetic interpolation mechanics were tested:
within-feature common random numbers, separate support flags, zero-pulse and
pre-divergence identity, rejection of extrapolation, and three decreasing
pulse sizes pass. A real fit is withheld because the current daily-derived
feature artifact contains three discontinuous short blocks rather than the
published 21-year smoothing support, and univariate quantile maps do not
preserve the joint rainfall, timing, persistence, extremes, heat, and drought
dependence required by the crop response. Whole-ESM, whole-scenario, actual
FAIR, crop-response, damage, and SCC gates therefore remain closed.
The first preregistered contiguous-support pilot fixes GFDL-ESM4 `r1i1p1f1`
under SSP1-2.6 and daily `pr`/`tas` for 2031--2060. Cross-year crop seasons
then yield 28 consecutive feature years (2032--2059), of which 2042--2049 have
ten real feature years on each side for a centered 21-year mean. Endpoint
padding and cross-gap smoothing are forbidden. All six files pass complete
source/content validation; the eight centered outputs retain same-realization
GMST and reconcile additive stage/season precipitation and wet-day means to
numerical precision. This pilot remains insufficient
for whole-ESM, whole-scenario, multi-crop, joint-dependence, FAIR, response,
damage, welfare, or SCC promotion.
The complete 2031--2060 input has 10,958 complete midnight daily steps per
variable. The bounded panel contains 19,208 seasonal plus 57,624 stage rows
for every harvest year 2032--2059 and passes exact unsmoothed reconciliation.
The centered operation emits only the eight complete registered windows.

The joint-dependence extension is registered before fitting. It uses ECC-Q
(Schefzik et al., 2013) to reorder 51 separately mapped marginal samples by
the empirical ranks of complete climate-model templates. A template is one
indivisible ESM--member--scenario--center-year field across cells, crops,
irrigation regimes, stages, and linked features; held-out ESM or scenario
templates never enter training. Physical coordinates use log seasonal rain,
epsilon-open logits for wet frequency, dry-spell fraction, Rx5/total, and
Rx1/Rx5, identity temperature, and two reversible additive-log-ratios for
stage-rain composition. Derived timing and concentration are reconstructed,
not sampled independently. The synthetic gate reproduces marginal multisets
and rank correlations exactly and preserves the rainfall ordering and unit-sum
composition. The current eight-template pilot is below the fixed 51-template
minimum; no empirical coupling, FAIR feature response, or SCC use is opened.

Before constructing additional contiguous features, a separate contract fixes
the complete Cartesian product of maize, soybean, first- and second-season
rice, spring wheat, and winter wheat with `noirr` and `firr` calendars on the
same bounded GFDL realization. All 12 calendar hashes, valid-cell counts,
2032--2059 annual support, 2042--2049 centered support, and same-realization
GMST identity are required. The audit passes 214,928 seasonal and 644,784
stage rows before centering and 61,408 seasonal and 184,224 stage rows after
centering. It also handles leap-year changes in cross-year season/stage
durations by averaging that geometry within the registered window. The paired
calendar comparisons are descriptive calendar sensitivity only and do not
identify irrigation treatment effects.
The preregistered replications replace only the scenario label with SSP3-7.0
or SSP5-8.5 while retaining GFDL-ESM4 `r1i1p1f1`, the six crop/calendar
definitions, and the same 2031--2060 and 2042--2049 support rules. All twelve
additional daily files pass catalogue byte/SHA-512 and decoded-content checks.
Each deterministic scenario audit again passes 214,928 seasonal and 644,784
stage rows before centering and 61,408 seasonal and 184,224 stage rows after
centering, with one common same-realization GMST identity across all 12 cells.
Byte-identical audit reruns pass. The three completed GFDL scenarios therefore
supply 24 centered templates, still below the 51-template dependence threshold
and with no held-out ESM; response, damage, welfare, and SCC gates remain
closed.
The first cross-ESM replication binds IPSL-CM6A-LR `r1i1p1f1` SSP1-2.6 to
six version-`20210512` daily files covering 2031--2060. All six pass exact
catalogue byte/SHA-512 and full decoded-content checks. A 30-row annual GMST
series is computed from those same temperature files. The preregistered
12-cell feature build passes 214,928 seasonal and 644,784 stage rows before
centering and 61,408 seasonal and 184,224 stage rows after 21-year centering;
every cell shares the same centered GMST identity and the aggregate audit is
byte-identical on rerun. With 24 GFDL and eight IPSL centered templates, the
available 32-template design remains below the 51-template dependence minimum
and cannot support a balanced whole-ESM or whole-scenario exclusion.
The corresponding IPSL-CM6A-LR `r1i1p1f1` SSP3-7.0 cell binds six more exact
version-`20210512` daily files covering 2031--2060. Full checksum, decoded
content, chronology, 30-row same-realization GMST, and every preregistered
12-cell feature and reconciliation gate pass. The build adds 214,928 seasonal
and 644,784 stage rows before centering and 61,408 seasonal and 184,224 stage
rows after 21-year centering; its aggregate audit reproduces byte-identically.
The matching SSP5-8.5 cell then binds and validates six additional files and
passes the same GMST, row-count, reconciliation, and deterministic-audit gates.
Its `firr` minus `noirr` centered seasonal-rain differences range from -25.94
to +12.50 mm across crops, with both rice pairs identical; these remain
calendar-date sensitivities rather than irrigation effects. Together the two
complete three-scenario ESMs provide 48 centered templates. An exact-key
2032--2059 SSP5-8.5-minus-SSP1-2.6 comparison passes for all 12 cells; mean
temperature changes range from +0.580 to +0.836 C and seasonal-precipitation
changes from -5.07 to +12.62 mm. These are climate-feature comparisons, not
response estimates. The matrix is below the 51-template dependence minimum;
holding out either ESM retains only 24 training templates, and holding out one
scenario retains 32, so whole-ESM and whole-scenario response validation remain
closed.
The next preregistered cell adds MPI-ESM1-2-HR `r1i1p1f1` SSP1-2.6. Its six
version-`20210512` files pass exact bytes/SHA-512, full decoded daily-content,
and model-specific noon-chronology checks; the same temperature realization
yields 30 annual GMST rows. The deterministic 12-cell build passes 214,928
seasonal, 644,784 stage, 61,408 centered-seasonal, and 184,224 centered-stage
rows, exact reconciliation, and a byte-identical aggregate-audit rerun.
Calendar-only `firr` minus `noirr` seasonal-rain differences range from -22.48
to +14.72 mm, with identical rice pairs. This brings the partial matrix to 56
templates but does not satisfy the registered holdout design: an MPI exclusion
retains 48 templates, a GFDL or IPSL exclusion retains 32, and an SSP1-2.6
exclusion retains 32. Joint-dependence fitting and all response, damage,
welfare, and SCC uses remain closed.
The matched MPI SSP3-7.0 replication passes the same six-file checksum and
decoded-content gates, 30-row same-realization GMST, 12-cell raw/centered
feature reconciliation, and byte-identical aggregate-audit rerun. Its
214,928/644,784 raw and 61,408/184,224 centered rows add eight templates;
calendar-only `firr` minus `noirr` seasonal-rain differences range from -21.76
to +11.22 mm, with identical rice pairs. Across 64 templates, every whole-ESM
or whole-scenario exclusion retains only 40--48, below the locked 51-template
minimum, so joint dependence and all response, damage, welfare, and SCC gates
remain closed.
The preregistered MPI SSP5-8.5 cell then passes all six exact checksum and
decoded-content gates, a 30-row same-realization GMST, the same 12-cell
raw/centered feature and exact-reconciliation gates, and a byte-identical
aggregate-audit rerun. It contributes the same 214,928/644,784 raw and
61,408/184,224 centered row counts. Calendar-only `firr` minus `noirr`
centered seasonal-rain differences are +0.85 mm for maize, -14.35 mm for
soybean, zero for both rice seasons, +12.62 mm for spring wheat, and -23.99 mm
for winter wheat. The partial matrix contains 72 templates, but every
whole-ESM or whole-scenario exclusion retains 48, below the locked 51-template
minimum. Joint dependence and all response, damage, welfare, and SCC gates
therefore remain closed.
The MRI-ESM2-0 `r1i1p1f1` SSP1-2.6 cell subsequently passes the same six-file
checksum/content, 30-row same-realization GMST, 12-cell raw/centered,
exact-reconciliation, and byte-identical aggregate-audit gates. It contributes
the same row counts. Calendar-only `firr` minus `noirr` centered seasonal-rain
differences are +0.84 mm for maize, -15.19 mm for soybean, zero for both rice
seasons, +13.80 mm for spring wheat, and -28.16 mm for winter wheat. The 80
templates leave 56--72 after whole-ESM exclusions and 56 after SSP3-7.0 or
SSP5-8.5 exclusion, but only 48 after SSP1-2.6 exclusion. The balanced matrix
remains incomplete, so joint dependence and all response, damage, welfare, and
SCC gates remain closed.
The MRI-ESM2-0 `r1i1p1f1` SSP3-7.0 cell subsequently passes the frozen
six-file checksum/content, 30-row same-realization GMST, 12-cell raw/centered,
exact-reconciliation, and byte-identical aggregate-audit gates. It contributes
214,928 seasonal, 644,784 stage, 61,408 centered-seasonal, and 184,224
centered-stage rows. Calendar-only `firr` minus `noirr` centered seasonal-rain
differences are +0.92 mm for maize, -15.78 mm for soybean, zero for both rice
seasons, +13.08 mm for spring wheat, and -22.93 mm for winter wheat; they do
not identify irrigation effects. The 88 available templates leave 64--72
training templates after excluding a represented ESM and 56--64 after
excluding a scenario, above the locked 51-template minimum in every currently
represented exclusion. UKESM1-0-LL nevertheless has no contiguous feature
templates, so the balanced five-ESM matrix is incomplete and joint dependence,
holdout promotion, response, damage, welfare, and SCC gates remain closed.
We next preregistered a represented-template dependence-stability diagnostic
before reading its outputs. Each of the 88 ESM--scenario--center-year templates
contains 7,676 aligned crop-calendar cells. Seasonal rain, wet frequency,
maximum dry-spell fraction, Rx5/total, Rx1/Rx5, temperature, and two stage-rain
additive-log-ratio coordinates are constructed from the centered derived
files. The implementation reads one season/stage file pair at a time in
explicit center-year blocks, forms one within-template Spearman matrix, and
compares the median matrix in training templates with the held-out median for
four represented whole-ESM and three whole-scenario exclusions. Locked
tolerances are 0.05 for mean absolute difference, 0.15 for maximum absolute
difference, and zero sign reversals when the absolute training median is at
least 0.20.

The MRI-ESM2-0 exclusion is the only failure. Its mean absolute difference is
0.043330, but the wet-frequency--Rx1-given-Rx5 pair differs by 0.192318 and
exceeds the maximum gate. The other three ESM and all three scenario exclusions
pass; no strong pair reverses sign. The computation reads 264 checksum-bound
derived Parquet files sequentially; maximum observed peak RSS across two
deterministic runs is 187,662,336 bytes, well below the registered 2 GiB
ceiling. The failed gate is not retuned. The
diagnostic is not an ECC-Q fit, does not validate missing UKESM or MRI SSP5-8.5
support, and does not authorize FAIR, response, damage, welfare, or SCC use.

We preregistered the MRI failure decomposition before reading its outputs. The
focal pair, original 0.15 maximum-difference gate, two common scenarios, eight
center years, six crops, and two calendar regimes were fixed. The primary test
recomputed held-out versus comparison medians after restricting both sides to
SSP1-2.6 and SSP3-7.0. Its absolute difference is 0.173654 versus 0.192318 in
the original unbalanced comparison, so the locked failure persists. The
scenario-specific differences are 0.163224 and 0.204990, and each of the eight
center-year differences exceeds 0.15. A second descriptive layer calculates
the focal correlation separately within all 1,056 complete
crop/regime/ESM/scenario/center-year fields. Ten of twelve scenario-matched
crop/regime differences exceed 0.15; irrigated- and rainfed-calendar winter
wheat are 0.070128 and 0.084917, while second-season rice is largest at
0.239124 for both calendars. No p-values, tolerance updates, model fitting, or
promotion decisions are permitted by the contract. All 264 inputs are derived
Parquet files read as sequential season/stage pairs; observed peak RSS remained
below 174 MiB across verification runs.
We then preregistered a receipt-only sample-sufficiency decision before
generating its output. It evaluates exactly two pool types: all ESMs pooled and
one ESM at a time. A pool must have at least 51 distinct templates, full
required scenario coverage, and resolved stability evidence; the pooled pool
also requires the complete five-ESM matrix. The current pooled count is 88 but
the matrix and MRI gates fail. A complete conditional pool has only 24
templates under the frozen three-scenario by eight-center-year design, so each
has a 27-template shortfall even after matrix completion. The audit reads three
JSON receipts, no derived Parquet or daily climate file, and performs no fit.
Overlapping 21-year windows are not counted as independent new support without
a separately registered design.
An initial receipt-only temporal count is withdrawn in a checksum-bound
sidecar because it assigned 21-year intervals to legacy annual one-crop/regime
holdout rows. Those rows are not registered as centered linked
multicrop/regime dependence templates, so their exact year labels cannot be
counted toward this gate. A corrected compatibility-first contract was then
preregistered before evaluation. It verifies the 11 current RIME-X cell
receipts and requires all six crops, both calendar regimes, the centered
21-year product identity, and eight center years. A greedy closed-interval
schedule retains at most one of the eight overlapping windows in each
ESM--member--scenario cell. The current 88 nominal templates therefore have an
upper bound of 11 pairwise-nonoverlapping templates; a complete 120-template,
15-cell matrix has an upper bound of only 15. Complete-design whole-ESM and
whole-scenario holdout bounds are 12 and 10. The four legacy receipts contain
2,376,990 rows but contribute zero compatible templates. The corrected audit
reads 17 JSON receipts, no Parquet or daily data, and performs no fit.
Pairwise nonoverlap remains only an upper bound, not evidence of independence;
every FAIR, response, damage, welfare, and SCC gate remains closed.
A subsequent preregistration fixes a purely arithmetic expansion-feasibility
test. It requires the same centered 21-year linked multicrop/regime unit, four
pairwise-nonoverlapping windows within every ESM-member--scenario track, three
SSPs, at least seven member tracks from at least four ESM families, and no more
than two members from one family. The resulting 84-template balanced design
retains 72 training templates after a whole-member holdout, 60 after the
worst-case whole-family holdout, and 56 after a whole-scenario holdout, all
strictly above 51. The corresponding six-member design retains 48 after the
limiting family and scenario exclusions and therefore fails. The evaluator
reads two checksum-bound JSON receipts, no Parquet or daily climate file, and
performs no fit. It does not select members, query new catalogue availability,
estimate bytes, approve storage or acquisition, establish member independence,
or resolve the adverse MRI stability result.
A following contract preregisters an official-catalogue-only candidate screen.
Six queries cover the Cartesian product of SSP1-2.6, SSP3-7.0, and SSP5-8.5
with daily `pr` and `tas`; neither climate forcing nor ensemble member is a
query filter. A track is eligible only when one ESM-member identity is present
in all six cells, every dataset is public, unrestricted, CC0, and version
`20210512`, every required source file exposes a positive byte count and
SHA-512, and continuous daily metadata cover 2015--2035, 2036--2056,
2057--2077, and 2078--2098. The live catalogue contains five eligible tracks
from five families, 30 datasets, and 270 unique source files totaling
536,861,000,440 bytes. Because the contract requires at least seven tracks,
the catalogue gate fails. The audit reads API metadata only, selects no final
ensemble, downloads zero climate bytes, and leaves storage, independence, MRI
stability, fitting, FAIR, response, damage, welfare, and SCC gates closed.
The national joint-crop temporal-support audit reads only county, crop, year,
eligibility, and the already fixed 2017 10% selector flag from the checksum-
bound national panel. After exact corn/soy county-year intersection, it reports
per-county year counts and longest consecutive runs without reading yield
magnitudes. Of 264 common counties, 105 have all 39 years from 1981--2019;
median count and longest run are 38, and the minimum count is eight. This is a
support diagnostic, not a requirement to analyze only balanced counties.
The subsequent metadata-only acquisition contract pins all 90 official
version-`20210512` files required for five ESMs, three SSPs, `pr`/`tas`, and
2031--2060. They total 187,138,935,135 catalogue bytes and are public,
unrestricted CC0 inputs. If all content and feature gates pass, the design
contains 120 centered templates; whole-ESM and whole-scenario exclusions retain
96 and 80 nominal training templates, respectively. The corrected audit does
not treat the overlapping centers as distinct support. These counts do not
imply that files were acquired or that holdout
performance passed.

A separately preregistered U.S. spatial sensitivity uses June 2019 because the
official NOAA county-average and registered gridded inputs were already locally
validated, and fixes nine production counties across nine state FIPS codes
before comparison. Exact official 3,107-county support and 30-day chronology
are required for PRCP/TAVG/TMIN/TMAX. The resulting 36 cells have minimum
defined daily correlation 0.999812; polygon-minus-official monthly rainfall
totals range from -0.830529 to +0.413524 mm. No equivalence threshold was
defined, yield outcomes were not read, and the polygon route was not replaced.
The subsequent temporal expansion holds the county sample fixed and adds
January and December 2019 to the preregistered June comparison. It requires
the same nine counties, four variables, official national support, exact month
lengths, and registered polygon weights in all three months. The resulting 108
cells all have nonzero maximum differences; minimum defined correlation is
0.999758, and polygon-minus-official monthly rainfall differences range from
-0.830529 to +0.619192 mm. No yield outcome or equivalence threshold enters
the selection or audit.
The next fixed expansion adds April and September before acquiring their
official county series. Across the resulting 180 cells, minimum defined daily
correlation is 0.999425 and polygon-minus-official monthly rainfall differences
range from -2.706813 to +1.286771 mm. No outcome is read, the polygon route is
not replaced, and no relationship or SCC gate is opened.

### S9.11 Published fallback-chain readiness

The fallback source screen was preregistered before the primary-source
metadata snapshot. It fixes four named components: MESMER-M-TP as the monthly
temperature--precipitation backbone, Kemsley et al.'s first-order Markov--gamma
method as the daily precipitation generator, MESMER-X Rx1day as the heavy-rain
benchmark, and STITCHES as the sequence-preserving multivariable benchmark.
Substitution after registration is prohibited. Each executable component must
have peer-reviewed method support, a public or archived implementation, a
license identity, and a pinned code identity before any fit.

The audit records public pinned implementations for MESMER-M-TP and both
benchmarks, but no repository or software archive for the fixed Kemsley daily
method. It separately requires exact monthly precipitation conservation,
joint daily temperature--precipitation innovations, spatially coherent daily
rainfall, wet-day frequency, consecutive dry days, Rx1day, Rx5day, crop-stage
timing, whole-ESM and whole-scenario holdouts, direct-daily comparison, and
common-random-number FAIR pulse convergence. Fourteen of fifteen end-to-end
requirements remain unestablished, so the audit exits with
`fallback_not_executable_no_fit`. It reads only metadata and authorizes no
software or climate-payload acquisition, fitting, FAIR evaluation, response,
damage, welfare, or SCC calculation.

### S9.12 Conservative common-innovation daily-pair interface

Before any daily-generator implementation, we preregistered an
algorithm-independent interface for matched FAIR baseline and pulse paths.
The pair identity fixes climate draw, ESM, member, grid, calendar, month, and
pulse size; path role distinguishes the two monthly and daily records. A
counter-based or equivalently keyed random-access stream supplies separate
wet-state, wet-amount, and spatial-dependence innovations. Its key includes
the seed namespace, generator and parameter-bundle identities, climate draw,
ESM/member/grid/calendar/day, innovation family, and slot. It excludes path
role, pulse size, monthly climate values, and path-specific parameters. Thus
baseline and every pulse size can have different thresholds and distributions
without consuming a different subsequent random stream. Matching monthly
innovation digests are required across path roles and pulse sizes.

For each path separately, provisional daily precipitation must be finite and
nonnegative. A zero monthly target requires all daily values to be zero. For a
positive target, the provisional monthly sum must be positive; every positive
provisional amount is multiplied by the target-to-provisional-sum ratio, which
preserves the wet/dry sequence. Any floating-point residual is assigned to the
last positive wet day in calendar order and the corrected amount must remain
nonnegative. The final monthly error cannot exceed the larger of `1e-9` mm or
`1e-12` times the monthly target. Each path must pass this gate independently.

The interface also requires exact zero-pulse and pre-divergence daily identity,
separate support flags, at least three decreasing positive pulse sizes,
direct-daily and crop-stage feature comparisons, whole-ESM and whole-scenario
holdouts, and convergence of pulse-normalized feature differences. A future
receipt must bind code, paper, parameters, monthly inputs, RNG identity and
namespace, innovation digests, output hash, maximum mass error, and peak
resident memory. The current status is
`interface_preregistered_no_generator_implementation`: schema validation is
not scientific validation or permission to implement, and the absent pinned
Kemsley source remains a hard no-fit blocker.

### S9.13 Future daily-pair output schema gate

Before any generator output exists, we separately preregistered its exact JSON
boundary. A bundle contains only a schema tag, receipt, and nonempty monthly
records. The receipt binds the parent interface, generator/paper/parameter and
monthly-input identities, RNG identity and namespace, canonical daily-output
hash, observed maximum monthly mass error, and peak resident memory. The
monthly-input digest is the SHA-256 of UTF-8 JSON with sorted object keys,
compact separators, and nonfinite values forbidden after projecting every
record to climate draw, ESM, member, grid, calendar, year, month, pulse scale,
path role, divergence key, monthly precipitation and temperature targets,
parameter-bundle identity, and support flag, then sorting by the exact monthly
record key. Record order, monthly innovation digests, and daily values are
excluded. Blank, missing, or additional receipt fields fail; memory above 2
GiB fails.

Each monthly record is keyed by climate draw, ESM, member, grid, calendar,
year, month, pulse scale, and path role. Each pair must contain exactly one
baseline and one pulse record. Each climate-month group must contain exactly
one zero scale and at least three distinct positive scales. Daily rows must
contain only the date/model-day and nonnegative precipitation, cover the exact
calendar month in increasing order, and sum to the path-specific monthly target
within `max(1e-9 mm, 1e-12 * target)`. The validator also requires matching
baseline/pulse and cross-scale innovation digests, an invariant baseline daily
path across scales, exact zero-pulse identity, and exact equality on every day
before the registered divergence date.

The in-memory synthetic fixture uses leap Gregorian, noleap, 360-day, and
all-zero calendar months, four pulse scales per month, and 32 monthly records.
It passes with zero maximum mass error. Invariance checks confirm that record
order, innovation digests, and daily values do not change the monthly-input
digest; monthly-target and support-flag changes fail. Fourteen single-purpose
corruptions verify fail-closed behavior for receipt, key, digest, conservation,
identity, day coverage, field, resource, and both hashes. Synthetic test values
are not persisted as climate output. This gate does not implement or substitute
the unavailable generator, validate its science, or authorize software/climate
acquisition, fitting, FAIR evaluation, response estimation, damages, welfare,
or SCC use.

### S9.14 Canonical daily-generator parameter boundary

Before allowing `parameter_bundle_sha256` to identify future parameters, we
separately preregistered its exact object and canonicalization. The object binds
the generator, paper, code, and parameterization identities plus one record for
every monthly output key. Each record contains dry-to-wet and wet-to-wet
transition probabilities on the closed unit interval; strictly positive gamma
shape and millimetre-scale parameters for wet amounts; SHA-256 identities for
the spatial-dependence and joint temperature--precipitation components; and the
support flag. Records are sorted by climate draw, ESM, member, grid, calendar,
year, month, pulse scale, and path role before compact UTF-8 JSON hashing with
sorted object keys and nonfinite values forbidden.

The validator requires unique parameter keys that exactly equal the monthly
output keys, identical support flags, matching generator code identity, and the
canonical parameter hash in both the output receipt and every monthly record.
It rejects missing or extra records, out-of-domain probabilities, nonpositive
gamma values, invalid component hashes, identity mismatches, and parameter
changes hidden behind a stale digest. Record order leaves the hash unchanged.
A two-record synthetic unit fixture rejects ten targeted corruptions, and the
existing 32-record four-calendar output fixture links to 32 parameter records.
These are schema and identity checks only: no parameter is fitted or presented
as empirical, and the missing pinned generator still blocks implementation,
FAIR evaluation, response estimation, damages, welfare, and SCC use.

## S10. Scientific integrity and independent review

Every quantitative statement is classified as observed source data, derived
empirical result, published result, synthetic test, diagnostic pilot,
assumption/scenario, or unavailable/planned. Missing or failed inputs and
analyses are reported rather than replaced by inferred values. Numerical
damage or SCC results require complete provenance, a frozen executable
configuration, machine-readable draw artifacts, holdout validation,
pulse-convergence and accounting checks, and explicit promotion in
`RESULTS_STATUS.md`. The full rules are in
`SCIENTIFIC_INTEGRITY_PROTOCOL.md`; `INDEPENDENT_REVIEW_CHECKLIST.md` defines
the adversarial replication handoff.

### S10.1 Citation and evidence gaps retained at this stage

The cited primary literature supports the definitions of PDSI/SPEI and the
decision to compare rainfall quantity, occurrence, intensity, and observed
drought severity. It does not validate a universal global crop coefficient,
the diagnostic scPDSI threshold of -2, or transport of a historical CRU
scPDSI association to future ISIMIP climate. No completed, validated global
SPEI or soil-moisture candidate is yet available. The climate-to-drought
mapping, causal response design, global welfare calibration, and empirical
cost basis for the `trend` and `upper` adaptation schedules therefore remain
evidence gaps rather than quantities to fill by assumption. The deferred
noncoastal infrastructure-flood component likewise requires its own primary
hazard, exposure, vulnerability, and overlap evidence before implementation.
