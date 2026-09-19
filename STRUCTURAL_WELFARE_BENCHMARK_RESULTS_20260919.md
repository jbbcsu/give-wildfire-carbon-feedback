# Structural maize-welfare benchmark: results and rejection boundary

## Result

The first fully audited monetary translation of the resident structural crop
benchmarks is complete. It is a **research sensitivity, not an empirical damage
estimate or SCC result**. The calculation values the joint temperature-plus-
precipitation maize response over the common supported footprint for the
1981--2010 to 2031--2060 contrast. It does not value precipitation alone.

Under separate country markets, the central 0.10/0.04 supply/demand elasticity
pair, horizontal-output mapping and fixed management, the CARAIB cases imply
the following signed welfare losses in billion USD2005:

| Climate case | Author calendar | Harvest-year calendar |
|---|---:|---:|
| GFDL-ESM4 / SSP1-2.6 | 9.347 | 9.327 |
| GFDL-ESM4 / SSP5-8.5 | 14.631 | 14.594 |
| IPSL-CM6A-LR / SSP1-2.6 | 13.982 | 14.002 |
| IPSL-CM6A-LR / SSP5-8.5 | 24.268 | 24.247 |

Across the three registered elasticity pairs and two yield-to-supply mappings,
the CARAIB ranges are 5.522--12.124, 7.962--20.275, 7.734--19.159 and
11.689--37.233 billion USD2005 for those four climate cases, respectively.
These ranges are economic-assumption sensitivity, not statistical uncertainty.

The covered baseline used in every admissible subtotal is 109.047 billion
USD2005 across 107 countries. Another 28 countries with 11.381 million tonnes
of common-support production lack a complete baseline-value proxy; they remain
unvalued and the subtotal is not rescaled. The source common-support proxy is
130.471 billion constant-2014--2016 USD before the registered price conversion.

## The EPIC result exposes a decisive economic-model fragility

EPIC-TAMU's central horizontal-output cases range from 7.120 to 106.142 billion
USD2005 on the valid subset. In the IPSL/SSP1-2.6 author-calendar case, Algeria's
country market retains only 0.10675 of baseline supply and contributes 93.494
billion of the 105.963-billion subtotal despite having only 0.153 million of
covered baseline value. It accounts for 88.18% of summed absolute country
changes. Under the full elasticity/mapping grid, the most extreme valid-subset
subtotal reaches 278,472.938 billion USD2005; this is an explosive consequence
of combining a severe local structural crop-model response with highly
inelastic, closed national markets, **not a credible estimate of damages**.

EPIC IPSL/SSP5-8.5 also contains one nonpositive country/regime productivity
multiplier under each calendar. Those 12 elasticity/mapping cases fail even the
mechanical log-admissibility rule. The affected response is retained and is not
clipped, dropped, or imputed. Valid-subset arithmetic is saved only as a
diagnostic.

The first execution is retained. A transparent v2 reporting amendment adds
minimum supply multipliers and country concentration without changing the
market arithmetic or introducing a post-result cutoff. The finding is useful:
country-level closed markets cannot be treated as a harmless default when
structural crop outputs include severe local tails. A prespecified continent
and global-market comparison is the next economic robustness test; it must not
be selected merely because it produces smaller damages.

## Scientific boundary

These numbers cannot enter GIVE. They cover maize only; use period-mean CMIP6
scenario contrasts rather than annual matched baseline/pulse paths; depend on
unvalidated structural crop-model responses; omit calibrated trend and upper
adaptation costs; and do not resolve trade, storage, cross-crop substitution,
or expectation formation. The separately completed empirical response screen
still authorizes no global yield family for damages.

The result nevertheless closes an implementation question: the published
physical benchmark, baseline-value ledger, price conversion, irrigation
aggregation and signed consumer-plus-producer surplus equations can be joined
without double scaling or loss truncation. The failure is substantive model
qualification, not missing software plumbing.

## Reproduction and validation

- Frozen protocol and amendment:
  `STRUCTURAL_WELFARE_BENCHMARK_PROTOCOL_20260919.md`.
- Builder: `scripts/build_structural_welfare_benchmark.py`.
- Independent validator: `scripts/validate_structural_welfare_benchmark.py`.
- Ignored v2 result SHA-256:
  `70996417ffe899817af0e6ac55515f7521de7457663d4074acecd37c5f2aadaa`.
- Independent audit passed 1,449 source, join, arithmetic, sign, mapping,
  concentration and gate checks. Audit SHA-256:
  `7afd9ad9c432e18c8b1e9bb39b9ea23777c2982d9f8cf78734a9330e0888e57f`.
- Builder and validator sampled peaks were 40.75 MB and 1.67 MB. They added
  0.73 MB and 0.001 MB under the 64 MiB cap; free disk remained at the 130 GiB
  floor. All raw/interim numerical outputs remain ignored.

No empirical-damage, agriculture-replacement, GIVE-export or SCC gate is open.
