# Closed-market accounting prototype

September 7, 2026. Implemented and tested, **uncalibrated and synthetic-only**.
This is an independent mathematical implementation, not a replication of
Hultgren et al.'s detailed valuation method and not a damage or SCC estimate.
No external source code was copied, installed, or executed.

## Scope and equations

`src/constant_elasticity_market.py` describes one closed market. Baseline price
and quantity are normalized to one; R is their actual value product supplied
by a future, independently validated calibration. Positive elasticities e_s
and e_d denote supply elasticity and the magnitude of demand elasticity.
The user of the function must specify both, R, and a value-unit label. There
are no empirical parameter defaults.

With log supply shifter s, declare Q_s=exp(s) P^e_s and Q_d=P^(-e_d).
Market clearing gives log P=-s/(e_s+e_d) and log Q=-e_d log P.
Consumer-surplus CHANGE is -R times the integral of P^(-e_d) from 1 to P;
producer-surplus change is R times (P Q-1)/(1+e_s), using the resource cost
obtained by integrating inverse supply. No level consumer surplus is needed,
which avoids an inappropriate integral to infinite willingness to pay.
These are partial-equilibrium surplus measures with no income effects, not
automatically general-equilibrium equivalent variation or distributional welfare.

For two supply states s_0 and s_0+delta, define l_0=-s_0/(e_s+e_d),
d=-delta/(e_s+e_d), z=(1-e_d)d and A=R exp((1-e_d)l_0). Then:

- change in consumer surplus: -A d exprel(z);
- change in producer surplus: A expm1(z)/(1+e_s);
- total surplus change: A delta exprel(z)/(1+e_s);
- derivative of total surplus at s_0: A/(1+e_s).

Here exprel(z)=expm1(z)/z with value one at zero. This expression handles
unit-elastic demand and tiny supply increments without subtracting large
nearly equal level values. Positive surplus change is a benefit; the returned
damage change has the opposite sign. This is NOT yet an emissions-pulse
mapping, although numerical stability would matter for such a future mapping.

## A yield shock is not a supply shifter by definition

The helper requires an explicit convention, with no automatic choice:

1. A horizontal output shift by productivity factor a implies s=log(a).
2. Holding the baseline input-cost schedule fixed while producing a times
   as much output, C_a(q)=C_0(q/a), implies s=(1+e_s)log(a).

The second result follows by differentiating the cost schedule: marginal
cost scales by a^(-1-1/e_s). Thus the local surplus derivative with respect
to log(a), at the normalized baseline, is R/(1+e_s) under the first convention
but R under the second. Both are explicitly hypothetical conventions. Neither
has been identified as the published paper's convention or selected for GIVE.
Treating them as interchangeable would silently change valuation.

The module does not estimate adaptation, model trade between markets, identify
crop price/calorie conversions, value missing crops or livestock, convert
currency years, discount, or consume the historical association outputs.
Adaptation costs and CO2 effects must not be counted again if already included
in a future productivity shock. Broader markets need regional incidence
accounting before FUND-region aggregation. This prototype does not replace
`JointAgriculture` or alter GIVE's current component graph.

## Tests and provenance

`scripts/test_constant_elasticity_market.py` passes seven synthetic tests:
market clearing/zero shock; independent numerical surplus integrals;
consumer-plus-producer accounting; demand elasticity approaching one;
tiny increments and centered-derivative convergence; level/pair and unit
scaling agreement; explicit mapping choices and invalid-domain rejection.
The numerical inputs are artificial fixtures, not observations or calibration.

The final test run was monitored at 512 MiB, with one numeric thread and
starting disk space minus 64 MiB. It completed in 0.103 seconds; sampled RSS
was 22,659,072 bytes (21.61 MiB). This very short job's sampled maximum is not
a measured continuous/kernel peak. No research data or PDF was saved.
Receipt: `data/provenance/welfare_accounting_prototype_20260907.json`.

## Publication/replication review status

The general market approach was motivated by the verified main Methods of
[Hultgren et al. (2025)](https://www.nature.com/articles/s41586-025-09085-w).
The detailed [supplement](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41586-025-09085-w/MediaObjects/41586_2025_9085_MOESM1_ESM.pdf)
could not be inspected: the web reader rejected its reported 34,800,087-byte
size. Local download was not attempted under the current below-150-GiB rule.
Author research pages returned the journal link, and the SSRN reader returned
403. **Section K equations and elasticity calibration remain unverified.**

Public GitLab metadata was inspectable without cloning. At commit
`3ccdffcd4e4ff6e55566ce76e2aac130ee86349a`, the
[Figure 3 notebook](https://gitlab.com/ClimateImpactLab/cil-ag-replication-package/-/blob/3ccdffcd4e4ff6e55566ce76e2aac130ee86349a/Fig3/3d_damages/main_code/calorie_damage_function_figure.ipynb)
is 735,531 bytes (SHA-256 in receipt). A capped in-memory inspection found
15 code cells, calorie-data inputs and fits against GMST. It did not establish
a reusable monetary valuation routine. The nearby `agval/utils` listing
contained weighting/filesystem helpers. No root license file was listed;
this is not an exhaustive repository licensing determination. Do not infer
that all unpublished code is absent or freely reusable.

## Next step and process state

No analysis subprocess remains running after the tests. The active heartbeat
continues the project. Do not repeat the completed historical fits or this
repository search. Obtain permission for a narrowly bounded supplement
download (under 36 MiB) or a readable supplied copy, then verify section K
against this prototype and locate the authors' valuation-specific package.
Independent local climate/response work need not stop for that document.
Next independent executable task: inspect the retained
`data/interim/welfare_weights/mapspam2000_maize_soy_production.csv` schema and
its validated GEC/GENC country-code receipt for a country-to-GDHY-cell
crosswalk. Determine resolution, border ambiguity and matched support before
fitting anything. If usable, register country-year controls as an exploratory
global response sensitivity; current global-year controls do not remove
country-specific annual shocks. Do not infer administrative identity from
yield values, use outcomes to select a border rule, or call this a causal fix.
No empirical damage estimate may be filled in to bypass the missing mapping,
calibration, climate transport, crop coverage or welfare-incidence decisions.
