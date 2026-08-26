# Response-specification boundary

## Purpose

The project has two different response specifications and they must not be
conflated:

1. `config/response_evaluation_spec.toml` is a **version-hashed predictive
   diagnostic**. It compares three small first-difference models, suppresses
   coefficients, and cannot provide response draws or SCC inputs. Any split or
   feature revision creates a new diagnostic version and makes prior audit
   artifacts stale.
2. `config/primary_response_spec.toml` is a **not-yet-frozen production causal
   design registry**. It records the complete set of feature comparisons and
   unresolved decisions required by the approved estimand. It does not
   authorize fitting.

The executable scope audit in
`scripts/validate_response_spec_boundaries.py` fails if the production registry
drops a required feature comparison, relabels a known diagnostic omission as
covered, selects an unsupported threshold, stacks competing drought families,
or promotes the current aggregation harness to production.

## What the version-hashed diagnostic does and does not cover

| Requirement in the production comparison | Diagnostic coverage | Production implication |
|---|---|---|
| Seasonal precipitation quantity | Covered by log seasonal total | Functional form remains open. |
| Crop-window precipitation quantity | Covered by three temporal-proxy totals | The windows are not validated phenological stages. |
| Normalized stage distribution and timing | Partial: stage totals encode some timing but do not separate shape from total | Compare explicit stage shares/timing/concentration while holding seasonal amount fixed. |
| Wet-day frequency | Omitted | A production wet-day definition and occurrence term remain to be registered. |
| Conditional wet-day intensity | Omitted | Estimate separately from amount and occurrence. |
| Consecutive dry days | Covered at season and proxy-stage scales | Wet/dry threshold and nonlinear form remain open. |
| Rx1day | Covered at season and proxy-stage scales | Tail response form remains open. |
| Rx5day | Omitted | Must enter a production candidate comparison. |
| Mean temperature | Covered | Nonlinear temperature form remains open. |
| Heat extremes | Omitted | Crop-specific thresholds must come from primary evidence or a documented training-only rule. |
| Temperature--precipitation interactions | Covered only for mean temperature by log precipitation total | Compound hot-dry and wet-heat forms remain open. |
| Climatic-water-balance and soil-moisture drought families | Omitted | Evaluate as separate alternatives to the direct-pattern family; never stack or add their damages. |

Thus a favorable diagnostic ranking cannot select a production model. The
diagnostic omits wet-day frequency, conditional intensity, Rx5day, heat
extremes, and the alternative drought families; it only partially represents
the normalized timing/distribution requirement.

The separate locked distribution screen fills part of that predictive gap but
does not change the promotion rule. It finds small pooled incremental RMSE
reductions in most crop/holdout comparisons and a materially worse full-model
soybean temporal result. Therefore distribution is not privileged: it remains
a candidate extension whose null, unstable, and adverse results must be
reported.

The spatial split holds out entire grid cells and is observation-disjoint.
The audits reported before the purged-split revision operated on adjacent
first-difference pairs, so a training pair and a temporal or extreme test pair
could share one level-yield endpoint. Those reported values are legacy
dependent predictive stress tests, not clean outer holdouts. Production
promotion requires purging every training pair containing either endpoint of a
test pair, followed by row-count and support audits. A revised diagnostic must
receive a new configuration hash and be rerun; it cannot retroactively upgrade
the legacy metrics and remains noncausal even after a successful purge.
The evaluator and audit validator now implement the endpoint purge and pass
synthetic failure-mode tests. Corrected MIRCA-2000 maize and soybean minimal
diagnostics for 1982--1989 also pass under the current hash with zero shared
yield endpoints. Other real panels remain stale or pending, and these two
predictive reruns do not close causal, production-feature, welfare, or SCC
gates.

## Required production comparisons

The production analysis must distinguish three questions.

1. **Amount benchmark.** What is the joint temperature--yield response when
   precipitation is represented by total amount (and the declared heat and
   temperature terms)? The primary total is the crop-calendar growing-season
   total; calendar-year total is a documented benchmark/sensitivity, not a
   substitute for stage-aligned exposure. This parsimonious specification is
   the reference and may become the production primary if added pattern terms
   do not show stable incremental out-of-sample value.
2. **Direct precipitation-pattern candidate set.** Does adding crop-window
   amount, normalized stage timing/distribution, wet-day frequency, conditional
   intensity, CDD, Rx1day, Rx5day, and registered temperature interactions
   improve outer blocked performance and yield stable paired pulse/base
   predictions? Retain only supported extensions. These are required
   comparisons, not a rule to place every correlated encoding in one
   unrestricted regression or to favor complexity.
3. **Alternative drought families.** How do a climatic-water-balance family
   (SPEI or defensible self-calibrated PDSI) and a soil-moisture family perform
   under the same outer holdouts? PDSI/scPDSI and SPEI are serious competing
   crop-yield representations, especially in the U.S. validation; they replace
   the direct water-stress representation in their specifications. They are not
   additional covariates or damage terms unless a separately pre-specified
   attribution design demonstrates nonoverlap.

Model selection must be based on scientific validity, parsimony, stability,
common outer holdouts, and external validation—never on which candidate yields
the largest SCC. Null or worse distribution performance is a result, not a
failed analysis.

The primary reported impact is the full joint-climate prediction. A
precipitation-quantity versus distribution breakdown requires a
pre-registered counterfactual substitution or symmetric decomposition:
seasonal amount changes while normalized pattern is held fixed, and normalized
pattern changes while amount is held fixed, with the interaction reported.
This is an accounting attribution within a joint model, not a uniquely
identified causal precipitation coefficient.

## Decisions that remain open

The following must be resolved before the production specification is frozen:

- crop-specific phenological stages versus the current 0--30/30--70/70--100%
  engineering windows;
- wet-day and dry-day definitions, including whether more than one documented
  definition is retained as sensitivity analysis;
- crop-specific heat thresholds and the temperature response basis;
- a composition-respecting parameterization for stage precipitation shares
  and the nonlinear forms for amount, CDD, Rx1day, and Rx5day;
- which hot-dry and wet-heat interactions are identified in advance rather
  than searched on the full outcome panel;
- a projected climatic-water-balance implementation and an appropriate
  matched soil-moisture source;
- fixed effects, trend controls, spatial error treatment, partial pooling,
  and the training/outer-validation selection rule, including real-panel reruns
  and support audits under the purged observation-disjoint splits;
- treatment of radiation, vapor-pressure deficit, CO2 fertilization, calendar
  adaptation, irrigation, and water-supply constraints; and
- the production integration interface described below.

All threshold arrays in the production registry are intentionally empty. The
1 mm wet-day setting and heat/PDSI values used in existing software tests or
diagnostics are QA definitions, not production selections.

GDHY provides one aggregate crop-season-grid-year outcome. The production
outcome cell is therefore latitude--longitude--crop/season, not
latitude--longitude--crop--irrigation. Irrigation-specific nonlinear response
basis terms must first be combined under the separate aggregate-outcome
irrigation estimand; an irrigation fixed effect would falsely imply two yield
observations. Whether the production response uses levels with crop-year or
crop-by-year shocks, first differences with additional year-shock controls, or
a hierarchically pooled alternative remains an unresolved identification
choice.

## Integration boundary

`src/CropResponseAggregation.jl` currently exposes six broad feature slots and
a linear temperature-by-seasonal-precipitation interaction. It is useful for
testing coverage, accounting, adaptation, and replacement wiring, but it
cannot by itself document the full candidate feature basis or a nonlinear
response. Before SCC integration, choose and test one auditable interface:

- expand the Mimi component to accept the complete frozen response basis; or
- evaluate each response draw upstream and pass precomputed
  crop-region-year loss fractions to a simpler aggregation component.

The second option can preserve arbitrary validated nonlinear models, but it
requires a strict one-to-one provenance link from every loss draw to its
climate, response, calendar, irrigation, adaptation, and weighting draw. Until
one interface is selected and validated, the existing component remains a
plumbing harness and is not a production response.

## Evidence basis and limits

The registered feature comparisons follow the primary-source notes already in
the project: Fishman (2016) for amount versus rainy-day frequency; Lesk,
Coffel, and Horton (2020) for rainfall-intensity distributions; Troy, Kipgen,
and Pal (2015) for dry spells, Rx5day, and irrigation context; Li et al. (2019)
for excess-rainfall damage; Marcos-Garcia, Carmona-Moreno, and Pastori (2024)
for stage-wise dry/wet patterns; and Guan et al. (2015) for controlled amount,
frequency/intensity, onset, and duration perturbations. The drought-family
rules follow `DROUGHT_METRICS_PLAN.md`. These sources motivate comparisons;
none supplies a transferable global coefficient or an empirical threshold by
itself.
