# Climate-driven air-pollution damages for GIVE

This isolated project evaluates transferable air-pollution damage functions
for addition to GIVE. It does not modify the separate wildfire-carbon,
precipitation-agriculture, labor, or fisheries projects.

## Pathways

1. **Wildfire smoke PM2.5 mortality.** Reproduce the investigator-supplied
   Williams et al. draft before integration. The draft's provisional global
   partial SCC is $50/tCO2 (conditional 95% interval $18.5-$102.6), but it is
   not yet a locally reproduced result.
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

Run the fail-closed summary audit with:

```bash
python3 scripts/validate_upstream_summaries.py
```

## Combination rules

- Air-pollution mortality is audited against GIVE mortality valuation and
  country-year baseline deaths.
- Wildfire smoke and non-wildfire PM2.5 remain disjoint by construction.
- Surface ozone mortality and ozone crop losses are separate endpoints; any
  future crop module is audited against the agriculture replacement.
- Shared fire and climate inputs may be reused, but each physical emission,
  exposure, health endpoint, and downstream climate effect is valued once.
