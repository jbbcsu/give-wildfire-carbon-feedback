# Published PEEPS monthly-pattern SCC decomposition: validated diagnostic

## Question

How much of the one-model monthly precipitation-pattern diagnostic comes from
the crop-season rainfall total, and how much comes from redistribution across
the months of the crop season?

## Matched reference

For every crop-calendar regime, year, and FAIR pulse, the quantity reference
preserves the joint PEEPS crop-season rainfall anomaly exactly but distributes
it across crop months in proportion to the positive historical monthly
climatology. It therefore changes seasonal quantity while holding historical
within-season rainfall shares fixed. The timing increment is defined after the
nonlinear crop response and national-market aggregation as joint monthly-
pattern damage minus this matched quantity-reference damage. It is a contrast,
not a separately additive damage function.

The calculation inherits the joint path's fixed common physical support: 360
of 32,301 crop cells are excluded because either irrigation regime would have
a negative month under at least one registered pulse/year. This is 0.649% of
eligible crop area and 0.998% of response value, with no renormalization.

## Result

At the smallest registered pulse and the 2% discount schedule, the diagnostic
values are 2020 USD per tCO2:

| Adaptation case | Joint monthly pattern | Quantity reference | Timing increment |
|---|---:|---:|---:|
| Fixed | 0.004269 | 0.002939 | 0.001330 |
| Trend | 0.002143 | 0.001135 | 0.001009 |
| Upper | -0.000376 | -0.001004 | 0.000628 |

Under fixed practice, the timing contrast is about 31% of the joint
diagnostic; under the trend rule it is about 47%. Under the upper rule, the
quantity reference is beneficial while the timing contrast is damaging, so
the joint result remains a smaller net benefit. These differences are useful
evidence that monthly redistribution is not negligible in this model. They do
not establish a universal timing share.

## Validation

- Exact annual damage identity passes with zero absolute error.
- Exact discounted SCC identity passes to `6.51e-19` 2005 USD/tCO2.
- The joint channel reproduces the previously frozen joint diagnostic to
  `9.89e-17` 2005 USD/tCO2.
- Maximum shrinking-pulse disagreement is `1.48e-5`, below the registered
  `2e-4` tolerance, across all three channels.
- The minimum proportional rainfall scale in the quantity reference is
  `0.999998721`, so the reference stays nonnegative.
- The bounded damage-decomposition job sampled a peak process-group RSS of
  296.5 MB, below the 512 MiB ceiling.

## Interpretation boundary

This is a one-ESM (MPI-ESM1-2-HR), SSP5-8.5, maize-only, monthly-mean
diagnostic. It does not represent daily dry spells, drought indices, rainfall
extremes, other crops, probabilistic climate uncertainty, or a paired GIVE
agriculture replacement. Its discount factors come from standard deterministic
GIVE while Moore agriculture remains installed. It is therefore not the
project's final precipitation SCC.

## Reproducible artifacts

- `scripts/decompose_peeps_monthly_damage_paths.py`
- `scripts/build_peeps_monthly_scc_decomposition.py`
- `data/provenance/peeps_monthly_damage_decomposition_20261012.json`
- `data/provenance/peeps_monthly_scc_decomposition_20261012.json`
