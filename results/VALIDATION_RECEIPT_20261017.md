# Validation receipt

- Local run: source hash verification, 340-row annual matched-pulse calculation, independent SCC reconciliation, and four unit tests passed.
- Server run: `darecompute-02`, executed with `nice -n 10` and `ulimit -v 1048576` (1 GiB); all checks and four tests passed.
- Python peak resident memory reported by the server calculation: 17 MiB.
- Cross-platform numerical agreement: local and server mean partial SCC values differ by about `1e-12` USD/tCO2 because the serialized R interpolation is evaluated by different platform builds.
- Release gates: CONUS benchmark allowed; global extrapolation and additive GIVE SCC remain disabled.
