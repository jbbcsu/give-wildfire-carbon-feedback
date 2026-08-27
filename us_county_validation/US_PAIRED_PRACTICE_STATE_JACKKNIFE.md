# U.S. paired-practice state jackknife

Status: historical support-sensitivity diagnostic only; not causal, nationally
representative, a global transfer parameter, a damage function, or an SCC
input.

The registered paired-practice association is estimated on selected counties
that report irrigated and non-irrigated yields under the same county weather
proxy. This audit removes each represented state once, refits the exact
registered quantity and quantity-plus-timing forms, and reports the range and
sign stability of the predeclared rainfall contrasts.

The audit is hash-bound to the original panel, contract, registered result,
and implementation. It first reproduces the registered full-sample contrasts,
then requires every represented state to be omitted exactly once while all
minimum-row and minimum-county gates continue to pass. State omission is a
support diagnostic, not a state-clustered causal design or a correction for
practice selection, soil, management, reporting, or crop-pixel exposure error.

The real audit omits each of ten represented corn states and five represented
soybean states. Every leave-one-state-out rainfall-quantity contrast retains
the full-sample negative sign: 10/10 corn omissions in each form and 5/5
soybean omissions in each form. The corn 100 mm contrast ranges from -0.0910
to -0.0719 log points in the quantity form and from -0.0907 to -0.0733 in the
timing form. Soybean ranges are -0.0477 to -0.0322 and -0.0501 to -0.0344.
The stage-3-to-stage-2 timing contrast also remains negative in every omission,
ranging from -0.0503 to -0.0215 log points for corn and -0.0554 to -0.0332 for
soybeans. Sign stability narrows one support concern but does not resolve the
diagnostic's selection, exposure, or causal limitations.

Reproduce with:

```bash
./.venv/bin/python \
  us_county_validation/scripts/test_us_paired_practice_state_jackknife.py

./.venv/bin/python \
  us_county_validation/scripts/audit_us_paired_practice_state_jackknife.py \
  --out data/provenance/us_paired_practice_state_jackknife_20260827.json
```
