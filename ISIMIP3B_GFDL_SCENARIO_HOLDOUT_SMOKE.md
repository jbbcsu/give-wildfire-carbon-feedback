# Bounded GFDL scenario holdout smoke

Status: bounded historical plus three-SSP engineering smoke only; not the
complete five-ESM/time-span product, a paired pulse path, damages, or SCC.

The smoke uses content-validated GFDL-ESM4 `r1i1p1f1` historical 2012--2014
and SSP1-2.6, SSP3-7.0, and SSP5-8.5 2016--2019 bounded maize/rainfed feature
cells. The historical cell was built from committed code in an isolated
`/private/tmp` snapshot, passed exact stage/season reconciliation, and was
copied to ignored interim storage. The evaluator applies the same transparent
cell-mean plus common within-cell same-realization-GMST slope used in the
five-ESM smoke, withholding each complete scenario in turn. Eleven rainfall
quantity, timing, dry-spell, extreme-rain, and mean-temperature feature
families are scored.

This is deliberately narrower than production. The exact four-scenario
training-design gate passes, but only one ESM/member, seven nonoverlapping crop
years, one crop/regime, and two latitude rows are represented. The raw
scenarios do not form a common-random-number marginal pulse pair. Passing the
smoke validates bounded table assembly, exact scenario exclusion, and scoring
mechanics only.

The real table has 113,190 long feature rows and the exact 44
scenario-by-feature scores. The GMST adjustment improves on the training-cell
mean in only 14/44 comparisons; the overall median RMSE ratio is `1.0011` and
the worst ratio is `1.0367`. Improvement counts are 3/11 when historical is
withheld, 6/11 for SSP1-2.6, 3/11 for SSP3-7.0, and 2/11 for SSP5-8.5. This
near-null and mixed result is evidence against promoting the simple GMST
adjustment from the bounded slice. It reinforces the requirement for the
complete historical and multi-ESM/scenario product and explicit structural-
uncertainty treatment.

The machine-readable result is
`data/provenance/isimip3b_gfdl_scenario_holdout_smoke_20260827.json`; transient
long and holdout tables remain uncommitted.
