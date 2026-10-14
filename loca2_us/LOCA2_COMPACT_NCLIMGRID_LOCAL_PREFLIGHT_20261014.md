# Compact-strata nClimGrid local-input preflight

## Outcome

The requested outcome-free 2001--2012 seasonal feature build cannot run from
resident files. The exact gridded nClimGrid-Daily inputs were deliberately
evicted on 2026-09-21, and none of the required objects is locally present.
No download was started, no raw file was created or modified, and no yield or
LOCA2 value was read.

The frozen Solano, Grady, and Shelby calendars require the union of April
through October for every year from 2001 through 2012: exactly **84 monthly
NetCDF objects**, **4,909,747,416 bytes (4.573 GiB)**. The availability receipt
binds every object to its canonical NOAA URL, HTTP identity, reviewed local
SHA-512, and a canonical 84-object manifest hash. Local status is 0 valid, 84
missing, 0 partial, and 0 invalid.

## Why retained county averages are not substituted

Resident NOAA county-average CSVs cannot satisfy this gate. They bypass the
three selected hash-bound grid-cell weight tables and apply spatial aggregation
before nonlinear dry-spell and extreme-rainfall construction. The registered
basis constructs CDD, Rx1day, and Rx5day at weather cells before weighting.
Substitution would therefore change the estimand and is explicitly prohibited.

The existing national all-practice builder is also not authorized for this
task: it reads and emits outcome magnitudes. After the active 11-cell SPEI
transfer completes, the next gate is to reacquire only these 84 exact objects,
validate all SHA-512 identities, and run a dedicated outcome-free adapter one
harvest year at a time under 512 MiB.

## Validation and claims

The preflight verifies the frozen preregistration/config hashes, all three
selected weight receipt/output hashes, the complete 468-object reviewed source
inventory and content receipt, and the raw-eviction receipt. Its tests derive
the 84-month union from the county calendars rather than a hard-coded list and
exercise missing, partial, invalid-size, invalid-hash, and valid local states.

Only the local-input-availability audit gate is open. Observed climate
features, historical climate sentinels, representative validation, model
skill, outcome response, causal damage, and SCC gates remain closed.

The executed availability receipt is
`loca2_us/data/provenance/loca2_compact_strata_nclimgrid_local_availability_20261014.json`;
its canonical manifest SHA-256 is
`78a070ea622bb22e1f0aa65d0c681abfc2fdc97a0088c59fba81152634490bce`.
The preflight's in-process peak RSS was 24,723,456 bytes (23.58 MiB). The full
LOCA2 test suite passed 42 tests, including a direct, independent
inventory/content-receipt intersection check. The bounded runner sampled a
peak process-group RSS of 215,384,064 bytes (205.41 MiB), below the 512 MiB
cap. These measurements are process-sampled rather than a kernel-enforced
memory limit.
