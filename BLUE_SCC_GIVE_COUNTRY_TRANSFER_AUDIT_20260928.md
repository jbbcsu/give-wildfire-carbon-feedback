# Blue-SCC market-coefficient transfer to GIVE: country coverage gate

## Decision

The published Blue-SCC country market coefficients are **not ready for direct
transfer** into the frozen GIVE aggregation universe. At the pinned external
commit, 142 of 184 GIVE countries have a matching coefficient key (77.17% by
unweighted country count). Forty-two GIVE countries are uncovered, and one of
the 143 source country keys is outside the frozen GIVE mapping.

Only 6 of 16 FUND regions have complete country-key coverage. The other 10
regions would fail the existing regional aggregation contract, which withholds
totals whenever a declared country is absent or incomplete. Missing countries
cannot be interpreted as zero damage, and the country-count coverage fraction
is not a population-, catch-, GDP-, or welfare-weighted coverage measure.

## Reproducible boundary

`scripts/audit_blue_scc_give_country_transfer.py` reads the external coefficient
table in place at commit `dbc0d8cb21c81f1508abfaf9e5c0f5671ccdd83f`, checks
its frozen SHA-256, validates unique ISO3-shaped keys, and compares them with
the hash-bound 184-country GIVE crosswalk. The tracked receipt contains only
aggregate totals and per-region counts. It includes no coefficient values and
no country-level source membership.

The external repository still has no explicit root license file at the pinned
commit. This audit therefore does not copy its table, authorize redistribution,
or cure the separate welfare mismatch: the published market pathway is based
on profit projections plus output multipliers, not consumer plus producer
surplus.

## Result by FUND region

| Region | GIVE countries | Covered | Uncovered | Complete |
|---|---:|---:|---:|:---:|
| ANZ | 2 | 2 | 0 | yes |
| CAM | 9 | 8 | 1 | no |
| CAN | 1 | 1 | 0 | yes |
| CHI | 4 | 1 | 3 | no |
| EEU | 13 | 7 | 6 | no |
| FSU | 15 | 9 | 6 | no |
| JPK | 2 | 2 | 0 | yes |
| LAM | 12 | 10 | 2 | no |
| MAF | 5 | 5 | 0 | yes |
| MDE | 15 | 13 | 2 | no |
| SAS | 7 | 4 | 3 | no |
| SEA | 13 | 12 | 1 | no |
| SIS | 21 | 21 | 0 | yes |
| SSA | 44 | 29 | 15 | no |
| USA | 1 | 1 | 0 | yes |
| WEU | 20 | 17 | 3 | no |

## Remaining blocker

A defensible transfer requires all three of the following before any GIVE
damage calculation: explicit source reuse permission or a licensed release; a
predeclared treatment for every uncovered GIVE country that does not equate
missing with zero; and a welfare-compatible replacement for, or explicit
labeling and overlap treatment of, the published profit-plus-multiplier
measure. The matched marginal-CO2 pulse gate also remains closed.

Reproduce from a separate checkout of the pinned commit:

```bash
python3 scripts/audit_blue_scc_give_country_transfer.py \
  --source-root /path/to/blue-scc
python3 test/test_blue_scc_give_country_transfer.py
```
