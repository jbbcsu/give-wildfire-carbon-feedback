# Soybean token-gated production reader result

Date: 2026-10-04

## Result

The pooled soybean path now has a production level reader that remains
unreachable without the existing exact authorization token. The reader binds
the four declared source roles (`direct`, `heat`, `scpdsi`, and
`country_proxy`), requires the token to bind both the reader implementation and
its configuration, verifies each source hash only after authorization, and
then reads only projected columns in sequential 8,192-row batches. It validates
the fixed MIRCA basis metadata, crop and 1982--2016 year support, coordinate and
feature finiteness, outcome missingness, singleton country-proxy ownership, and
exact moisture-family/heat support.

The bounded implementation validates every Arrow batch before conversion and
accumulates only rows with finite, strictly positive observed yields. It tracks
full-source row counts and year coverage separately. Unobserved rows are
validated against the flag/missingness contract and discarded before pandas
conversion, rather than retained in a list for a full-table concatenation.

No response engine is imported or invoked by the reader. The existing
execution adapter remains responsible for pair construction, frozen sample
selection, and the separately authorized engine call.

## Production-contract correction

The source receipts report many more panel rows than observed outcomes. The
production tables therefore use `yield_observed = false` with a missing yield
magnitude outside observed GDHY support. The adapter previously required every
level yield to be finite, which was compatible with its all-observed synthetic
fixture but incompatible with the declared real source contract.

The adapter now requires finite, strictly positive yield exactly when
`yield_observed` is true and missing yield exactly when it is false. Valid
unobserved levels are removed only during positive-pair construction. A finite
unobserved yield or a missing/nonpositive observed yield fails closed. Source
and heat outcome equality now treats paired missing values as equal.

## Validation

The reader synthetic-file suite passes all 19 checks. It verifies:

- authorization and reader/config token binding before source hash or open;
- exact four-role path closure and path-containment checks;
- hash-before-Parquet-decode behavior and rejection of a wrong hash;
- per-batch validation before observed-row filtering and pandas conversion;
- separate full-source year/support accounting without accumulating unobserved rows;
- projected-column batching with basis-constant validation;
- singleton country-proxy filtering;
- direct/heat and scPDSI/heat exact support;
- valid unobserved-yield handling; and
- fail-closed behavior for a basis mismatch and path escape.

The synthetic fixture contains 105 full-source levels per family. Each reader
validates all 105 in Arrow, accumulates 104 observed-positive rows, and returns
69 singleton-country rows after excluding one unobserved row and the ambiguous
country cell; those rows yield 66 positive consecutive pairs. Reader tests
peaked at 106,577,920 bytes RSS. The independent validator passed 15 checks at
25,411,584 bytes RSS. The refreshed adapter suite passes all 19
checks across all three families at 153,862,144 bytes RSS; its independent
validator passed at 25,378,816 bytes. All are below the 536,870,912-byte
contract.

Primary files and receipts:

- `config/soybean_pooled_response_production_reader_v1.toml`
- `scripts/soybean_pooled_response_production_reader.py`
- `scripts/test_soybean_pooled_response_production_reader.py`
- `scripts/validate_soybean_pooled_response_production_reader.py`
- `data/provenance/soybean_pooled_response_production_reader_tests_20261004.json`
- `data/provenance/soybean_pooled_response_production_reader_validation_20261004.json`
- `data/provenance/soybean_pooled_response_execution_adapter_tests_20261004.json`
- `data/provenance/soybean_pooled_response_execution_adapter_validation_20261004.json`

## Claim boundary and next gate

All work was synthetic or metadata-only. No real outcome-bearing path was
opened or hashed, no production token was created, no real fit or coefficient
was computed, and no response, winner/loser, damage, SCC, or GIVE claim is
authorized.

The nearest scientific gate remains the explicitly authorized pooled soybean
fit. The authorization token must use the exact statement in
`config/soybean_pooled_response_execution_gate_v1.toml` and must additionally
bind this reader and reader configuration. After authorization, execution
should run one family at a time and retain the frozen hierarchy: quantity is
primary; distribution and scPDSI are mutually exclusive challengers. A passing
associational fit would still require the locked 2012--2016 transport test and
a matched marginal-CO2 soybean climate path before any damage or GIVE SCC use.
