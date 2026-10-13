# Blue-SCC nutrition pathway transfer to GIVE

## Decision

The published Blue-SCC nutrition pathway is the shortest existing route to a
fisheries marginal SCC benchmark, but it is not ready to generate defensible
GIVE regional annual damages or a GIVE fisheries SCC. The released files do
not pass country coverage, missingness, output reconciliation, executable
annual-path, license, or mortality-overlap gates.

No coefficient was copied, no missing country or field was set to zero, no
region was renormalized, and no damage or SCC was calculated.

## Exact coverage result

The pinned nutrition input contains 128 unique country rows, of which 127
match the frozen 184-country GIVE universe. Eleven rows have
`Nutritional_D = NA`. Requiring all five published nutrition and mortality
fields to be numeric leaves 117 source countries and 116 GIVE matches
(63.04% by unweighted country count). Only 4 of 16 FUND regions then have
complete country-key coverage: ANZ, CAN, JPK, and USA.

The broader released 2020 country-SCC output has 155 country keys and covers
154 GIVE countries, but only 6 of 16 FUND regions completely. That broader
support cannot cure the upstream nutrition gaps: the published input builder
outer-joins market and nutrition records and applies `fillna(0)`. The local
contract forbids treating unavailable country coefficients or an unavailable
`Nutritional_D` value as an observed zero.

These fractions are unweighted country counts, not population-, mortality-,
seafood-dependence-, catch-, GDP-, or welfare-weighted coverage measures.

## Published-output reconciliation

The 155 released fisheries rows for each valuation are explicitly selected at
year 2020 by the published export code. Their country sums do not reproduce
the separately released Figure 4 source values:

| Valuation | Country-file sum | Figure 4 | Relative difference |
|---|---:|---:|---:|
| Market value | 0.0526646 | 0.0570404 | -7.67% |
| Non-market use value | 23.1322251 | 22.0405095 | +4.95% |

Values are published 2020 USD per tCO2. The combined country-file fisheries
sum is 23.1848898, 4.92% above the Figure 4 fisheries total of 22.0975499.
The audit does not choose between the releases or reinterpret the difference.

## Annual-damage and overlap blockers

The source code documents a one-million-ton emissions pulse and baseline/pulse
SCC calculation, but the pinned repository contains only the socioeconomic
input GDX. It does not contain the baseline and pulse result GDX files or the
RICE50x model used to generate annual damage paths; the run instructions point
to a separate RICE50x checkout. The released country file is a 2020 SCC
snapshot, not an annual regional damage series.

Even an exact rerun would not resolve GIVE additivity. The published nutrition
path monetizes mortality through seafood nutrient availability and VSL, while
core GIVE already values temperature-related mortality without a fisheries
cause/pathway exclusion. The cause, population, baseline mortality, VSL, and
substitution boundaries must be reconciled before adding this pathway.

The external repository also remains without an explicit root license at the
pinned commit. Aggregate audit facts are retained locally; source tables and
country membership are not copied.

## Reproduction

The config and aggregate-only receipt are:

- `config/blue_scc_nutrition_give_transfer_v1.toml`
- `data/provenance/blue_scc_nutrition_give_transfer_audit_20261013.json`

Run against a separate checkout at commit
`dbc0d8cb21c81f1508abfaf9e5c0f5671ccdd83f`:

```bash
python3 scripts/audit_blue_scc_nutrition_give_transfer.py \
  --source-root /path/to/blue-scc
python3 test/test_blue_scc_nutrition_give_transfer.py
```

The exact external request is a licensed, versioned RICE50x release with the
baseline and one-million-ton-pulse run inputs and GDX outputs, an explanation
of the country-file/Figure-4 discrepancy, complete non-zero-imputed nutrition
inputs or explicit missingness semantics, and a mortality-overlap accounting
crosswalk suitable for GIVE.
