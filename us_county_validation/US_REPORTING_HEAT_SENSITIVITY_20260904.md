# U.S. reporting-period and temperature-control sensitivity

Specification recorded before executing this sensitivity. This is a new
exploratory robustness analysis; earlier model selection and results are known.
It does not reuse development holdouts as independent confirmation.

Use the exact source-validated direct-practice panel and existing county and
state-year fixed effects. Estimate both quantity and quantity-plus-timing
forms separately for corn/soy and reported irrigated/non-irrigated practice.
Retain the original county-clustered uncertainty estimator.

Evaluate three prespecified variants: original 1981–2018 specification;
1981–2018 with the three stage-average daily maximum temperatures and their
squares added to the existing stage mean-temperature controls; and the
2000–2018 reporting-period restriction with the original controls. Retain all
variants and failed sample/numerical checks. No model is selected by its result.

Stage-average maximum temperature is not extreme-heat degree-days. This is a
temperature-control sensitivity only. Report early-to-middle/late timing and
rainfall-quantity contrasts with their conditional interpretation. Percentile
reference rainfall changes with the period sample, so restricted-period
contrasts are not evaluated at identical rainfall levels.

All calculations read existing data, run sequentially under a 1 GiB sampled
process-group monitor and write a compact result. The low-write job preserves
the measured starting free space minus 64 MiB; it does not authorize bulk
downloads below the 150 GiB acquisition reserve.
