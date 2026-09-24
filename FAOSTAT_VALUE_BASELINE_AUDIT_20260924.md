# FAOSTAT maize-value baseline audit

## Decision

Monetary promotion is blocked pending a revised price-basis sensitivity. The
constant-2014--2016-USD field is reproduced exactly, but it fails the project's
cross-country plausibility review as a maize market baseline. This does not
affect the production-weighted yield-response results.

## Material finding

Venezuela's 1999--2001 mean maize value is US$16.646 billion in the selected
constant-dollar field. This is 11.62% of the matched global value and
US$10,400 per MapSPAM tonne. The same FAOSTAT records report a mean current-
dollar value of US$0.402 billion, so the constant/current ratio is 41.45. The
constant values are flagged `Estimated value`; the Venezuelan current-dollar
values are flagged `Official value`.

Diagnostic review thresholds—US$2,000 constant dollars per MapSPAM tonne or a
constant/current ratio above 10—also flag Jamaica, Kuwait, and Saint Vincent
and the Grenadines. These thresholds are review triggers only. They are not
caps, winsorization rules, or replacement values.

The official FAOSTAT catalog describes the domain as farm-gate production
value, reports current and constant US dollars, and identifies 2014--2016 as
the constant-price base. That confirms the requested field but does not resolve
whether the Venezuelan cross-country magnitude is suitable for this market
application.

## Consequence

The conditional value-weighted, fixed-price, global-market, national-market,
and FUND-incidence dollar results remain transparent arithmetic sensitivities
to the declared field, but they are not publication-ready evidence and are not
passed to GIVE. No country is deleted, capped, or reassigned. A leave-one-out
calculation selected after seeing the anomaly would not solve the price-basis
problem.

The next registered sensitivity should use countries with complete
1999--2001 current-USD values, convert each annual observation to a common
price year using a pinned official deflator, retain missing countries, and
compare the resulting support and weights against the constant-dollar case.
It must be selected on source comparability rather than on the resulting
damage magnitude.

That alternative input is now constructed, but not yet passed through the
market model. Requiring all three 1999--2001 current-USD observations and
rebasing each year with the pinned U.S. GDP implicit price deflator retains
110 MapSPAM-matched countries, 97.88% of MapSPAM maize production, and
US$97.272 billion. Venezuela becomes US$0.537 billion, or 0.552% of this
alternative total. The change shows that price-basis selection is material;
it does not by itself establish that the GDP-wide deflator matches farm-gate
prices or authorize the alternative as the primary welfare calibration.
Receipt:
`data/provenance/hultgren_country_cell_maize_value_weights_current_rebased_20260924.json`.

Machine-readable audit:
`data/provenance/faostat_maize_value_plausibility_audit_20260924.json`.
The country/FUND diagnostic that exposed the issue and its independent
aggregation audit are retained under `data/provenance/` but should not be
interpreted substantively.

Primary documentation: [FAOSTAT Value of agricultural production](https://data.fao.org/catalog/dataset/b1a04191-c86f-4972-a9d7-28b23568deba).
