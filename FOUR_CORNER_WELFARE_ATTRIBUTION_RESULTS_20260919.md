# Four-corner welfare attribution: precipitation is small and model-dependent

## Main finding

The project now has a nonlinear, order-symmetric welfare attribution for the
resident structural maize benchmarks. Welfare is evaluated at all four
temperature/precipitation crop-model corners before assigning the interaction;
the precipitation yield contribution is never treated as an independent supply
shock. An independent implementation passed 3,081 checks.

Under the central 0.10/0.04 elasticity pair, horizontal-output mapping, one
global maize market and fixed management, billion-USD2005 damages are:

| Crop model / climate case | Precipitation Shapley damage | Temperature Shapley damage | Joint damage |
|---|---:|---:|---:|
| CARAIB / GFDL SSP1-2.6 | −0.337 to −0.328 | 9.387 to 9.397 | 9.049 to 9.069 |
| CARAIB / GFDL SSP5-8.5 | 0.008 to 0.014 | 14.203 to 14.228 | 14.211 to 14.241 |
| CARAIB / IPSL SSP1-2.6 | −0.063 to −0.057 | 13.801 to 13.813 | 13.738 to 13.757 |
| CARAIB / IPSL SSP5-8.5 | 0.014 to 0.022 | 23.690 to 23.706 | 23.703 to 23.728 |
| EPIC-TAMU / GFDL SSP1-2.6 | −2.820 to −2.787 | 7.548 to 7.566 | 4.728 to 4.779 |
| EPIC-TAMU / GFDL SSP5-8.5 | 0.119 | 12.350 to 12.378 | 12.469 to 12.497 |
| EPIC-TAMU / IPSL SSP1-2.6 | −1.010 to −0.938 | 11.648 to 11.679 | 10.637 to 10.742 |
| EPIC-TAMU / IPSL SSP5-8.5 | not admissible | not admissible | not admissible |

Negative precipitation damage denotes a welfare benefit. Calendar conventions
form the reported ranges. Across all registered elasticities and supply
mappings, precipitation attribution remains beneficial for both SSP1-2.6 cases:
CARAIB GFDL −0.441 to −0.195 billion, CARAIB IPSL −0.090 to −0.030,
EPIC GFDL −3.483 to −1.792 and EPIC IPSL −1.343 to −0.550. For the admissible
SSP5-8.5 cases it is a small loss: CARAIB GFDL 0.004--0.019 billion,
CARAIB IPSL 0.007--0.035 and EPIC GFDL 0.064--0.167.

These structural results imply that, in this specific period-mean quantity-only
benchmark, warming dominates joint maize losses while precipitation changes can
partly offset them under SSP1-2.6. They do **not** imply that real precipitation
damages are small: these crop emulators perturb seasonal quantity and do not
represent the within-season timing, dry spells, extremes or drought pathways
that motivate the main project.

## Integrity and validity boundary

The four-corner joint welfare totals reproduce the previously audited global-
market totals to numerical precision, and precipitation plus temperature closes
exactly to joint damage. EPIC IPSL/SSP5-8.5 remains mechanically inadmissible
because three country/regime/corner aggregates are nonpositive; it is not
clipped or omitted.

Nonpositive cell-level crop-model corners occur in otherwise aggregate-positive
cases and are retained. Across the central cases, the largest affected fixed
covered-value share is 0.01198% (50 EPIC cells in IPSL/SSP5-8.5 joint climate).
Their small global value share does not make negative yields physically valid,
so structural-damage interpretation remains disabled for every case.

This is a two-driver Shapley decomposition, not causal identification. It is
maize-only, covers the common supported/value-matched footprint, uses a global
market sensitivity, and compares 1981--2010 with 2031--2060. It lacks annual
matched baseline/pulse climate, distribution-aware crop response, calibrated
trend/upper adaptation and a validated total-agriculture replacement. It cannot
enter GIVE or be converted into an SCC.

## Reproduction

- Protocol: `FOUR_CORNER_WELFARE_ATTRIBUTION_PROTOCOL_20260919.md`.
- Builder: `scripts/build_four_corner_welfare_attribution.py`.
- Independent validator: `scripts/validate_four_corner_welfare_attribution.py`.
- Ignored result SHA-256:
  `86dc68b153b7d7ea1a4f5c1ca024cb7637f9fc83fe49454cee51015f31b7572b`.
- Validation output SHA-256:
  `da6f6bf4c26ca6dd9baa0c09fbd792ee93101e3000b8ac25adcda410d8e921c0`.
- Builder/validator sampled peaks were 143.59/144.77 MB and added less than
  0.24 MB combined under the existing resource limits.

All empirical-damage, agriculture-replacement, GIVE-export and SCC flags remain
false.
