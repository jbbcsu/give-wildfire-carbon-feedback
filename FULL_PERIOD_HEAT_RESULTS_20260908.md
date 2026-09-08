# Full28year matched climate inputs: two models, two crops

September8,2026. Climate diagnostics only: **not crop losses, welfare or SCC**.

## Main result

Extending the matched daily-heat calculation from eight to28harvest years
resolves the short-window rainfall sign disagreement for these two models:
both now show less seasonal rain, longer longest dry spells, and more
mid-season threshold heat under SSP585 versus SSP126. Magnitudes and local
signs still differ. The rainfall numbers reproduce the existing full-period
rainfall basis; they are not new rainfall estimates. The new contribution is
matched daily heat, full-period joint inputs and their validation.

| Equal-cell mean SSP585-minus-SSP126,2032–2059 | GFDL maize | IPSL maize | GFDL soybean | IPSL soybean |
|---|---:|---:|---:|---:|
| Seasonal rainfall,mm | −24.00 | −3.50 | −31.74 | −4.15 |
| Longest dry spell,days | +1.72 | +0.22 | +1.20 | +0.33 |
| Maximum five-day rain,mm | −4.27 | −1.20 | −6.10 | −2.05 |
| Stage2threshold heat,°C·days | +29.61 | +28.47 | +26.83 | +26.69 |

Thresholds are29°C for maize and30°C for soybean, applied to daily Tmax
within each irrigation-calendar regime before fixed MIRCA2000 area weighting.
Stages divide crop-season duration at0/0.3/0.7/1; they are timing proxies,
not validated physiological stages. The other stage heat increases are also
positive on average, but cellwise directions are not uniform. Full13feature
summaries, spatial10th/90thpercentiles and sign counts are in the provenance.
Those spatial percentiles are not confidence intervals.

Scope remains39.25/39.75°N,500maize/327soybean supported cells. Each model/
scenario supplies14,000maize and9,156soybean crop-years; all eight joint tables
contain92,624rows. These are equal-cell summaries after irrigation-regime
weighting, not globally representative, national, production-weighted or
welfare-weighted effects. The paired scenarios differ in more than marginal
CO2; neither is an unforced counterfactual. Two models/one realization each
do not quantify climate-model uncertainty or isolate internal variability.

## Historical extrapolation remains substantial

For the292maize/149soybean cells with observed positive GDHY yields and
historical1982–2010heat controls, each scenario has8,176/4,172evaluable future
crop-years. Outside means at least one of six stage hot-day/degree-day fields
lies beyond that cell's historical range, with absolute tolerance1e-10.

| Model/scenario | Maize outside/evaluable | Soybean outside/evaluable |
|---|---:|---:|
| GFDL SSP126 | 5,162/8,176 (63.14%) | 2,338/4,172 (56.04%) |
| GFDL SSP585 | 6,581/8,176 (80.49%) | 3,160/4,172 (75.74%) |
| IPSL SSP126 | 5,375/8,176 (65.74%) | 2,411/4,172 (57.79%) |
| IPSL SSP585 | 6,660/8,176 (81.46%) | 3,134/4,172 (75.12%) |

These are marginal heat-range diagnostics, not a joint support test or a
percentage of crops damaged. They mix genuine future exposure changes and
possible climate-source differences. They cannot justify applying historical
yield coefficients without source-matched historical checks and transport
assessment. Missing historical ranges are excluded, not filled or renormalized.

## Acquisition, validation and reproducibility

Only eight missing two-row Tmax cutouts were downloaded,2031–2040/2051–2060
for GFDL-ESM4/IPSL-CM6A-LR SSP126/585, r1i1p1f1 W5E5. Four resident2041–2050
files were reused. Public source identity/version/CC0 rights were verified
against the official ISIMIP catalogue, version20210512,
[dataset DOI](https://doi.org/10.48364/ISIMIP.842396.1). Parent source IDs,
paths, catalogue SHA512s and downloaded cutout SHA256s are recorded; full
global parent payloads were not downloaded or asserted verified.

Explicit dates include all Gregorian leap days:3653/3652/3653days in each
three-decade sequence. Every cutout passes variable, units, grid, dates and
finite-value checks. Every sequence passes lineage, identical coordinate order
and exact adjoining timestamp checks. Both irrigation calendars pass seasonal/
stage heat reconciliation. The join requires exact rainfall support and
identical weighted stage mean temperatures; no future outcomes are fabricated.

All eight overlaps with2042–2049old products match **every column exactly**,
covering26,464old rows across models/scenarios/crops. The strengthened test
suites pass20tests. An initial synthetic fixture lacked dated filenames; its
fixture was updated, not the validation gate. The initial IPSL acquisition
check encountered a still-running server job, downloaded nothing, and stopped
the chain. It later acquired the same finished job without resubmission.
Both events and original logs are preserved.

One numeric thread/analysis job at a time; all real calculations completed
under1024MiB sampled process-group limits. Maximum observed801.08MiB;
largest retained individual acquisition/processing directory24.73MiB. New raw
cutouts plus crop products/receipts total240,091,220bytes (228.97MiB), excluding
small tracked documentation/logs and excluding preexisting middle-decade inputs.
Free disk at aggregate export133.24GiB. The process-group sampler is not a
kernel memory cap.

Protocols: `FULL_PERIOD_HEAT_PROTOCOL_20260908.md` and
`IPSL_FULL_PERIOD_HEAT_PROTOCOL_20260908.md`. Source contracts are the eight
`config/isimip3b_{gfdl,ipsl}_{ssp126,ssp585}_{2031,2051}_heat_cutout_20260908.json`
files. Run `prepare_heat_subset_pilot.py` then `acquire_registered_heat_cutout.py`
with a fresh request/output path; requests can require server completion first.
Run `extend_heat_cutout_two_crops.py --pilot FIRST MIDDLE LAST --year-start 2032
--year-end 2059`, explicit model/scenario/
crop and threshold. Run `validate_full_period_heat_overlap.py`,
`compare_paired_heat_climate.py --year-start 2032 --year-end 2059`, and
`compare_future_heat_ranges.py`, each through `run_bounded_job.py` with a new
receipt/log. `config/{gfdl,ipsl}_full_period_heat_comparison_20260908.json`
binds the actual paired outputs. Aggregate reproducibility evidence:
`data/provenance/full_period_heat_20260908.json`.

## Next distinct step

Do not rebuild these future inputs or repeat the completed contrasts.
Advance the source-matched historical benchmark and joint-response transport
design in `RESPONSE_TRANSPORT_NEXT_STAGE_20260908.md`. The needed causal,
adaptation/CO2, welfare and GIVE pulse links remain unfinished. No empirical
SCC figure is available.
