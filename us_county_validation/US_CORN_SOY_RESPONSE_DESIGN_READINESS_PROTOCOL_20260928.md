# Outcome-blind corn/soy response-design readiness protocol

This audit asks whether the existing direct-practice county panels can support
a later, frozen historical response specification. It does not read yield
values, fit a response, export coefficients, or authorize national, causal,
damage, or SCC claims. Non-irrigated corn and soybean are the priority strata;
irrigated outcomes are audited separately on exactly paired exposure rows.

The executable contract is
`us_corn_soy_response_design_readiness_v1.toml`. Every candidate uses county
and state-by-harvest-year fixed effects and a later county-clustered CR1
inference convention. The quantity family contains linear and quadratic total
rainfall. The distribution family contains that same quantity basis plus the
previously frozen dry-spell, wet-day, intensity, heavy-rain, concentration,
and two-of-three stage-share extension. The PDSI family contains linear and
quadratic seasonal PDSI. All three retain linear and quadratic stage-mean
temperature controls. They are separate fits; direct rainfall, PDSI, and SPEI
must never be stacked. SPEI fails closed because no validated direct-practice
county-crop SPEI panel currently exists.

Before any outcome is inspected, the audit freezes minimum support, terminal
support, leave-one-state support, within-FE variation, numerical rank,
standardized condition number, VIF, row leverage, county-cluster leverage,
state concentration, and effective-cluster thresholds. It also requires exact
practice-pair exposure identity and exact common direct/PDSI keys. Diagnostics
are computed separately by crop, practice, and family; identical practice
designs must produce identical diagnostics.

Passing means only that a later historical association protocol can be frozen
without obvious support or numerical-identification defects. County clustering
is conditional inference, not a solution to all spatial dependence. A
geographic influence analysis and an explicitly spatial covariance or
dependence sensitivity remain manuscript-promotion requirements.
