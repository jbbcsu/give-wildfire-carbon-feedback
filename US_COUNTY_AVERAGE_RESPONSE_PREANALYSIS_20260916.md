# Pre-analysis rules for the nationwide U.S. NASS weather stress test

This design is frozen **before** fitting the new NOAA county-average weather
to NASS 2020–2025 yield magnitudes. It is an additional U.S. predictive and
measurement-robustness check, not a pristine test of the whole research
program: earlier weather sources, models and pre-2020 holdouts were examined.
It does not by itself identify global climate-change damages or a GIVE SCC.

## Outcome, sample and exposure

Use positive annual [USDA NASS Quick Stats](https://www.nass.usda.gov/Quick_Stats/)
SURVEY county YIELD in bushels/acre for corn grain and soybean `ALL
PRODUCTION PRACTICES`, with real 2019 TIGER-matched county FIPS. The primary
rainfed-dominant *sample proxy* requires a numeric crop-specific <=10% share
of irrigated acreage from the **fixed 2017 Census**, never treating suppressed
or missing acreage as zero. Report all-practice and <=20/30%/2022-vintage
screen sensitivities separately. Do not relabel any all-practice yield as a
directly observed non-irrigated yield. The existing practice-specific NASS
series remain a separate historical comparison; post-2019 paired direct-
practice outcomes are too sparse for a credible terminal test.
For the primary paired historical/terminal analysis, apply the existing fixed
2019 TIGER substantial-county-change geography gate in both periods; a
terminal-only county outside that gate is counted as attrition rather than
given an invented historical county effect.

Join to the new NOAA county-area-average daily features on exact
crop/county/harvest-year keys, only where the fixed 2010 NASS crop calendar
has source support. Use the same source, county estimator, calendar and
feature code for historical 1981–2019 fitting and recent 2020–2025 testing.
Report availability and any missing/calendar/boundary exclusions by year,
crop and geography *before* outcome-response estimation. Never impute missing
yield/weather, duplicate a county, or select counties based on their yield
response. NOAA county-average exposure is not crop-pixel weather and is not
numerically interchangeable with the earlier cell-first polygon method.

## Fixed model ladder

For each crop separately, use log positive yield as the target and compare
the same county-years across models. A no-weather county/time baseline comes
first. The parsimonious weather model adds seasonal precipitation total and
its quadratic, seasonal TAVG and TMAX heat exposure to separate moisture from
temperature. Candidate timing/extreme extensions add wet days, longest
PRCP<1mm dry run, Rx5, and two of three stage rainfall shares; do not include
all three shares with an intercept or use stage totals alongside total without
a registered compositional constraint. Fit candidate families separately and
report incremental predictive value relative to the quantity/temperature
baseline. PDSI/scPDSI and SPEI are **competing** moisture-stress families,
not automatic additive regressors alongside raw rain and temperature. Any
index comparison must document its calibration period and source climate
inputs so that terminal observations cannot leak into standardization.

For the first exact, non-tuned model ladder, the no-weather baseline is one
historically estimated intercept per county plus `(harvest_year−2000)/10`.
The quantity/temperature model adds `precip_mm/1000`, its square,
`tmean_c/10`, and `tmax_exceedance_29c_c_days/100`. The registered pattern
extension adds `wet_days_ge_1mm/100`, `cdd_max_days/100`, `rx5day_mm/100`,
and stage-1/stage-2 precipitation shares (stage 3 omitted). All are fitted by
unpenalized least squares on 1981–2019 only, with a diagnostic condition and
convergence check; no coefficient or feature is selected using terminal
outcomes. This is deliberately a transparent initial benchmark, not the final
causal specification or a claim that within-season terms help.

Historical fit ends in 2019. County fixed effects and a prespecified common
time trend (with state-specific linear trend sensitivity) are estimated on
the historical sample; a historical year-effect specification may diagnose
confounding but is not used for out-of-sample absolute forecasts because
unobserved future year intercepts cannot be predicted. Standardization and
any regularization parameter are determined using only historical blocked
years, with no 2020–2025 yield value consulted. A first-difference model is
a separate sensitivity; its 2020 endpoint may use the observed 2019 yield
only as a declared forecasting baseline and must be scored separately from
the levels model. A county absent in historical fitting has no estimable
county intercept and is excluded from county-fixed-effect scores with its
attrition reported; it is not assigned an invented effect. County
composition, terminal-year and year-block losses must all be shown, not just
a pooled headline score.

As a non-pristine historical diagnostic, also fit each unchanged model on
1981–2010, purge 2011, and score 2012–2019 among counties previously seen
in training. Earlier project work examined some of these historical years,
so this check is not an independent confirmation or a hyperparameter source.
Do not choose a model because it wins this diagnostic and then describe the
2020–2025 score as untouched discovery; report both comparisons.

Primary predictive comparison: paired 2020–2025 root-mean-squared error in
log yield, alongside mean error and per-year/crop sample counts on identical
keys. Also score persistent same-county observations and geographic/state
subsets. Use paired state/block resampling for uncertainty, retaining the
limited number of terminal years. A timing/extreme family earns substantive
prominence only if improvement over total-rain-plus-temperature is stable
across recent years, crop/geographic sensitivities, and reasonable sample
screens; worse/null performance is reported plainly. Predictive improvement
does not imply causal identification. Do not opportunistically select a
winning metric or retrospectively redefine the terminal sample.

## Attribution and downstream gate

The U.S. test is only one piece of the global agricultural replacement
evidence. Any eventual climate-attributable crop effect must compare
matched projected climates with versus without anthropogenic forcing, alter
precipitation quantity and timing while controlling temperature and CO2
fertilization consistently, propagate adaptation (fixed/trend/upper)
scenarios, keep process-model and observational evidence distinct, and
account for displacement of GIVE's existing agriculture damages. Monetary
conversion and SCC integration require separate valuation, global transfer,
uncertainty and no-double-counting checks. No step here authorizes a causal
or SCC claim from a U.S. forecast score.
