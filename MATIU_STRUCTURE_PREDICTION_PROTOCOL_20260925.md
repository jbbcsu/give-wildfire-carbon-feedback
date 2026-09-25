# Matiu-structure drought prediction protocol

Date frozen: 2026-09-25

## Purpose and claim boundary

Test whether the nonlinear temperature--moisture structure motivated by Matiu,
Ankerst, and Menzel (2017) improves already-exposed global terminal prediction
relative to linear moisture families. This is an exploratory benchmark, not a
replication, causal estimate, production response, or SCC input.

## Sample and split

Use the exact validated maize and soybean master-support bands. Form
consecutive-year changes at crop-grid cells. Train on endpoints 1983--2010,
purge 2011, and score endpoints 2012--2016. Preserve the existing five
country-hash folds, so no scoring country appears in its fitted fold.

## Models

For each level observation define crop-season mean temperature as the mean of
the three stage temperatures and extreme heat as the sum of the three stage
degree-day measures. Moisture is either `log1p(seasonal precipitation)` or
crop-season SPEI at scale 1, 3, or 6 months.

Every model includes an intercept, endpoint year, endpoint year squared, the
change in seasonal temperature, and the change in extreme heat. Linear models
add the change in the selected moisture measure. Nonlinear models additionally
add changes in temperature squared, moisture squared, and their interaction.
Transform levels before differencing. This avoids incorrectly squaring annual
changes. No family includes both direct precipitation and a drought index.

## Promotion rule

Report pooled-pair and equal-country RMSE. A nonlinear family may advance only
if it improves on its linear counterpart under both weightings, the sign of
that improvement is stable across at least four of five country folds, and a
paired stratified country bootstrap interval excludes zero. Because the
terminal period has already been inspected, passing is necessary but not
sufficient for model promotion. Any further use requires new validation.

## Computation

Run maize and soybean sequentially through `scripts/run_bounded_job.py` with a
1.25 GiB RSS ceiling. Export aggregate SSE/count summaries, hashes, conditions,
and conditional bootstrap intervals only; do not export row predictions or
coefficient arrays.

