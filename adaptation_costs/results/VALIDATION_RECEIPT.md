# Validation receipt

Date: 2026-10-17

- Local: standard-library ledger builder and five unit tests passed.
- Independent server: `darecompute-02`, Linux x86_64, Python 3.10.12.
- Server controls: `nice -n 10`; virtual memory capped at 1 GiB with `ulimit -v 1048576`.
- Local and server output hashes matched:
  - `readiness.json`: `7a66d9a6758ca38a55b00548773d5c7d247e4f07c2a89f4f48c3053f48dd6ba2`
  - `bounded_agriculture_cost_benchmark.csv`: `e3cf82e1102c9ae701080898cc899e21edd8b3898f2b1d2c31443e1eed90a061`
- Raw PDFs are not committed.
- Agriculture net-adaptation SCC status remains intentionally blocked.
