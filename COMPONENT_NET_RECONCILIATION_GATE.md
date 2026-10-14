# EPA globalAQ component/net reconciliation gate

Status date: 14 October 2026.

The official `USEPA/globalAQ_rft` remote remains unchanged from the submission
snapshot: `HEAD` and `main` both resolve to commit
`1139e7aff1ca7806b6b542268e829f9759dd8808`, and the official API reports no
tags or releases. The available source therefore still predates the final
article revision and cannot identify an article-generating release.

The new validator distinguishes three released objects at the 2% Ramsey rate:

- Ozone component rows in `npd_global_rff_means.csv`.
- PM rows in that component file. The final article says that open-burning
  emissions, including wildfires, are excluded, but the repository itself
  contains no machine-readable open-burning/wildfire boundary. The validator
  consequently labels this a PM2.5 non-wildfire **candidate**, not a verified
  transferable non-wildfire component.
- A separate net file, `npd_global_rff_net_means.csv`. Source code forms the
  component and net tables from distinct aggregation objects. The ignored and
  absent trial streams prevent a same-run identity check.

## Exact released reconciliation

| Output | CESM2 | GISS | Model mean |
|---|---:|---:|---:|
| Ozone component | 24.231616 | 9.111682 | 16.671649 |
| PM2.5 candidate | -46.454720 | -2.603377 | -24.529049 |
| Component sum | -22.223104 | 6.508305 | -7.857400 |
| Separate net | -57.147772 | -12.187464 | -34.667618 |
| Net minus component sum | -34.924667 | -18.695769 | -26.810218 |

These are reconciliations of released summaries, not calibrated estimates.
They do not reproduce the article's +23, -38, and -15 USD/tCO2 means.

## Metadata blockers

The source input builder converts 2011-dollar GDP to 2024 dollars and records
`dollar.year = 2024`; the reduced-form tool uses a 2024-dollar VSL. In contrast,
the reduced-form and NPV file headers describe 2020-dollar outputs. No explicit
2024-to-2020 conversion is present in the released code. The price year is
therefore unresolved.

The final article explicitly states that emissions from open burning, including
wildfires, are not included. That is authoritative scientific-scope evidence,
but it is not represented by any machine-readable flag, emissions inventory,
species manifest, or boundary record in the repository. The code-transfer gate
remains closed pending that artifact.

Run the bounded gate with:

```bash
python3 test/test_component_net_boundary.py
python3 scripts/validate_component_net_boundary.py
```

No article-value calibration, replacement SCC, or GIVE transfer is authorized.
The minimum remaining author delivery is a versioned final code/environment,
same-run identified ozone/PM/net streams, an explicit final price year, and a
machine-readable emissions/species boundary confirming open-burning exclusion.
