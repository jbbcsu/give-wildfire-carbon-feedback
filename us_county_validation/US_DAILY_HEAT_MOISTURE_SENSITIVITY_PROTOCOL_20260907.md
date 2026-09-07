# Daily-heat competing-moisture sensitivity

On the exact 20,228 audited first-difference observations and unchanged
development leave-state-out, terminal-time, and precipitation-tail splits,
reproduce the registered baseline and add daily heat controls to every model
family.  Evaluate 29 C and 30 C separately.  For each threshold add first
differences of the three stage-specific cell-first Tmax exceedance sums and
three stage-specific above-threshold day counts.  Do not include season totals,
which are exact sums of the stages, and do not stack the two thresholds.

Heat levels must come from the validated 1981--2019 heat assembly and must join
one-to-many without changing practice-specific outcome support.  Square no
heat metric.  Use the existing endpoint purge, training-only scaling, solver,
model families, folds, and diagnostic materiality rules without change.

These reused splits are exploratory sensitivity evidence, not independent
confirmation.  Export only aggregate predictive metrics and comparisons; no
coefficients or row predictions.  A lower RMSE does not identify a causal
temperature or precipitation response and authorizes no model promotion,
future projection, FAIR run, damage, welfare, or SCC calculation.  Retain null
and adverse results.  Run once through the 1 GiB bounded monitor using only
the retained derived tables.
