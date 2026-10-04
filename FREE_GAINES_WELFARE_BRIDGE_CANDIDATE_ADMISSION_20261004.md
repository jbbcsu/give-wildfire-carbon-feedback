# Free/Gaines welfare-bridge candidate admission

Date: 2026-10-04

Contract: `global_fisheries_welfare_bridge_input_v1`

Candidate: `candidate:free-gaines-dfd250d-partial`

## Result

The fail-closed candidate audit admits one item of real, immutable evidence:
`code/Step1_format_gaines_data.R` at `SFG-UCSB/cc_trade` commit
`dfd250ddd806973f463e83097a3ed39dd27f8bfb`, with SHA-256
`fc2683b45be1d306e56ed1e01dd0527d850c3f8f222e66dbf653a7d006c95477`.
The version and digest are copied from, and tested against, the independently
produced source audit in
`data/provenance/alternative_global_fisheries_welfare_audit_20260928.json`.

This file is downstream formatting code, not the complete executable model.
Its candidate component is therefore explicitly `provided: false`. The audit
finds 0 of 7 components ready for scientific review and keeps scientific
validation, coefficient transfer, fitting, damages, aggregation, discounting,
and SCC authorization false.

The candidate inventory is
`data/provenance/free_gaines_welfare_bridge_candidate_inventory_20261004.json`.
It contains no response, incidence, or welfare rows and invents no missing
license, dependency, coverage, pulse, welfare, or overlap value.

## External blockers

The Free/Gaines custodians would need to supply the following before a future
production scientific review could begin:

1. An explicit redistribution and derivative-use license for the exact code
   and data release.
2. The missing raw RDS inputs identified in the pinned audit, including
   `eez_delta_k_df.rds` and
   `global_cc_1nation_manuscript_2019Feb12.rds`, plus the corresponding
   realistic-adaptation input.
3. The executable model core and exact dependency lock; the admitted Step 1
   script alone is insufficient.
4. Stock-to-producer, landing, trade, and consumer-market incidence keys with
   explicit missing, joint-area, high-seas, and out-of-scope semantics.
5. Direct consumer-surplus evidence and a validated statement of whether the
   modeled profit is producer surplus/resource rent on identical support.
6. Same-realization baseline and one-ton-CO2-pulse paths. RCP and management
   contrasts do not substitute for a marginal pulse.
7. A passed accounting-boundary review separating capture-fisheries direct
   market surplus from aquaculture, terrestrial food, nutrition/mortality,
   coral services, biodiversity, coastal impacts, and indirect output.

Published coverage also remains explicitly incomplete: 779 stocks, 156
coastal sovereign countries, and 58.2% of reported 2012 catch. Missing
coverage must not be imputed or renormalized.

No outreach was performed, no external data were downloaded, and no welfare
or SCC estimate was calculated.

## Authoritative repository metadata refresh

On 2026-10-04, the GitHub API was queried for the repository, current default
branch head, exact pinned commit and recursive tree, releases, and tags. The
machine-readable receipt is
`data/provenance/free_gaines_github_metadata_20261004.json`; the reproducible
query is `scripts/audit_free_gaines_github_metadata.py`.

The default branch still resolves to the pinned commit. GitHub reports no
detected repository license, releases, or tags. Its untruncated 244-entry tree
contains no recognized license filename, no recognized dependency-lock
filename, and neither named raw RDS input. The admitted formatting script is
present as a 12,521-byte Git blob. These facts leave all seven contract
components blocked.

This is a repository-scoped negative result. It does not prove that no
off-repository license, release, dependency record, or source artifact exists;
it establishes that the authoritative repository endpoints do not supply the
required evidence.
