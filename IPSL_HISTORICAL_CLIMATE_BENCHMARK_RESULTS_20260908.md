# Independent-model historical benchmark: IPSL

September8,2026. Climate-input diagnostics only; no crop damages or SCC.
The prospective IPSL protocol is implemented. All nine public CC0 cutouts
passed source identity, dates, grid, units, nonnegative precipitation and
cross-variable daily-temperature checks. pr includes snow water equivalent.

## Historical differences are model-dependent

Both models use1982–2010 historical distributions and the same observed-source
support:292maize/149soybean cells at39.25/39.75°N. Cell differences are equally
weighted after temporal averaging. This is not global or U.S. representative
coverage, a confidence interval, or observed/simulated weather-year pairing.

| Model historical minus observed-source historical | GFDL maize | IPSL maize | GFDL soy | IPSL soy |
|---|---:|---:|---:|---:|
| Seasonal precipitation,mm | −8.12 | −6.60 | −14.37 | −9.63 |
| Longest dry spell,days | +1.86 | +0.55 | +1.88 | +0.76 |
| Maximum five-day precipitation,mm | +6.09 | +1.12 | +10.77 | +1.84 |
| Stage2mean temperature,°C | +0.048 | +0.028 | +0.101 | +0.086 |
| Stage2threshold heat,°C·days | +0.22 | +4.75 | +1.30 | +9.49 |

The precipitation-pattern offsets are smaller in this IPSL realization than
GFDL, whereas threshold-heat offsets are larger. These comparisons do not
separately identify model bias, observational errors or internal variability,
and do not justify choosing one model by its preferred future result.
Thresholds remain29°Cmaize/30°Csoy; nonlinear features precede irrigation
weighting. The original GFDL outputs are unchanged.

## Future minus each model's own historical distribution

SSP5852032–2059 minus historical1982–2010, same292/149cells. This is NOT
SSP585-minus-SSP126 or the earlier500/327cell full-pilot comparison. Neither
historical simulation is a no-anthropogenic-forcing counterfactual.

| Future minus model-historical mean | GFDL maize | IPSL maize | GFDL soy | IPSL soy |
|---|---:|---:|---:|---:|
| Seasonal precipitation,mm | −3.42 | +15.98 | +0.05 | +30.39 |
| Longest dry spell,days | +1.73 | +0.05 | −0.20 | −0.92 |
| Maximum five-day precipitation,mm | +0.34 | +1.24 | −0.45 | +3.24 |
| Stage2mean temperature,°C | +2.336 | +2.561 | +2.186 | +2.447 |
| Stage2threshold heat,°C·days | +100.21 | +87.14 | +86.18 | +66.76 |

Thus precipitation changes depend on model, crop and comparison, even though
warming and increasing threshold heat are consistent in these two realizations.
Do not generalize a negative higher-minus-lower-scenario precipitation
difference into a claim that future precipitation must fall relative to history.

IPSL future rows outside at least one of six model-historical marginal heat
ranges:SSP126maize4,204/8,176(51.42%),soy1,887/4,172(45.23%);
SSP585maize5,725/8,176(70.02%),soy2,655/4,172(63.64%). Source-matched ranges
reduce some earlier observed-source exceedances but do not remove the transport
problem. This is neither a joint-support test nor a fraction of crops damaged.

## Construction, audit and resource use

Each crop uses both GGCMI2015soc irrigation calendars, fractions0/.3/.7/1 and
the1mm/day wet threshold. Each calendar has686cells×29years; fixed MIRCA2000
allocation yields14,500maize and9,483soy joint rows. On observed-supported
cells, maize has8,465observed-source rows versus8,468complete model rows;
soy has4,321in each. Restricting model years to observed availability changes
maize precipitation offset from−6.6003to−6.6106mm and dry-spell offset from
0.54740to0.54773days; soybean is unchanged. This sensitivity is sampling
composition, not same-year weather matching.

Thirteen non-shape features retain mean and temporal10th/50th/90thquantile
differences and cell dispersion. Four precipitation-shape features use287/286
maize cells forSSP126/585 after zero-regime exclusions; soy149in both.
Different shape cohorts must not be treated as identical. Mean source/period
bookkeeping reconciles within1.9e-14; this is not causal decomposition.

Eight targeted tests pass, including cross-model relabeling rejection and
exact daily/calendar checks. All nine requests, nine acquisitions, two builds,
comparison and provenance export completed on first execution. One child
latitude at a time, one numeric thread; peak sampled process-groupRAM746.70MiB.
New retained raw+derived files248.85MiB; largest acquisition directory24.71MiB;
all batches below64MiB. Cumulative with the two preceding completed climate
stages724.24MiB, excluding small documentation/logs. Free disk132.70GiB at
export. No global raw files were hydrated or deleted.

Source-bound configs:`config/isimip3b_ipsl_historical_*_cutout_20260908.json`.
Aggregate provenance:`data/provenance/ipsl_historical_climate_benchmark_20260908.json`.
Ignored complete comparison:
`data/interim/ipsl_historical_soy_joint_20260908/source_comparison.json`.
Existing GFDL comparator:`HISTORICAL_CLIMATE_BENCHMARK_RESULTS_20260908.md`.

For fresh ignored output directories, use bounded launches of
`build_historical_climate_benchmark.py --model ipsl --crop mai/soy --out-dir ...`,
then`compare_historical_climate_sources.py --model ipsl --out ...` and
`export_historical_climate_provenance.py --model ipsl`. Original receipt/output
paths must not be overwritten. Tests are the three`test_historical_*` scripts
recorded in the aggregate provenance. Default GFDL source contracts remain
unchanged; the explicit model option selects registered IDs, not only labels.

## Next scientific step

Both source benchmarks are complete: do not rerun them or multiply diagnostic
yield coefficients by these climate differences. Develop the separate response
transport design, with published historical counterclimate as a feasible
alternative input route to assess. See`ATTRICI_METHOD_ASSESSMENT_20260908.md`.
Global representativeness, CO2/adaptation, welfare and GIVE pulse remain open.
