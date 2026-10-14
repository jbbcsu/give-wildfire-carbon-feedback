# Residual coral-reef services for GIVE

This isolated project screens coral-reef welfare channels for a component that
can be added to GIVE without duplicating fisheries, biodiversity nonuse, or
coastal impacts assigned to CIAM.

The present admissible target is narrower than “coral value”: consumer welfare
from opportunities for coral-reef recreation and tourism. Market provisioning
services, coastal protection, existence/nonuse value, and ambiguous cultural
services remain excluded.

The October 14, 2026 audit found a newly released primary candidate in the
Blue-SCC repositories, but its coral “non-market use” SCC bundles eight
services and cannot be reduced to recreation without an unsupported
allocation. The current gate therefore remains closed.

Run the machine-bound source audit against temporary checkouts:

```sh
python3 scripts/validate_coral_residual_audit.py \
  --contract config/coral_residual_candidate_audit_v1.json \
  --blue-root /path/to/blue-scc \
  --rice-root /path/to/RICE50xmodel-v2.6.0 \
  --out data/provenance/coral_residual_public_source_audit_20261014.json
```

This command checks source revisions, file hashes, license presence, published
output structure, and overlap boundaries. It does not calculate damages or an
SCC.
