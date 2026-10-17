# Tropical-cyclone damages for GIVE

This isolated project audits Krichene et al. (2023), *The social costs of
tropical cyclones*, as a candidate omitted damage sector for GIVE.

The published global benchmark and 41-country GMT-growth coefficient table are
machine-verified. The benchmark remains non-additive because persistent GDP
growth losses can include multiple sectoral channels already represented or
planned elsewhere in GIVE.

Run the bounded source audit against the official Zenodo code extraction and
Springer Nature source-data extraction:

```sh
python3 scripts/audit_tropical_cyclone_give_readiness.py \
  --contract config/tropical_cyclone_give_readiness_v1.json \
  --code-root /path/to/tc_cost \
  --source-data-root /path/to/source_data \
  --out data/provenance/tropical_cyclone_give_readiness_20261017.json
```

See `TROPICAL_CYCLONE_GIVE_READINESS_20261017.md` for the result, overlap
boundary, and shortest route to a GIVE-compatible sensitivity calculation.

Raw releases are intentionally excluded from git. The contract records their
official URLs, versions, licenses, sizes, and checksums.
