# Longer-period, multi-crop direct scenario comparison

Register before calculation. Extend the short maize pilot using retained
annual feature products for 2032–2059 (28 harvest years), not overlapping
21-year centered products. No new data, emulator, yield or SCC calculation.

Freeze the source matrix in
`data/provenance/isimip3b_rimex_contiguous_completed_matrix_audit_20260903.json`.
Verify its referenced audit and config hashes and every consumed season/stage
file hash. Refuse missing or macOS dataless source files; do not rehydrate.
Use all available complete SSP126/candidate pairs: GFDL, IPSL and MPI for
SSP370 and SSP585, plus MRI for SSP370 only. No UKESM or MRI SSP585 values
are imputed. Compare candidate scenarios using the common three-model set;
the fourth SSP370 model is a separately labeled sensitivity, not a different
ensemble silently compared with SSP585.

Use all six crop-season definitions × both calendar regimes, retaining
crop identity and support. Report whole two-latitude bands and USA/CHN
singleton-country-proxy subsets. No weighting by outcomes, crop area or
production. Fully irrigated versus rainfed calendar differences are not
irrigation treatments, simulated irrigation applications or yield effects.

Pair exact cells/years. Validate three stage rows per season, fractions,
calendar identities, stage/season rainfall reconciliation and stage-day
weighted temperature. Calculate the same 11 season/shape features as the
short pilot, with the legacy stage-position index and three-stage HHI explicitly
identified. Before execution, source inspection established stage fractions
(0, 0.3, 0.7, 1). Preserve the existing index weights (1/6, 1/2, 5/6) for
comparability, but do not call them actual window midpoints or interpret the
index as exact timing in days. Reuse within-cell then equal-cell averaging and positive-rain
shape support rule over all 28 years. Record absent country subsets. Report
all model-specific results and all features; model ranges are not CIs.

Record whether the actual source schemas contain the stage mean temperatures
and daily Tmax threshold integrals required by historical response models.
Do not reconstruct heat extremes from mean temperatures or substitute
rainfed-calendar primitives for irrigation-weighted nonlinear response bases.
This inventory is confined to the selected retained products; it does not
assert absence across every external source or every project artifact.

Read one crop/regime scenario pair at a time, under the existing bounded-job
monitor with numerical threads one and at most 2 GiB. Retain aggregate results
only. Preserve raw/derived restricted files outside Git. The longer window
reduces the short-pilot limitation but does not remove internal variability,
shared ESM structure, narrow geography, joint-forcing attribution limits or
the missing marginal CO2, crop-transport and welfare links.

## Transparent numerical-precision amendment

The first run stopped at a newly introduced 1e-5 °C stage/season temperature
reconciliation threshold. A context-only rerun located the failure in IPSL
SSP585 spring-wheat/rainfed: one of 19,208 rows differed by
1.00336155e-5 °C, with exactly reconciled season days. At that row's 22.761 °C
mean, one float32 representable step is 1.90735e-6 °C. Both original feature
builders call `.mean()` on the source temperature arrays without requesting
float64 accumulation, consistent with this small aggregation discrepancy;
the original daily values were not rehydrated to prove its cause.

Before the next full run, declare 1e-4 °C absolute agreement as adequate
numerical resolution for this descriptive climate comparison, retain every
file's actual maximum residual, and test acceptance at 2e-5 and rejection at
2e-4. This is an explicit changed numerical tolerance, not an unchanged
preregistration or a demonstrated worst-case floating-point bound. No values,
calendar-day identities, rainfall tolerances, response-validation rules or
SCC gates are changed. Preserve both failed resource receipts/logs. A later
raw-data rebuild should accumulate temperature in float64; it is not required
to convert a sub-0.0001 °C precision check into a damage estimate.
