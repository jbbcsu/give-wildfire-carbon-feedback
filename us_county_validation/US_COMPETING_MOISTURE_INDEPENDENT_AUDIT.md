# Independent audit: U.S. competing-moisture predictive diagnostic

## Status

**CLEAR.** A standalone implementation rebuilt 23,722 common crop-county-
practice-year levels and 20,228 consecutive-year first differences directly
from the bound raw direct-weather, PDSI, and calendar tables. It did not import
the registered builder, evaluator, or validator. It recreated every split and
endpoint purge and fit the 120 aggregate model/split rows with reduced QR plus
a triangular solve. SVD was used only to audit the registered rank cutoff, not
to solve the regressions.

The independent results agree with the registered aggregate metrics to at
most `4.44e-16` for RMSE, `3.33e-16` for MAE, `2.00e-15` for out-of-sample
R-squared, `1.08e-15` for correlation, and `8.88e-16` for the reported
singular-value ratio. Every integer and Boolean field—including split sizes,
endpoint-purge counts, retained-column counts, and rank—matches exactly. The
promotion summaries agree to at most `3.89e-16`.

The audited registered artifacts are:

- `results.json`: `12d32bec7b9ff6a74339123f95b9282263fdc7675280d9a019c1710dcaaf0b66`
- `validation.json`: `778e2fbc2f1dd2351eb0ad91bd1565a7bb7582d68c42b88434ab0c67f697d28c`

The machine-readable receipt is
[`../data/provenance/us_competing_moisture_independent_audit_20260826.json`](../data/provenance/us_competing_moisture_independent_audit_20260826.json).
Its SHA-256 is
`3e159b495336257869d01698657375a772bfa71a99150c1758e2bdbe797f5283`.

## Substantive predictive summary

All values below are `quantity-only RMSE - alternative RMSE`; positive values
mean the named alternative has lower held-out RMSE. “Dev mean” is the mean over
eligible leave-one-state-out tests. State counts show how many eligible states
favor the alternative. Only the distribution-extension development gate is a
predeclared selection rule; terminal and extreme results are separate
confirmation/stress tests.

| Crop/practice | Distribution extension | Seasonal PDSI | Stage PDSI sensitivity |
|---|---|---|---|
| Corn, irrigated | **FAIL** (material floor in 1/5 states); dev mean `-0.001531`; terminal `-0.002852`; extreme `-0.002046` | dev mean `+0.000786` (4/5); terminal `+0.000690`; extreme `+0.005340` | dev mean `-0.000533` (2/5); terminal `+0.000140`; extreme `+0.003895` |
| Corn, non-irrigated | **FAIL** (4/5; South Dakota reverses); dev mean `+0.005854`; terminal `+0.060342`; extreme `+0.006075` | dev mean `+0.015309` (5/5); terminal `+0.049216`; extreme `+0.032397` | dev mean `+0.018826` (5/5); terminal `+0.045035`; extreme `+0.039544` |
| Soybeans, irrigated | **PASS** (3/3); dev mean `+0.003862`; terminal `-0.012312`; extreme `+0.001760` | dev mean `-0.000629` (1/3); terminal `+0.002253`; extreme `-0.000930` | dev mean `-0.002004` (1/3); terminal `-0.000168`; extreme `-0.001406` |
| Soybeans, non-irrigated | **PASS** (3/3); dev mean `+0.012279`; terminal `+0.058268`; extreme `+0.028115` | dev mean `+0.004819` (2/3); terminal `+0.025360`; extreme `-0.003682` | dev mean `+0.004191` (2/3); terminal `+0.035792`; extreme `+0.006672` |

Thus, the distribution extension clears its development rule for both soybean
practice strata, but the irrigated-soy terminal result reverses. It does not
clear for either corn stratum: irrigated corn is also unfavorable in both
outer tests, while non-irrigated corn is favorable in both outer tests but is
blocked by South Dakota in development. Seasonal and stage PDSI both look
strong relative to quantity-only for non-irrigated corn. Their advantages are
smaller or geographically mixed in the other strata.

## Integrity checks and limitations

- The direct and PDSI raw tables have exactly the same 23,722 locked level
  keys, outcomes, fixed-calendar lineage, and practice-shared exposures. The
  independently self-joined difference keys and every stored difference value
  match the three analysis tables exactly.
- Leave-state-out groups, terminal same-county exclusions, precipitation-tail
  cutoffs, and level-endpoint purges were independently recreated. Terminal
  purges remove 84 training rows per corn practice and 56 per soybean practice;
  extreme purges remove 1,188 and 934, respectively. No endpoint remains shared.
- Centering, scaling, year terms, variance floors, and design matrices use
  training rows only. All 120 designs retain every candidate column and are
  full rank. The minimum retained/largest singular-value ratio is `0.04930`,
  far above the registered `1e-10` cutoff, so the cutoff is inactive here.
- Model feature sets are mutually exclusive: no regression combines direct
  precipitation and PDSI. The results and receipt contain neither coefficients
  nor row predictions.
- The eligible development holdouts are regional: CO, KS, ND, NE, and SD for
  corn; AR, KS, and NE for soybeans. States below the 50-row threshold remain
  in training but are not scored alone. These results are not a national or
  structural ranking of moisture measures.
- This audit validates the immediate hash-bound feature, index, calendar, and
  analysis tables. It does not independently recompute daily nClimGrid weather,
  monthly NOAA PDSI, county aggregation weights, or the 2010 calendar from its
  publisher PDF. It also does not assess wheat.
- The exercise measures held-out prediction of annual county yield changes
  under fixed historical specifications. It provides no causal climate-yield
  effect, damage function, welfare estimate, or SCC input.

Reproduce the independent audit and its synthetic fail-closed checks with:

```bash
PYTHONWARNINGS=error ./.venv/bin/python \
  us_county_validation/scripts/test_independent_audit_us_competing_moisture.py -v

PYTHONWARNINGS=error ./.venv/bin/python \
  us_county_validation/scripts/independent_audit_us_competing_moisture.py \
  --out data/provenance/us_competing_moisture_independent_audit_20260826.json
```
