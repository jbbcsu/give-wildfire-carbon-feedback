# Soybean pooled-response engine: synthetic validation

Date: 2026-09-28

## Result

The pooled-only estimator/inference engine specified by `soybean_pooled_response_inference_protocol_v1` is implemented and validated on generated data only. The engine contains no filesystem data reader and no real GDHY outcome was opened or fitted.

Implemented mechanics:

- strict consecutive-pair input contract with integer years, strict-boolean observed flags, positive current/prior yield endpoints, and internally derived `Δlog(yield)`;
- latitude in `[-90, 90]`, longitude in `[0, 360)`, exact coordinate-to-10-degree-block validation, and singleton-country requirement;
- production training pair-end years exactly 1983–2010 and terminal pair-end years exactly 2012–2016, with 2011 excluded as the frozen buffer; alternate synthetic years require literal Boolean `test_mode=True`;
- country × year, global-year, and block × year residualization;
- pooled OLS only, with country/block/cell/irrigation slope requests rejected;
- low-rank CR2 block adjustment and Satterthwaite degrees of freedom;
- restricted-null, studentized Webb six-point wild-cluster bootstrap-t, re-absorbing country-year controls on every draw;
- leave-one-block influence, block score/residual shares, and control sensitivities;
- terminal within-country-year anomaly transport scoring and paired block-bootstrap RMSE differences;
- fail-closed positive-draw and finite-positive score-share, residual-share, and terminal-bootstrap denominator checks;
- strict direct/scPDSI nonstacking;
- 9,999 production bootstrap draws from the frozen config, with reduced draws accepted only under an explicit synthetic-test flag.

## Independent checks

The deterministic test uses 720 synthetic training pairs, 300 terminal pairs, 12 spatial blocks, and six countries. A separate brute-force implementation constructs every cluster hat block and inverse-square-root CR2 adjustment, the full residual-maker representation for Satterthwaite degrees of freedom, identical Webb draws, and an independent block-bootstrap terminal score.

All checks pass:

- OLS coefficients agree within `1e-11`.
- CR2 covariance agrees within `1e-10`.
- Satterthwaite degrees of freedom agree within `1e-8`.
- Webb bootstrap p-value and t quantiles agree within `1e-10` using 199 fixed test draws.
- Terminal point and bootstrap interval agree within `1e-12` using 199 fixed test draws.
- Leave-one-block and all three control estimates match independent refits.
- Invalid coordinate endpoints, non-Boolean observed flags, non-integer years, positive-yield, consecutive-year, spatial-block, duplicate-key, family-stacking, geographic-slope, zero-draw, and reduced-production-draw requests fail closed.
- Incomplete/alternate production training years, missing 2012 terminal support, 2011 buffer leakage, and post-2016 terminal support fail closed. Synthetic alternate years work only with explicit Boolean `test_mode=True`.
- Synthetic recovery only: known coefficient `-0.14`, recovered `-0.1397429816`, absolute error `0.0002570184`.

Peak RSS was 164,528,128 bytes for the full synthetic/reference test and 27,410,432 bytes for the source-bound validator, both below 512 MiB.

## Boundaries

The engine is ready for code review, not real fitting. Real coefficients, production responses, causal interpretation, geographic heterogeneity, winner/loser claims, damages, SCC, and GIVE integration remain unauthorized.

## Artifacts

- Engine: `scripts/soybean_pooled_response_engine.py` (`a437fab438e17fccdc6bf9780de6799e5d11306174f18c55e2bd286f494f0b66`)
- Deterministic tests: `scripts/test_soybean_pooled_response_engine.py` (`94dee6c05687cf817ca2839f41a0815bee5c96c35a9538fb0892e13c0ebf100d`)
- Synthetic receipt: `data/provenance/soybean_pooled_response_engine_synthetic_validation_20260928.json` (`05cf9c223b784767a0943e30b79c2c6d3a2ba2fb64c676e5eb403fcfeb623955`)
- Boundary validator: `scripts/validate_soybean_pooled_response_engine.py` (`d3ebcef7ecb02fdc1accc3dfad61a97ddb803c7da133cf1bc114cc1854907b2b`)
- Validation provenance: `data/provenance/soybean_pooled_response_engine_validation_20260928.json` (`e76a73e1ce4c51a4722e6fdc1f0ecfd64cf835d8e8f517f311f5f717ecde791c`)
