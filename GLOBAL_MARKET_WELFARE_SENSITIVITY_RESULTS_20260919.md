# Global-market sensitivity: market geography is consequential

## Finding

The prespecified single-global-maize-market sensitivity is complete and
independently validated. It uses exactly the same structural crop responses,
covered values, price conversion, fixed management, elasticity pairs and
yield-to-supply mappings as the separate-country-market calculation. It changes
only the order of aggregation: all valued supply shifts are combined before one
global market is solved.

For CARAIB, the central 0.10/0.04 horizontal-output results remain close to the
country-market values:

| Climate case | Global market, billion USD2005 | Country markets, billion USD2005 | Global/country |
|---|---:|---:|---:|
| GFDL-ESM4 / SSP1-2.6 | 9.049--9.069 | 9.327--9.347 | 0.970 |
| GFDL-ESM4 / SSP5-8.5 | 14.211--14.241 | 14.594--14.631 | 0.973--0.974 |
| IPSL-CM6A-LR / SSP1-2.6 | 13.738--13.757 | 13.982--14.002 | 0.983 |
| IPSL-CM6A-LR / SSP5-8.5 | 23.703--23.728 | 24.247--24.268 | 0.978 |

Ranges across the two rows reflect the two calendar conventions, not sampling
uncertainty. Across all registered elasticity and supply-mapping assumptions,
the CARAIB global-market ranges are 5.473--11.539, 7.901--19.377,
7.693--18.609 and 11.616--35.816 billion USD2005 for those four climate cases.

## The EPIC tail is largely a market-segmentation result

For EPIC-TAMU, aggregating before equilibrium materially changes the result.
The central global-market estimates are 4.728--4.779 billion for GFDL/SSP1-2.6,
12.469--12.497 billion for GFDL/SSP5-8.5, and 10.637--10.742 billion for
IPSL/SSP1-2.6. The corresponding country-market values are 7.120--7.196,
16.208--16.258 and 105.963--106.142 billion. Thus global integration reduces
the extreme IPSL/SSP1-2.6 result by about 90%, because Algeria's severe local
shock is pooled with global supply before the inelastic market response.

This comparison does **not** prove that a global market is correct. It shows
that market geography is a first-order structural assumption for severe,
spatially concentrated crop shocks. CARAIB's results are comparatively stable
across the two geographies, while EPIC's are not. The difference is useful
model-diagnostic evidence and cannot be counted as statistical uncertainty.

EPIC IPSL/SSP5-8.5 remains unvalued under the global sensitivity because one
valued regime multiplier is nonpositive. All 12 elasticity/mapping/calendar
variants fail the frozen admissibility rule; none is clipped or silently
removed. Overall, 84 of 96 global cases are mechanically admissible.

## Boundary

These remain structural, maize-only, mid-century scenario sensitivities—not
empirical climate damages, annual damage paths, agriculture replacements or SCC
estimates. Missing-value production is retained without rescaling. Trend and
upper adaptation, trade costs, storage, cross-crop substitution and matched
emissions-pulse paths remain absent. No market geography is selected by its
damage magnitude.

The next economic step, if pursued, should be a source-justified intermediate
trade geography rather than an invented continent mapping. The higher-value
scientific bottleneck remains qualification of the physical response and its
annual paired climate path.

## Reproduction

- Protocol: `GLOBAL_MARKET_WELFARE_SENSITIVITY_PROTOCOL_20260919.md`.
- Builder: `scripts/build_global_market_welfare_sensitivity.py`.
- Independent validator: `scripts/validate_global_market_welfare_sensitivity.py`.
- Ignored result SHA-256:
  `046df0554c6d4cc699c3b10c5fedc3e565601db60c217da362a359cbfcddd6b6`.
- Independent audit passed 1,160 checks; audit SHA-256:
  `4bab4dab0f552fb3e6662240cfac84173db919bd9579b7c319ba36281e1c2ac7`.
- Builder and validator sampled peaks were 1.84 and 1.51 MB and added less
  than 0.13 MB combined under the existing limits.

All empirical-damage, agriculture-replacement, GIVE-export and SCC flags remain
false.
