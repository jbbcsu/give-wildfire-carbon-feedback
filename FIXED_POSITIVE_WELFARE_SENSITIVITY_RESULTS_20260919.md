# Fixed-positive partial-support welfare sensitivity

## Result

The four-corner welfare attribution has been repeated on one fixed support that
is positive in every corner of every CARAIB and EPIC-TAMU case. The mask retains
109.023 billion USD2005 of baseline value and excludes 24.584 million
(0.02254%) without redistribution or rescaling. All 96 economic cases are now
mechanically evaluable, but every result remains a partial-support structural
sensitivity.

For cases already admissible on full support, the central horizontal-output
precipitation attribution is stable in sign and close in level. The largest
central change is EPIC GFDL/SSP1-2.6: the estimated precipitation benefit falls
from 2.787--2.820 to 2.661--2.694 billion USD2005, a 0.126-billion change.
Other central precipitation changes are at most about 0.011 billion. Across
all elasticity/mapping sensitivities, the largest absolute restricted-minus-
full precipitation difference is 0.247 billion, and the largest joint-damage
difference is 0.238 billion.

The previously inadmissible EPIC IPSL/SSP5-8.5 case becomes arithmetically
positive on the fixed restricted support. Under the central horizontal-output
case, its precipitation Shapley contribution is a benefit of 0.346--0.368
billion USD2005, temperature damage is 22.416--22.465 billion, and joint damage
is 22.048--22.097 billion. These values describe only the retained population;
there is no valid full-support comparison and they are not promoted.

## Interpretation

The main admissible-case conclusions are not driven by the 0.02254% of value
with a nonpositive corner: precipitation remains beneficial in the SSP1-2.6
structural cases and a small loss in the previously admissible SSP5-8.5 cases.
However, excluding a tiny value share can move the EPIC precipitation component
by more than 0.1 billion because affected cells can have extreme relative
responses. This reinforces the need to report tail validity, not just coverage.

The sensitivity does not repair the polynomial emulators or authorize choosing
the restricted support because it is convenient. It changes the estimand from
the full common footprint to a fixed all-case-positive partial footprint. No
renormalization, case-specific exclusion, clipping, welfare selection or damage
truncation is used.

These remain period-mean, quantity-only, maize structural results under a
single global market and fixed management. They omit within-season rainfall
distribution, drought, annual pulse paths, trend/upper adaptation and empirical
response validation. They cannot enter GIVE or SCC.

## Reproduction

- Protocol: `FIXED_POSITIVE_WELFARE_SENSITIVITY_PROTOCOL_20260919.md`.
- Builder: `scripts/build_fixed_positive_welfare_sensitivity.py`.
- Independent validator: `scripts/validate_fixed_positive_welfare_sensitivity.py`.
- Ignored result SHA-256:
  `303344d73dfa6b76cc890a8de81df380dbb883225b6c018d1894e07a8a7359ec`.
- Validation output SHA-256:
  `b87898f639acecddc9ea1d83e18f2fe2a0d75cfd9bcd53afeef05a08571e2de3`.
- Independent validation passed 1,929 checks. Builder/validator sampled peaks
  were 151.37/175.11 MB and added less than 0.19 MB combined.

All crop-model-repair, empirical-damage, agriculture-replacement, GIVE-export
and SCC flags remain false.
