# Blue-SCC market component transfer to GIVE

## Decision

The published Blue-SCC fisheries market component of
$0.0570404/tCO2 can be read exactly from the released Figure 4 workbook, but
it cannot be reproduced or transferred from the released country files. The
country SCC rows are not an additive decomposition of the published global
result, upstream coefficient and output country supports differ, and the
released repository does not contain the annual baseline/pulse results needed
for a GIVE damage path.

No missing country was filled, no partial region was renormalized, no
coefficient was transferred, and no damage or SCC was calculated.

## Country-output reconciliation

The 155 released 2020 country rows labelled `Fisheries` and `Market value`
sum to $0.0526646/tCO2. This is $0.0043758/tCO2, or 7.67%, below the separately
published Figure 4 value of $0.0570404/tCO2.

This difference is not a rounding discrepancy. The published SCC utility
changes its aggregation key from year alone for a global result to year and
country for a country result, then constructs aggregation-specific population
weights, consumption, and discount factors. The country export explicitly
calls that utility with `country_level=True` and selects 2020. Consequently,
the released country rows cannot be treated as additive shares of the global
Figure 4 component.

## Coverage and welfare semantics

The released temperature-coefficient table contains 143 country keys and
matches 142 of the frozen 184 GIVE countries. Six of 16 FUND regions are
complete: ANZ, CAN, JPK, MAF, SIS, and USA. The released country-SCC market
output contains 155 keys and matches 154 GIVE countries, with six complete
regions: ANZ, CAN, EEU, JPK, USA, and WEU. The two source supports intersect
on only 120 keys; 23 occur only in the coefficient table and 35 only in the
country SCC output. These are unweighted country-count diagnostics.

The market coefficient is a Free et al. projected profit/GDP temperature
slope after applying regional direct, indirect, and induced output
multipliers. It is not a released consumer-plus-producer-surplus measure.
Restricting attention to this market component avoids the Blue-SCC
nutrition/mortality pathway, but it does not resolve double counting between
the multiplier-expanded fisheries measure and other GIVE market damages.

## Executable and legal blockers

The source code documents a one-million-ton emissions pulse, but the pinned
repository contains only the socioeconomic input GDX. It omits both
baseline/pulse result GDX files and the RICE50x model tree used to produce the
annual result. The audited repository commit also has no explicit root
license. Aggregate facts and hashes are recorded locally; source tables,
country membership, and country values are not copied.

The minimum external artifact request is:

1. an explicit code and data reuse license;
2. a same-run additive country decomposition that sums to the Figure 4 market
   component;
3. annual country baseline and pulse fisheries-market damage flows;
4. the exact RICE50x commit, dependency lock, and baseline/pulse result GDX;
5. the exact mapping and missingness semantics connecting the 143 coefficient
   keys to the 155 output keys;
6. country multiplier assignments and the upstream profit panel, plus either
   multiplier-free direct surplus or valid consumer-plus-producer surplus;
7. an accounting boundary resolving overlap with GIVE market damages.

## Reproduction

The fail-closed config and aggregate-only receipt are:

- `config/blue_scc_market_component_transfer_v1.toml`
- `data/provenance/blue_scc_market_component_transfer_audit_20261013.json`

Run against a separate checkout of the Blue-SCC repository at commit
`dbc0d8cb21c81f1508abfaf9e5c0f5671ccdd83f`:

```bash
python3 scripts/audit_blue_scc_market_component_transfer.py \
  --source-root /path/to/blue-scc
python3 test/test_blue_scc_market_component_transfer.py
```
