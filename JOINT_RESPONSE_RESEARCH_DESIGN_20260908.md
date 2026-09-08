# Joint agricultural response: research design and advancement gates

Status: proposed new response study, not an approved production response or a
completed estimate. This document does not change any existing coefficient,
projection, damage, or SCC permission flag. Completed historical association,
country-control, held-out prediction and climate-input analyses stay complete;
do not rerun them as if no estimates existed.

## Estimands and immediate next work

The final estimand remains global agricultural welfare under a marginal GIVE
CO2 pulse, replacing its existing agriculture component. The next empirical
target is narrower: a **joint historical weather–yield response candidate**,
with precipitation quantity as the primary moisture representation, controlled
for temperature and threshold heat. It must first survive independent outcome
and held-out validation. A subsequent factual/counterclim yield contrast would
be a model-implied historical trend contrast, not automatically an
anthropogenic damage estimate. Do not relabel the pilot as globally sampled.

The highest-value next executable step is a small provenance/design check for
independent response validation: identify the exact U.S. NASS county outcome
and daily-weather records already used in the completed irrigation analysis,
their spatial intersection with the paired climate strip, and years that
remain unexposed to model selection. Inspect existing manifests first, not
another broad download. Report insufficient overlap or a previously inspected
test set honestly. A two-row climate pilot must not be silently expanded into
a county-area average or assigned to a county centroid as if equivalent.

In parallel with that design check only if resources allow, inventory whether
retained global climate/outcome inputs identify GDHY source dependence at a
finer level than the existing crop-footprint country proxy. This is an outcome
validity requirement, not a new attempt to recover significance with more
fixed effects. If source construction cannot be separated, the global fit
remains descriptive and the independently observed U.S. analysis carries the
stronger validation role. U.S. evidence alone cannot identify global transfer.

## Separate prospective fit contract, required before a new fit

Record exact source versions/hashes, outcome and weather units, crop/irrigation
definitions, spatial aggregation, permitted years, missingness, and previously
used validation splits. Do not manufacture a new untouched holdout after
examining its results. A new flexible fit can be exploratory; its validation
claim must disclose repeated use of data. Freeze the design artifact before
executing new empirical fits, and retain unsuccessful fits as well as successes.

Candidate model family to assess, not silently implement here:

- Log yield with cell/county effects and country/state-by-year controls, plus
  a documented alternative first-difference formulation. Weather bases must
  be differenced **after** their nonlinear transformation if differences are
  used. Retain existing estimates as named benchmarks, not production priors.
- Rainfall quantity: low-dimensional nonlinear amount response; define knot
  placement only from training exposures, not future SCC or outcome fit.
  Compare with the existing parsimonious amount specification on identical
  samples. Quantity-first does not mean linearity is known or heat omitted.
- Temperature: crop-stage means and daily Tmax degree-day controls, with
  predeclared complexity and rank checks. Joint precipitation/heat interaction
  is a separate candidate requiring incremental validation, not an obligatory
  assumption that any fitted interaction is causal.
- Irrigation: preserve directly reported NASS regimes in the U.S.; use fixed
  baseline irrigation shares for global exposures. Transform regime-specific
  weather before weighting. Their contrast is not an irrigation treatment
  effect, and fixed shares do not represent future irrigation expansion.
- Timing/extremes: incremental candidate on matched samples only. Existing
  weak/null/worse out-of-sample evidence must remain visible. Do not mandate
  timing in a production model if it does not validate.
- scPDSI/PDSI and SPEI: competing moisture-stress families, not an additional
  damage term. Use only a documented matched forcing and PET/index procedure
  when climate paths are available; the current paired features do not supply
  paired drought indices. Never infer SPEI or PDSI from total rain alone.

Predicted yield agreement must be evaluated with spatial and temporal blocks,
uncertainty appropriate to dependent crop observations, clear baseline losses,
and performance heterogeneity by irrigation and crop. Fix selection criteria
and allowable complexity before the new run. Account for effective source-unit
dependence in gridded yields; pixel counts are not independent sample sizes.

## Identification and joint climate contrasts

Short-run weather variation conditional on fixed effects can support a
weather-response interpretation only under explicit assumptions about omitted
local drivers, measurement error, harvest reporting and treatment timing.
Annual controls can absorb common changes, but they neither estimate a CO2
fertilization response nor prove local temperature/precipitation exogeneity.
Historical adaptation, input choice and selective reporting remain issues.
Long-run transport requires separate evidence, not a label on a regression.

For a validated joint candidate f(P,T), where P is the whole allowed
precipitation feature block and T is the temperature/heat block, the total
conditional climate contrast would be f(P1,T1) - f(P0,T0). Index 1 denotes
factual and 0 counterclim in the historical experiment. With interactions,
an explicit symmetric allocation could be reported as:

    precipitation = 0.5 * [(f(P1,T0)-f(P0,T0)) + (f(P1,T1)-f(P0,T1))]
    temperature   = 0.5 * [(f(P0,T1)-f(P0,T0)) + (f(P1,T1)-f(P1,T0))]

These sum exactly to the joint model contrast. They are an accounting
convention, not two independently identified causal effects. All four mixed
states require support checks; hybrids may break physical dependence. The
completed diagnostic only checks the actual paired paths, not these hybrids.
Do not evaluate the decomposition with existing barred coefficients.

Amount and timing must not be swapped independently as arbitrary derived
features while asserting a valid daily climate sequence. First report a
validated precipitation-block contrast. Any subsequent amount-versus-timing
decomposition needs a separate daily-sequence construction, explicit
zero-precipitation handling, and validation of physical dependence. For drought
models, indices must be recomputed under the relevant driver combinations;
they are not a second precipitation contribution to add to the direct model.

## Extrapolation, adaptation, valuation and GIVE gates

The new support diagnostic finds about 50% maize and 47% soy crop-years outside
at least one factual marginal quantity/heat range, despite much lower joint
distance flag rates. Neither accepting all rows nor dropping flagged rows
without changing the estimand is justified. Register full-sample/extrapolation
sensitivity and restricted-support descriptive results separately. No clipping,
nearest-neighbor substitution or shrinkage may be described as validation.

Fixed, trend and upper adaptation remain the user-authorized scenarios. A
historical time trend is not itself adaptation and the word 'upper' supplies
no empirical bound. Fixed holds specified response/calendar/irrigation choices
constant; trend and upper require independent, source-bound parameterization
and feasible constraints. Do not invent numerical attenuation factors to
complete the scenario table. Carry CO2 as a separately identified/calibrated
driver rather than assigning its effects to precipitation.

Before welfare/SCC: representative crop and geography coverage, baseline
production/value weights, a defensible market and inventory-cost mapping,
uncertainty draws, and genuinely matched baseline/pulse climate inputs remain
required. The reviewed Hultgren market mechanics and price-only prototype do
not yet supply a validated welfare calculation. Replace MooreAg agriculture,
never stack this response on top of it. No new user decision is needed for the
small existing-input provenance check; ask only when substantive scientific
alternatives cannot be resolved with the approved defaults and evidence.
