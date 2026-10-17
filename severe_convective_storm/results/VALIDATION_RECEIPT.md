# Validation receipt

Date: 2026-10-17

- Local: Python 3 standard-library builder and five unit tests passed.
- Independent server: `darecompute-02`, Linux x86_64, Python 3.10.12.
- Server controls: `nice -n 10`; `ulimit -v 1048576` (1 GiB) applied to the validation shell.
- The local and server output hashes matched exactly:
  - `swiss_hail_benchmark.csv`: `97bc403c87f183e2030f2015ad9adc6a7be4ead1514cb623abb2ab0213a0b4e2`
  - `readiness.json`: `28123645988eb66081aded79c6926668761b2bb48466ec9413543ab62abb6bee`
- No raw event data were downloaded. The 19.9 GB event set is unnecessary for the source-pinned endpoint benchmark.
- The readiness status is intentionally `BLOCKED_FROM_SCC_BY_DESIGN`.
