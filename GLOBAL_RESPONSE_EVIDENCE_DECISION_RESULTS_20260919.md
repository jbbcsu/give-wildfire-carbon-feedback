# Evidence-led global agricultural-response decision

## Decision

**No empirical global response family is promoted to damages or SCC.** Seasonal
precipitation quantity plus temperature controls remains the parsimonious
research benchmark. Precipitation distribution and drought indices remain
separate sensitivity candidates. Published process-crop-model rainfall effects
remain structural benchmarks, not substitutes for the failed empirical gates.

This decision follows a rule written after the contributing results were known;
it is a transparent evidence synthesis, not new holdout validation. The source
country-held-out result itself sets `production_promotion_authorized=false`,
uses no new independent outcomes, and is not a new untouched holdout.

## Why no family passes

| Candidate | Maize country folds | Maize result | Soy country folds | Soy result | Promotion |
|---|---:|---|---:|---|---|
| Seasonal quantity | 5 | Better point RMSE than heat and zero change, but paired intervals cross zero | 4 | Worse than zero change; no supported bootstrap | No |
| Quantity + distribution | 5 | Worse than quantity on both pooled and equal-country point RMSE; paired intervals cross zero | 4 | Worse than quantity on both weightings; no supported bootstrap | No |
| Seasonal scPDSI | 5 | Weighting-dependent and paired intervals cross zero | 4 | Worse than quantity; no supported bootstrap | No |
| Stage scPDSI | 5 | Weighting-dependent and paired intervals cross zero | 4 | Worse than quantity; no supported bootstrap | No |

The maize quantity-minus-heat 95% paired upper bounds are +0.000391 pooled and
+0.000611 equal-country RMSE; quantity-minus-zero upper bounds are +0.004999
and +0.001499. Distribution-minus-quantity point RMSE is +0.000371 pooled and
+0.000089 equal-country, with both intervals spanning zero. Thus even the most
favorable historical candidate does not meet the fixed cross-weighting rule.

## Climate evidence does not override yield evidence

All six same-realization end-century scenario/GMST endpoint ratios show fewer
wet days, longer maximum dry spells, and larger Rx1day and Rx5day. This supports
reporting distributional climate changes. However, future cell-weather is
outside the 1982--2016 same-cell min/max on 18.3--33.5% of area for wet days,
7.1--13.1% for maximum dry spell, 5.3--21.0% for Rx1day, and 5.9--20.3% for
Rx5day. Seasonal rainfall is outside on 7.6--19.5% and mean temperature on
37.0--100%. The climate signal therefore adds transport risk; it does not prove
incremental crop-yield predictability.

The manuscript hierarchy is consequently:

1. report seasonal-quantity, distributional, and drought climate changes;
2. use quantity plus temperature only as a parsimonious research comparator;
3. report distribution and drought null/worse predictive results plainly;
4. do not monetize any empirical response until independent predictive and
   transport gates pass; and
5. retain EPIC/CARAIB differences as structural uncertainty, not as an
   empirically selected damage function.

## Reproduction and audit

The builder reads six aggregate JSON artifacts and no row-level yield or raw
climate. A separate implementation rehashes all sources and repeats 48 decision
checks. It passes. The first builder output incorrectly counted `evaluated`
folds as zero because it expected the label `scored`; that output and receipt
are retained but rejected. The corrected v2 also enforces the predeclared
quantity comparisons against both heat controls and zero change.

- Protocol: `GLOBAL_RESPONSE_EVIDENCE_DECISION_PROTOCOL_20260919.md`
- Builder: `scripts/build_global_response_evidence_decision.py`
- Independent audit: `scripts/validate_global_response_evidence_decision.py`
- Ignored corrected result SHA-256: `63f5bf6f9bc92752652bba68f9400add2f690c64f3a0a52436bcc93bfd530d72`
- All numerical work stayed below 2 MiB sampled RSS and added under 20 KiB.
