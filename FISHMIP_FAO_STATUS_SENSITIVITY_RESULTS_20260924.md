# FishMIP–FAO observation-status sensitivity

## Result

The existing global historical comparison was recomputed with two literal FAO
status sets: all source codes classified by the frozen contract as observed or
quality-coded (`A`, `E`, `I`, and `X` in the marine slice), and `A` alone. Each
series is normalized by its own 2005--2014 mean.

| FishMIP path | 1980--2014 level correlation, quality set | `A` only | First-difference correlation, quality set | `A` only |
|---|---:|---:|---:|---:|
| GFDL-ESM4 / BOATS | 0.903 | 0.521 | 0.294 | 0.197 |
| GFDL-ESM4 / EcoOcean | 0.778 | 0.278 | 0.338 | 0.198 |
| IPSL-CM6A-LR / BOATS | 0.769 | 0.290 | 0.308 | 0.082 |
| IPSL-CM6A-LR / EcoOcean | 0.726 | 0.241 | 0.217 | 0.042 |

The 2005--2014 reference is 80.694 million tonnes for the contract quality set
and 74.804 million tonnes for `A` alone. The post-1980 apparent level fit is
therefore highly sensitive to observation-status composition; weak annual-
change fit becomes still weaker under `A` only.

## Interpretation boundary

`A` only is a transparent robustness subset, not a claim that `E`, `I`, or `X`
are invalid observations. This post-existing-evidence comparison cannot be used
to select a FishMIP model or a preferred status family. Instead, it shows that
future calibration must pre-register status inclusion and report sensitivity.

A separate implementation reconstructed 64 metrics directly from the full
30,918-record reconciled export with maximum discrepancy `4.44e-16`. No climate
effect, effort/management response, welfare, marginal CO2 pulse, damage, or SCC
is identified here.
