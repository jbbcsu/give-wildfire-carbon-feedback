# Historical precipitation totals and timing: paired counterclimate pilot

September8,2026. **Validated climate-input comparison, not agricultural damage,
anthropogenic-forcing attribution or SCC.** No new emulator was trained.

## Question and scope

How do observed-source crop-season climate exposures differ from the published
detrended version of the same weather sequence? We use GSWP3-W5E5 obsclim and
counterclim, not a future high-versus-low emissions comparison. ATTRICI removes
historical trends associated with global temperature irrespective of their
cause; its limitations are documented in`ATTRICI_METHOD_ASSESSMENT_20260908.md`.

Support remains only39.25/39.75°N:500maize/327soybean cells with fixed MIRCA2000
irrigation weights. These equal-cell averages are not globally representative,
production-weighted or specific U.S. national estimates. Both irrigation
calendars enter the crop exposures; they are not separate measured yields.
pr includes snow water equivalent. No PDSI/SPEI counterclimate has been built.

## Both totals and distribution change

Factual minus counterclim,1982–2010; average paired crop-year differences
within each cell, then equal weight across cells. Positive means larger in
the factual source. Shape metrics use488maize/325soy cells after removing
cells with any zero-rain regime in either path; totals and heat retain500/327.

| Crop-season exposure difference | Maize | Soybean |
|---|---:|---:|
| Total precipitation,mm | +8.70 | +12.47 |
| Longest dry spell,days | −0.411 | −0.656 |
| Maximum five-day precipitation,mm | +0.501 | +0.385 |
| Stage1precipitation share,percentage points | +0.830 | +0.221 |
| Stage2precipitation share,percentage points | −0.340 | +0.102 |
| Stage3precipitation share,percentage points | −0.491 | −0.323 |
| Across-stage precipitation concentration,HHI | −0.00281 | −0.00607 |
| Stage2mean temperature,°C | +0.982 | +0.800 |
| Stage2threshold heat,°C·days | +14.66 | +9.19 |

The spatial10th–90thpercentiles of cell-mean precipitation differences are
−12.59to+35.28mm(maize),−12.55to+42.68mm(soy); these are geographic dispersion,
not confidence intervals. There is no uniform drying signal on this sample.
The crop-specific heat thresholds are29°Cmaize/30°Csoy; stages use0/.3/.7/1
season fractions and dry spells use a1mm/day threshold.

The predeclared early1982–1991and late2001–2010comparisons also remain in
the output. Factual-minus-counterclim precipitation differences rise from
7.17to10.54mm maize and10.38to15.10mm soy; dry-spell differences change from
−0.373to−0.511days maize and−0.554to−0.735days soy. These describe this
conditional detrending comparison, not independently estimated causal trends.

More precipitation and shorter dry spells do not establish net agricultural
benefits: heat, regional variation, baseline moisture, extreme wetness and
crop responses must be evaluated jointly. No historical yield coefficient
has been multiplied by these differences. This does not reverse or contradict
the different future scenario/baseline diagnostics.

## Validation and the failures that were resolved

All eighteen public CC0 source-bound daily cutouts are resident and validated
for the required crop domain. The initial counterclim precipitation file
failed the existing full-grid missingness gate. Its754permanently missing
cells lie wholly outside all four crop-calendar masks; all686crop cells are
finite on every day. A separate exact-domain validator rejects any missing
crop value, intermittent mask, infinity or unexpected finite noncrop value.
The full-grid validator is unchanged; the original failure and file remain.
See`FACTUAL_COUNTERCLIM_DOMAIN_AMENDMENT_20260908.md`.

Four crop/scenario products contain47,966joint rows in total. Exact paired
daily axes, date coverage, units, nonnegative precipitation, daily mean/max
temperature ordering, calendar/weight identities and crop-year completeness
passed. No missing crop weather was filled or crop support reduced.

The initial factual-feature parity check also failed. Differences were below
0.0001mm in totals but exceeded the registered tight tolerance. The first
uniform early float32 reconstruction failed too. The successful audit used
the actual hash-bound unweighted panels: early rainfed primitives match
float32 sums, irrigated primitives float64 sums, for both crops. Every early
primitive matches one of those EXACT reductions, and every new season/stage
total matches raw-daily float64 reduction exactly. Reassembled historical
weighted features have ZERO residual on all8,465maize/4,321soy observed keys;
unaffected fields separately match at the original tolerance. Both comparison
paths use the new float64 sums. Old inputs/results were not overwritten and
the original strict parity failure is explicitly retained, not relabeled as
an initial pass. See`FACTUAL_PARITY_PRECISION_RECONCILIATION_20260908.md`.

Two disk-guard interruptions occurred before crop builds. Owned-path disk
monitoring resolved the accounting problem while preserving64MiB/job and
130GiB free-space safeguards (`OWNED_DISK_ACCOUNTING_20260908.md`). The small
regression test subsequently used95,632sampled new bytes and passed. Eighteen
distinct targeted tests pass. All four crop builds completed first execution.
Peak sampled process-group RAM786.52MiB; new retained inputs/products407.95MiB,
largest retained batch25.14MiB. Cumulative with preceding climate stages
1,132.19MiB, excluding small logs/docs;159.16GiB free at export. The increase
in free space versus earlier exports is not attributed to project cleanup;
no unique/derived files were deleted here.

## Reproduction and remaining work

Protocols and their amendment hashes are in the product receipts. Use
`prepare_heat_subset_pilot.py` then`acquire_registered_heat_cutout.py` with
the exact registered config/request files; counterclim requires the explicit
`--counterclim-crop-domain` flag. The first preserved payload instead uses
`revalidate_counterclim_cutout.py` with a new receipt and no download.
Run`build_observational_climate_benchmark.py --scenario obsclim/counterclim
--crop mai/soy --out-dir ...` via the bounded launcher and fresh owned output/
scratch paths. Then use the precision reconstruction and paired-comparison
scripts. Do not overwrite existing artifacts or rerun completed construction.

Complete aggregate provenance, including unsuccessful attempts:
`data/provenance/factual_counterclim_pilot_20260908.json`.
Full ignored climate comparison:
`data/interim/counterclim_soy_joint_20260908/paired_comparison.json`.
Next is an explicit joint crop-response/transport design on a defensible
sample, not exporting barred coefficients or treating this pilot as global
damages. CO2/adaptation,representative weighting,welfare and GIVE pulse remain.
