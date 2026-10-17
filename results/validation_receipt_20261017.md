# Validation receipt

- Date: 2026-10-17
- Local: source verifier, readiness audit, and five unit tests passed.
- Server: `darecompute-02`, Linux 5.15.0-190-generic x86_64, Python 3.10.12.
- Server controls: `nice -n 10`; virtual-memory cap set with `ulimit -v 1048576` (1 GiB) for the complete validation command.
- Server result: all eight pinned files verified; readiness audit passed; five tests passed.
- Scientific release state: additive SCC remains disabled, as intended.

No large epidemiological archive was downloaded and no full bootstrap projection was attempted. This validation concerns provenance, executable contracts, and claim gates—not numerical replication of the paper.
