# Historical climate-source benchmark: rainfall patterns need particular care

September8,2026. Distributional climate diagnostics only; no yield estimate,
bias correction, causal attribution, welfare or SCC calculation.

Terminology: all pr-based “rainfall” below is water-equivalent total
precipitation, including snowfall. Nominal reference compatibility has now
been checked: the historical exposure product and ISIMIP3b adjustment both
use W5E5 v2.0 in this period. This does not make simulated/observed sequences
identical. See`OBSERVED_CLIMATE_REFERENCE_CHECK_20260908.md`.

## Finding

On the292maize/149soybean cells with observed positive yields and aligned
historical exposures, GFDL's1982–2010historical simulation has similar mean
mid-season temperature to the observed-source exposure series, but different
rainfall-pattern distributions. The longest crop-season dry spell is about
1.9days longer and the maximum five-day rainfall is6–11mm higher in the model.
These historical offsets must not be labeled entirely as future climate change.

| Equal-cell mean: model historical minus observed-source historical | Maize | Soybean |
|---|---:|---:|
| Seasonal rainfall,mm | −8.12 | −14.37 |
| Longest dry spell,days | +1.86 | +1.88 |
| Maximum five-day rainfall,mm | +6.09 | +10.77 |
| Stage2mean temperature,°C | +0.048 | +0.101 |
| Stage2threshold heat,°C·days | +0.216 | +1.303 |

Daily Tmax thresholds are29°C/30°C for maize/soy. These offsets describe the
specific model realization and data-source comparison; they do not separately
identify structural model bias, observational error or internal variability.
No simulated year is treated as a reproduction of observed weather that year.

## Why the baseline matters

The table below compares2032–2059SSP585to two different1982–2010baselines on
the same observed-supported cells. It is **not** the previously reported
SSP585-minus-SSP126contrast, nor does it use the full500/327cell pilot support.

| Future SSP585 minus historical mean | Maize: model baseline | Maize: observed-source baseline | Soy: model baseline | Soy: observed-source baseline |
|---|---:|---:|---:|---:|
| Seasonal rainfall,mm | −3.42 | −11.54 | +0.05 | −14.32 |
| Longest dry spell,days | +1.73 | +3.58 | −0.20 | +1.68 |
| Maximum five-day rainfall,mm | +0.34 | +6.44 | −0.45 | +10.32 |
| Stage2mean temperature,°C | +2.336 | +2.384 | +2.186 | +2.286 |
| Stage2threshold heat,°C·days | +100.21 | +100.43 | +86.18 | +87.49 |

In particular, soybean's modeled future longest dry spell is slightly shorter
than its model-historical mean, even though it is longer than the observed-
source historical mean. Simply attributing that entire latter gap to warming
would be misleading. The two future scenarios also both contain climate change;
these period shifts are not unforced or marginal-emissions counterfactuals.

Source and period mean differences reconcile algebraically within8.9e-15.
This identity is bookkeeping, not causal decomposition. Separate temporal
10th/50th/90thquantile differences and between-cell dispersion are retained
for all13non-shape features, plus four precipitation-shape features on valid
nonzero-rain support. They are not uncertainty/confidence intervals. For maize,
shape comparisons use286cells inSSP126 and285inSSP585; soybean uses149in both.
Do not compare their different maize shape cohorts as if identical.

## Heat extrapolation persists against the model's own history

Using the same observed-supported cells, the share of future rows outside at
least one of six **model-historical** stage hot-day/degree-day ranges is:

| Scenario | Maize | Soybean |
|---|---:|---:|
| SSP126 | 5,031/8,176 (61.53%) | 2,635/4,172 (63.16%) |
| SSP585 | 6,444/8,176 (78.82%) | 3,275/4,172 (78.50%) |

Thus the earlier warning does not disappear when the temperature source is
held to the same model family. This still is not a joint response-support
test or a fraction of crops damaged. Finite historical ranges, natural
variability and model/source differences remain relevant.

## Scope and validation

The nine public CC0 source-bound pr/tas/tasmax cutouts cover1981–2010to permit
cross-year harvest seasons1982–2010. GFDL-ESM4,r1i1p1f1,W5E5,version20210512,
[ISIMIP source](https://doi.org/10.48364/ISIMIP.842396.1). Every source passes
exact dates, units, finite-value and grid validation. Negative precipitation
is rejected without clipping. Cross-variable/date grids and adjoining decades
match exactly; no daily mean exceeds Tmax by more than1e-5°C.

Both calendars have686cells and29years each:19,894season rows and59,682stage
rows per crop/regime. Nonlinear rainfall and heat features are constructed
inside the irrigation-calendar regime before fixed MIRCA2000 weighting.
Resulting joint climate tables contain14,500maize and9,483soybean rows, with
no outcomes. Historical observational comparison then restricts to292/149cells,
8,465/4,321observed rows, versus8,468/4,321complete model-historical rows.
Restricting model historical years to observational availability barely changes
maize offsets (e.g.dry spell1.855→1.849days); soybean availability is complete.
That sensitivity matches availability, not actual weather realizations.

Direct-weather full-grid/cutout construction agrees exactly on synthetic
cross-year/noon-stamped examples. Misaligned temperature grids, wrong units,
negative rain, wrong model/member/version/period, missing/duplicate sources
and incorrect distribution support fail tests. Thirteen unittest tests plus
the existing multi-file climate-input test script pass; all real acquisitions,
construction and comparison jobs pass on first execution.

Construction processes one latitude row per child and retains fragments;
full-grid raw files were not downloaded or rehydrated. Peak sampled group RAM
743.78MiB under1024MiB limits. New historical raw/derived artifacts retain
258,391,915bytes (246.42MiB); largest individual directory24.60MiB. Historical
plus the preceding future extension retain475.39MiB in total, excluding small
tracked docs/logs. Free space at export132.96GiB, above130GiB reserve. No unique
data were deleted. Sampling is not a kernel-enforced memory limit.

## Reproduce and next work

Protocol:`HISTORICAL_CLIMATE_BENCHMARK_PROTOCOL_20260908.md`. Nine configs are
`config/isimip3b_gfdl_historical_{pr,tas,tasmax}_{1981,1991,2001}_cutout_20260908.json`.
Use the existing source-request/acquisition tools with fresh receipt/output
paths; await completed server jobs without resubmitting uncertain requests.
Run `build_historical_climate_benchmark.py --crop mai --out-dir NEW_DIRECTORY`
and the soybean equivalent, then `compare_historical_climate_sources.py --out
NEW_RECEIPT`, all through`run_bounded_job.py`. Source hashes, aggregate results,
code hashes, resource receipts and log hashes are preserved in
`data/provenance/historical_climate_benchmark_20260908.json`. No raw climate,
yield records or credentials are published.

Next: independently test the historical distribution comparison with IPSL,
which already has matched future inputs. Do not repeat this GFDL construction.
Precipitation/temperature correction and response transport require explicit
joint-variable and validation choices; no correction is selected from these
results, no rejected model is promoted, and no coefficients are silently
converted into damages.
