# Conditional maize drought response on the GIVE/FAIR pulse path

Status: frozen before multiplying any drought--GMST slope by a FAIR pulse.

## Purpose and non-promotion rule

Exercise the numerical climate-interface requested for GIVE using the validated
rainfed-maize endpoint slope, while keeping the scientific gate closed. This
answers what the fitted *linear endpoint relation* would imply for SPEI under
the already validated GIVE/FAIR temperature perturbation. It does not convert
the relation into a validated transient emulator.

The output is a **conditional sensitivity only**. The source slope is based on
multi-forcing late-century SSP endpoints and cannot identify a CO2-only or
anthropogenic response. No soybean path is produced because its primary
whole-ESM rule failed. No yield coefficient, economic value, damage, discount
factor, GIVE agriculture replacement, or SCC calculation is allowed.

## Frozen inputs and calculation

Use the independently validated public drought--GMST evidence in
`data/provenance/five_esm_drought_gmst_endpoint_public_evidence_20260922.json`.
Require the primary maize rainfed season SPEI-3 record to pass every whole-ESM
and whole-scenario holdout. Retain its full slope and the five leave-one-ESM-out
training slopes as six named, unweighted sensitivity slopes. Do not use the
failed soybean slope or select a maize slope after inspecting the FAIR path.

Use the 2,204-row matched core-GIVE FAIR file
`data/interim/give_fair_temperature_path_smoke/temperature_paths.csv`, bound
to `data/provenance/give_fair_temperature_path_smoke_20260827.json`. For each
year, pulse size and slope, calculate

`conditional_delta_spei = slope_spei_per_k * (pulse_temperature - baseline_temperature)`.

Do not add an intercept, clip values, generate weather sequences, or apply the
endpoint slope to the absolute baseline temperature. Preserve all years
1750--2300, the zero pulse, and the three decreasing positive pulse sizes.

## Validation

Require exact zero-pulse identity and exact conditional-SPEI identity through
the 2020 pulse year. Recompute the temperature difference from the two
temperature columns. For the two smallest positive pulses, normalize each
conditional SPEI signal by pulse size and require the same convergence
tolerance used by the validated FAIR temperature path. Report 2021, 2030,
2050, 2100, 2200 and 2300 values for the full slope, the maximum absolute
conditional signal for every pulse and slope, and the full-slope normalized
maximum per GtC. Leave-one-ESM slopes are a named sensitivity range, not a
confidence interval.

A separate implementation must reread the FAIR paths and public slope record,
recompute every one of the 13,224 row--slope products and all reported
summaries, and bind the output hash. Use one worker, sampled RSS <=512 MiB,
<=64 MiB retained output, and >=130 GiB free disk.
