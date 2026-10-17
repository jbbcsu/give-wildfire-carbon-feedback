# Climate-driven air-pollution damages for GIVE

This isolated project evaluates transferable air-pollution damage functions
for addition to GIVE. It does not modify the separate wildfire-carbon,
precipitation-agriculture, labor, or fisheries projects.

## Pathways

1. **Wildfire smoke PM2.5 mortality.** Reproduce the investigator-supplied
   Williams et al. draft before integration. The draft's provisional global
   partial SCC is $50.04/tCO2 (rounded headline $50; conditional 95% interval
   $18.5-$102.6), but it is not yet a locally reproduced result. The source
   uses 100 Monte Carlo simulations; 10,000 is a future production-reproduction
   target, not a replacement for the source-reported trial count. The
   fail-closed admission audit in
   [`WILLIAMS_WILDFIRE_SMOKE_ADMISSION_GATE.md`](WILLIAMS_WILDFIRE_SMOKE_ADMISSION_GATE.md)
   currently admits 0 of 8 required operational artifact groups. It also
   preserves the unresolved 275-versus-276-year horizon ambiguity rather than
   choosing a value silently.
2. **Meteorologically driven surface ozone.** Replicate McDuffie et al. (2026),
   DOI `10.1021/acs.est.5c14713`, using the official EPA reduced-form code.
3. **Non-wildfire meteorological PM2.5.** Retain as a separate pathway because
   the published result is a benefit on average and explicitly excludes open
   burning. It must not be conflated with wildfire smoke PM2.5.
4. **Wildfire CO2 feedback.** This is a carbon-cycle pathway, not direct
   air-pollution mortality. The present module records the endpoint distinction
   but does not read from or depend on that separate project's working files.

## Current EPA fast-route audit

The official repository was acquired at commit
`1139e7aff1ca7806b6b542268e829f9759dd8808` under its MIT code license and
CC-BY-4.0 data license. The peer-reviewed article reports, at a 2% Ramsey
discount rate, global means of +$23/tCO2 for ozone, -$38/tCO2 for PM2.5, and
-$15/tCO2 net. It uses two GCMs, 10,000 RFF socioeconomic paths, country-level
impact-per-degree functions, and a marginal CO2 perturbation.

The checked-in upstream summaries do **not** numerically reproduce those final
article values. Equal weighting of the two GCM rows in
`npd_global_rff_means.csv` gives +$16.67/tCO2 for ozone and -$24.53/tCO2 for
PM2.5. The separate checked-in net summary gives -$34.67/tCO2, which also does
not equal the sum of those component means. The repository commit predates the
final 2026 article and lacks the full intermediate parquet set expected by the
NPV script. Therefore the article values remain published external benchmarks,
not local reproductions, until the final input/output release is identified or
the model is rebuilt from its documented inputs.

A current official-source reconciliation confirms that this is not resolved by
a newer public version. As of 2026-10-13, the EPA repository still exposes only
the 2025-09-29 submission commit, with no release or tag. Its 33-entry tree has
no Parquet stream or dependency lock. A second checked-in mean-path summary
also misses the article components (+$20.66 ozone and -$21.91 PM2.5), while the
10,000-path component and net summaries are not additive to each other. The
exact versioned author-artifact request is documented in
[`EPA_GLOBALAQ_FINAL_RELEASE_ARTIFACT_REQUEST_20261013.md`](EPA_GLOBALAQ_FINAL_RELEASE_ARTIFACT_REQUEST_20261013.md).
The primary article and Supporting Information now resolve the published
currency year as 2024 USD and explicitly exclude open-burning emissions,
including wildfires. The public-repository reproduction and GIVE-transfer gates
remain closed.

## Executable literature bridge

The project now exports a small, independently validated table that gives the
GIVE integration layer a common schema for four source-reported scalar partial
SCC benchmarks: wildfire-smoke PM2.5 mortality, surface ozone health,
non-wildfire meteorological PM2.5 health, and the published ozone-plus-PM2.5
net. This is the shortest defensible executable route while the annual
country-level damage streams are unavailable. It deliberately does not turn a
published or draft scalar into a local reproduction or an additive SCC result.

The source-value evidence table preserves the different pulse years (2025 for
the smoke draft and 2030 for the EPA article), records the article's 2024 price
year, and labels the smoke interval as conditional. A second target interface
converts the EPA scalars to 2020 USD with a pinned BEA GDP deflator. It
does not falsely convert the 2030 pulse to 2025 or invent annual paths. Wildfire
smoke and non-wildfire PM2.5 remain separate rows.

Build and independently validate it with:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build_air_pollution_literature_bridge.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_air_pollution_literature_bridge.py
PYTHONDONTWRITEBYTECODE=1 python3 test/test_air_pollution_literature_bridge.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build_air_pollution_target_interface.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_air_pollution_target_interface.py
PYTHONDONTWRITEBYTECODE=1 python3 test/test_air_pollution_target_interface.py
```

The generated interface is
`data/derived/air_pollution_literature_bridge_v1.csv`. It is suitable for
evidence registries and benchmark comparison, not for a headline GIVE total.
The price-harmonized target table is
`data/derived/air_pollution_target_interface_v1.csv`; its exact gates and
interpretation are documented in
[`AIR_POLLUTION_TARGET_INTEGRATION_GATE.md`](AIR_POLLUTION_TARGET_INTEGRATION_GATE.md).

## Wildfire-smoke normalization and additivity decision

The confidential draft has now been directly hash-verified and its detailed
mean normalized without arithmetic conversion: $50.04/tCO2, 2025 pulse, 2020
USD, and a source-reported 2% discount rate. The target GIVE discount contract
pins the 2.0% near-term Ramsey parameters (`prtp = exp(0.001972641) - 1`,
`eta = 1.244458999`). Exact joint addition still requires annual country-draw
damage paths because GIVE's net-consumption discount factors change when a
damage sector is added.

The physical wildfire/nonwildfire emissions boundary is separable, because the
EPA benchmark excludes open burning. The mortality accounting boundary is not
yet cleared: the two PM2.5 studies use different health-risk functions, and
baseline GIVE temperature mortality is net all-cause mortality whose evidence
base may include air pollution as a mediator or modifier. Both additivity flags
therefore remain closed. The full assessment is in
[`WILDFIRE_SMOKE_ADDITIVE_INTEGRATION_ASSESSMENT.md`](WILDFIRE_SMOKE_ADDITIVE_INTEGRATION_ASSESSMENT.md).

Build and independently validate the pinned smoke contract with:

```bash
python3 scripts/build_wildfire_smoke_integration_contract.py \
  --source-pdf "/Users/jbb/Downloads/Fire_SC_CO2_draft (1).pdf"
python3 scripts/validate_wildfire_smoke_integration_contract.py \
  --source-pdf "/Users/jbb/Downloads/Fire_SC_CO2_draft (1).pdf"
PYTHONDONTWRITEBYTECODE=1 python3 test/test_wildfire_smoke_integration_contract.py
```

Run the fail-closed summary audit with:

```bash
python3 scripts/validate_upstream_summaries.py
python3 scripts/audit_release_reconciliation.py
python3 test/test_release_reconciliation.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_williams_wildfire_smoke_admission.py
PYTHONDONTWRITEBYTECODE=1 python3 test/test_williams_wildfire_smoke_admission.py
```

## Combination rules

- Air-pollution mortality is audited against GIVE mortality valuation and
  country-year baseline deaths.
- Wildfire smoke and non-wildfire PM2.5 remain disjoint by construction.
- Surface ozone mortality and ozone crop losses are separate endpoints; any
  future crop module is audited against the agriculture replacement.
- Shared fire and climate inputs may be reused, but each physical emission,
  exposure, health endpoint, and downstream climate effect is valued once.
