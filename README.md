# Climate-driven air-pollution damages for GIVE

This isolated project evaluates transferable air-pollution damage functions
for addition to GIVE. It does not modify the separate wildfire-carbon,
precipitation-agriculture, labor, or fisheries projects.

## Pathways

1. **Wildfire smoke PM2.5 mortality.** Reproduce the investigator-supplied
   Williams et al. draft before integration. The draft's provisional global
   partial SCC is $50/tCO2 (conditional 95% interval $18.5-$102.6), but it is
   not yet a locally reproduced result. The fail-closed admission audit in
   [`WILLIAMS_WILDFIRE_SMOKE_ADMISSION_GATE.md`](WILLIAMS_WILDFIRE_SMOKE_ADMISSION_GATE.md)
   currently admits 0 of 8 required operational artifact groups. It also
   preserves unresolved 100-versus-10,000-trial and 275-versus-276-year source
   conflicts rather than choosing values silently.
2. **Meteorologically driven surface ozone.** Replicate McDuffie et al. (2026),
   DOI `10.1021/acs.est.5c14713`, using the official EPA reduced-form code.
3. **Non-wildfire meteorological PM2.5.** Retain as a separate pathway because
   the published result is a benefit on average and explicitly excludes open
   burning. It must not be conflated with wildfire smoke PM2.5.
4. **Wildfire CO2 feedback.** Import only the reviewed marginal-damage output
   from the separate project. This is a carbon-cycle pathway, not direct
   air-pollution mortality.

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
All article-reproduction, non-wildfire-boundary, and GIVE-transfer gates remain
closed.

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
