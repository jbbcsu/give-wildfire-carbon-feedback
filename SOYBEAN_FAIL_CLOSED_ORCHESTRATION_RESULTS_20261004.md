# Soybean fail-closed orchestration result

## Scope and status

This gate closes the executable engineering path from the token-gated,
memory-bounded production reader through the dependency-injected adapter to
the real pooled response engine. It does not authorize or read real outcomes,
create a production token, disclose numeric fit results, run terminal
validation, or open any response, damage, SCC, or GIVE claim gate.

The production order is now fail-closed:

1. verify every pinned configuration and implementation hash;
2. validate the base production authorization and portability bindings;
3. validate the token's exact orchestrator and orchestrator-config hashes;
4. construct the authorized reader;
5. import the response engine dynamically;
6. execute exactly one declared moisture family through the adapter; and
7. emit only support/design structure plus explicit redaction and closed-gate
   metadata.

The CLI has no synthetic or test-mode switch. Its `run` command requires one
of `quantity`, `distribution`, or `scpdsi_season`, an explicit token path, and
a fresh output path. Direct quantity remains primary; distribution and
scPDSI are mutually exclusive challengers and are not stacked or substituted
automatically.

## Exact authorization packet

`data/provenance/soybean_pooled_response_authorization_packet_20261004.json`
freezes the required authorization statement and exact token-bound hashes for
the dry-run manifest, protocol, engine, portability manifest, reader, reader
configuration, orchestrator, and orchestrator configuration. It intentionally
records `authorization_granted=false`, `token_created=false`, no nonce value,
no engine import, no fit invocation, and no real source access. It is a
requirements packet, not an authorization artifact.

## Synthetic full-path result

Synthetic Parquet fixtures exercised the actual production reader, pair
construction adapter, and real pooled engine for all three families. Each
family had 2,100 levels (60 cells over 1982--2016), 2,040 consecutive pairs
over 34 pair-end years, and 30 independent 10-degree clusters. The quantity,
distribution, and scPDSI designs had respectively 7, 12, and 7 columns, all at
full rank. The test also established that a missing production token and a
synthetic token both stop before production reader construction and engine
import. Applying the frozen production sample selector to each synthetic
family retained 1,680 training pairs for 1983--2010, excluded 60 pairs in the
2011 buffer, and locked 300 pairs in 2012--2016 for separate terminal work.

The full synthetic test peaked at 179,486,720 bytes (171.17 MiB), below the
536,870,912-byte cap. The independent static/receipt validator peaked at
25,313,280 bytes (24.14 MiB). No real outcome file was opened and no production
token was created.

The macOS test runtime emitted NumPy matrix-multiplication warnings while the
frozen engine evaluated the synthetic distribution-family design. The engine's
existing full-rank, finite coefficient/residual/covariance, and positive finite
standard-error guards nevertheless passed. This warning is disclosed rather
than treated as evidence of numerical validation; production results remain
blocked, and the warning must be reassessed on the real authorized design.

## Output and terminal boundary

Public orchestration output contains no coefficients, standard errors,
p-values, confidence intervals, residuals, or predictions. It retains only
support counts, design dimensions/rank, execution audit, resource use, and
closed claim gates.

The fit summary explicitly records terminal validation as not run and not
passed. Production fitting remains limited to pair-end years 1983--2010;
2011 is the buffer and 2012--2016 is the locked terminal block. Terminal
transport must be a separately authorized, in-memory operation using the
unchanged training fit. A successful fit summary cannot promote a response.

## Bound artifacts

- `scripts/soybean_pooled_response_orchestrator.py`:
  `02ed93c9eb29d98ce2610dac848a05d81385b14f939f5ab7460bc5aa40b20d17`
- `config/soybean_pooled_response_orchestrator_v1.toml`:
  `a1d05ae18431d49130fe61615fbb77281904a4280f94627ba8d31afa459f6297`
- `scripts/test_soybean_pooled_response_orchestrator.py`:
  `f9183d0fcd0f87e9c8d11b7f2e85fe7941c95bb77c805bdd49e67eb336ceaf18`
- `scripts/validate_soybean_pooled_response_orchestrator.py`:
  `19bbf98da0ea257d34295b3a6b1989da91be7cc95169510f9f9a93ef1280ceab`
- authorization packet:
  `a33f3104a39742184c6b6b3dacdb86f5995b7470a8c764a5bc457e5705290c6f`
- synthetic test receipt:
  `0afb0ea267395775f3cdf978f118b56d6770a7f0b0ed6478ce93e8ae18dc2e11`
- independent validation receipt:
  `5b08b60c6ad7cc31d193032b362a2da91d51d77fa9d3c3de249f6adaa36bc26b`

## Gate conclusion

The reader-to-adapter-to-engine route is mechanically ready for a future
explicitly authorized, one-family production execution. Scientific promotion
remains closed: no real fit or terminal validation has run, and no
associational, predictive, causal, geographic winner/loser, damage, SCC, or
GIVE conclusion follows from this engineering result.
