# Bounded GFDL scenario holdout smoke

Status: three-future-scenario engineering smoke only; not the required
historical plus three-SSP product, a paired pulse path, damages, or SCC.

The smoke uses the existing content-validated GFDL-ESM4 `r1i1p1f1`
SSP1-2.6, SSP3-7.0, and SSP5-8.5 bounded maize/rainfed feature cells for
2016--2019. It applies the same transparent cell-mean plus common within-cell
same-realization-GMST slope used in the five-ESM smoke, withholding each future
scenario in turn. Eleven rainfall quantity, timing, dry-spell, extreme-rain,
and mean-temperature feature families are scored.

This is deliberately narrower than the production validator. Historical is
absent, only one ESM/member and four crop years are represented, and the raw
scenarios do not form a common-random-number marginal pulse pair. Passing the
smoke can validate table assembly, exact scenario exclusion, and scoring
mechanics only.

The real table has 90,552 long feature rows and the exact 33
scenario-by-feature scores. The GMST adjustment improves on the training-cell
mean in only 12/33 comparisons; the overall median RMSE ratio is `1.0002` and
the worst ratio is `1.0452`. Improvement counts are 6/11 when SSP1-2.6 is
withheld, 4/11 for SSP3-7.0, and 2/11 for SSP5-8.5. This near-null and mixed
result is evidence against promoting the simple GMST adjustment from the
bounded slice. It reinforces the requirement for the complete historical and
multi-ESM/scenario product and explicit structural-uncertainty treatment.

The machine-readable result is
`data/provenance/isimip3b_gfdl_scenario_holdout_smoke_20260827.json`; transient
long and holdout tables remain uncommitted.
