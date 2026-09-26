# MIRCA rice-season proportional-reconciliation sensitivity protocol

**Frozen before running the sensitivity: 2026-09-26.**

## Question

Can the official MIRCA-OS v2 Rice1--Rice3 monthly layers be reconciled to the
official annual broad-rice layer by a transparent within-cell scaling that
preserves the source season shares, without hiding unsupported cells or
materially changing global/seasonal exposure?

## Inputs and transformation

- Use only the six metadata-valid year-2000 monthly Rice1--Rice3 irrigated and
  rainfed files and the corresponding official annual 30-arcminute Rice files.
- Reproduce the publisher-code logic already audited: take each season's
  maximum monthly 5-arcminute area and sum aligned 6-by-6 blocks.
- Within each 30-arcminute cell and irrigation system, multiply all three
  seasonal areas by `annual broad-rice area / sum(seasonal areas)`.
- The transformation is invalid wherever annual area is positive but the
  seasonal sum is zero. Such cells are reported and never filled.
- Rice3 remains disclosed and is never reassigned to Rice1 or Rice2.

## Diagnostics and gates

Report source hashes; global and cell discrepancies; unmatched support;
scaling-factor quantiles; annual-area shares receiving absolute relative
corrections above 0.1%, 1%, 5%, and 10%; season-specific global area changes;
and exact post-repair reconciliation. A candidate weight table may be written
only if no positive annual area lacks seasonal support and repaired totals
match annual totals within numerical tolerance.

This is an explicitly labeled sensitivity, not publisher data, author
replication, or a primary production input. It cannot authorize a response,
damage estimate, or SCC. Promotion would additionally require a Rice1/Rice2
calendar/spatial crosswalk, response-domain validation, and manuscript
sensitivity showing that conclusions do not depend on the repair.
