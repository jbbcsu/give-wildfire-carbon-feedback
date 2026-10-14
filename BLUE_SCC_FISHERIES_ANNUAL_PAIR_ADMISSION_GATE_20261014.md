# Blue-SCC fisheries annual-pair admission gate

## Result

The requested Blue-SCC fisheries artifacts now have a versioned, executable,
fail-closed admission contract. A package can pass only if it supplies
license-cleared, checksum-pinned, matched annual baseline and pulse country
paths; a complete country mapping; explicit pulse and run-pair metadata;
direct consumer- and producer-surplus components; an explicit exclusion of
nutrition/mortality and other overlapping pathways; and global rows that
reconcile additively to country rows for both paths and their changes.

Passing this gate would admit source artifacts for a later scientific review.
It would not validate a damage function, apply discounting, calculate an SCC,
or authorize addition to GIVE.

## Package contract

The manifest must conform to
`config/blue_scc_fisheries_annual_pair_v1.schema.json` and refer to four
distinct CSV files located inside the same package directory:

1. `baseline_path`: one undiscounted annual level for every declared
   draw-country-year key;
2. `pulse_path`: the exactly matched pulse level for the same keys;
3. `country_mapping`: a one-to-one source-key, ISO3, and GIVE-country mapping
   with coefficient and annual-path support; and
4. `global_reconciliation`: baseline and pulse global levels by draw-year,
   split into consumer surplus, producer surplus, and their market total.

Every file is checked against its declared byte size and SHA-256. File paths
may not escape the package directory or resolve to symlinks. Exact headers are
required; extra or missing fields fail. Missing rows, duplicate keys,
non-finite values, unit drift, unmatched run identifiers, undeclared
countries/draws/years, and implicit zero filling all fail.

The welfare boundary admits only direct consumer plus producer surplus in
annual USD flows. Nutrition/mortality must be explicitly excluded and absent
from these market paths. Accounting profit cannot silently stand in for
producer surplus, and gross revenue, multiplier-expanded output,
aquaculture, coral/reef services, biodiversity nonuse value, and CIAM coastal
impacts must all be excluded. Any unresolved third-party license restriction
fails closed.

For bounded operation, one package may declare at most 100,000 rows per path.
Larger deliveries must be partitioned into separately complete,
checksum-pinned packages rather than bypassing the memory guard.

## Public-export negative control

The validator's `public-summary` mode was run on the two released files at
Blue-SCC commit `dbc0d8cb21c81f1508abfaf9e5c0f5671ccdd83f`. The 310 fisheries
rows in `Data/SCC/out/country_level_scc.csv` and two fisheries rows in
`Data/SCC/out/scc.csv` provide two comparable valuation summaries. Zero of
the two country sums equals its global summary. More fundamentally, these are
terminal SCC summaries: neither contains annual matched baseline/pulse paths,
pulse metadata, a complete source-to-GIVE country mapping, direct CS/PS
semantics, a machine-readable market versus nutrition/mortality boundary, or
an artifact license manifest.

The exact hashes, sizes, headers, row counts, and nonnumeric admission result
are recorded in
`data/provenance/blue_scc_public_fisheries_summary_admission_20261014.json`.
The receipt deliberately does not repeat the SCC values. It verifies only
that the public summaries are inadmissible under the annual-pair contract.

## Commands

Validate a future delivery:

```bash
python3 scripts/validate_blue_scc_fisheries_annual_pair.py package /path/to/package/manifest.json
```

Reproduce the pinned public-summary negative control from an independently
checked-out source tree:

```bash
python3 scripts/validate_blue_scc_fisheries_annual_pair.py public-summary \
  /path/to/blue-scc/Data/SCC/out/country_level_scc.csv \
  /path/to/blue-scc/Data/SCC/out/scc.csv \
  --source-commit dbc0d8cb21c81f1508abfaf9e5c0f5671ccdd83f
```

Focused synthetic tests:

```bash
python3 test/test_blue_scc_fisheries_annual_pair.py
```

The tests exercise one valid synthetic package and failures for unresolved
license, invalid pulse unit, incomplete mapping, unmatched path coverage,
nonadditive global totals, nutrition/mortality leakage, and a checksum
mismatch. A separate synthetic fixture verifies rejection of the released
public-summary shape. No real input value is fabricated by the tests.

## Remaining external blocker

No admissible real package exists locally. The exact outstanding delivery is
still the licensed source and environment chain, matched RICE50x annual
baseline/pulse outputs, complete mapping, direct CS+PS semantics, and
overlap-cleared additive reconciliation requested in
`BLUE_SCC_AUTHOR_ARTIFACT_REQUEST_20261013.md`. Until those artifacts pass this
gate and later scientific checks, the fisheries GIVE damage and SCC gates
remain closed.
