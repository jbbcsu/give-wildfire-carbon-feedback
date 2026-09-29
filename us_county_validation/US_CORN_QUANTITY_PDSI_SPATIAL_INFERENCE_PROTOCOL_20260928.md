# Frozen corn quantity/PDSI spatial-inference protocol

## Boundary

This contract closes the missing inference-design step for the two corn
families that passed the outcome-blind readiness audit. It authorizes synthetic
tests only. It does not authorize reading real yields, estimating a response,
exporting coefficients, or making national, causal, damage, or SCC claims.

Non-irrigated and irrigated NASS outcomes must be fitted separately on exact
paired exposure support. Every model uses county and state-by-harvest-year
fixed effects, linear and quadratic stage-mean temperature controls, and one
of two mutually exclusive moisture families:

1. linear and quadratic total crop-season precipitation; or
2. linear and quadratic seasonal PDSI.

PDSI is an alternative moisture family, not an added control. SPEI and direct
rainfall/PDSI stacking are forbidden. The target precipitation contrasts are
+100 mm at the full-sample 25th, 50th, and 75th percentiles. The target PDSI
contrasts are a one-unit decrease at the same frozen percentiles. Reference
values are computed without outcomes and then held fixed across all checks.

## Spatial covariance beyond county CR1

County CR1 remains the conditional primary covariance. Two spatial
sensitivities add cross-county, same-harvest-year score covariance using a
Bartlett distance kernel at fixed 250 km and 500 km cutoffs. Distances use
great-circle distance between hash-bound Census TIGER/Line 2019 county internal
points. The county meat already contains diagonal and all within-county pairs;
the spatial addition therefore excludes same-county pairs and adds only
ordered cross-county pairs within the same harvest year. This combines serial
dependence within county with contemporaneous local spatial dependence without
double-counting the intersection.

No positive-semidefinite clipping is allowed. A nonfinite or negative target-
contrast variance fails the sensitivity. A contrast may be described as
spatially robust only when its normal 95% interval excludes zero under county
CR1 and both spatial cutoffs. This is still conditional associational
inference; the cutoffs are sensitivity scales, not estimated correlation
ranges.

## Geographic influence and terminal checks

Every observed state is omitted in turn. All omissions are retained and must
keep at least 2,500 rows and 100 counties, remain full rank, and have absolute
contrast DFBETA no larger than one full-sample county-CR1 standard error. If a
full-sample contrast is at least one standard error from zero, every state
omission must preserve its sign.

Temporal stability is checked by separate 1981–2011 development and 2012–2018
terminal fits with the unchanged fixed effects and family basis. The terminal
sample must retain at least 500 rows, 100 counties, and five states. The
absolute split difference may not exceed 1.96 times the square root of the sum
of the two independent county-CR1 contrast variances. When either split is at
least one of its own standard errors from zero, the two signs must agree. This
is a confirmation of historical parameter stability, not model selection,
causal validation, or future transport validation.

## Preidentified Texas exposure

County 48277 (TX), harvest year 2011, was identified without outcomes as the
maximum-leverage corn row. It remains in every primary quantity and PDSI fit;
both families already passed their 0.05 leverage gate. Predeclared leave-row-
out and leave-entire-county-out changes are reported only as influence
sensitivities, with DFBETA ceilings of 0.5 and 0.75 respectively.

The expanded distribution family remains ineligible. Its 0.07630 design
leverage cannot be repaired by deleting this row. Reentry requires a separately
frozen, outcome-blind redesign that passes the original 0.05 leverage gate on
the unchanged full sample.
