# Soybean production execution sample-boundary result

Date: 2026-10-03

## Result

The pooled soybean execution adapter had a fail-closed production mismatch.
Its declared level sources cover 1982--2016, so exact consecutive-pair
construction would yield pair end-years 1983--2016. The production estimator
correctly accepts only the frozen 1983--2010 training period. Before this
change, the adapter passed the entire constructed pair table to the estimator,
which would have stopped every authorized production run at the engine's year
contract rather than fitting the preregistered sample.

The adapter now applies an explicit sample-selection boundary before engine
invocation. Production requires every pair end-year from 1983 through 2016 to
be represented, retains only 1983--2010 for fitting, excludes the 2011 buffer,
and locks 2012--2016 outside the fit for a later terminal-transport operation.
Missing boundary years, a non-Boolean test-mode flag, or any buffer/terminal
leakage fail closed. Synthetic alternate years remain available only through
the explicit synthetic test mode.

## Validation

The synthetic adapter suite passes all 17 checks. It executes quantity,
distribution, and scPDSI families separately on 720 synthetic levels and 660
pairs per family; confirms exact current-minus-prior construction; confirms
the 1983--2010 production selection and 2011/2012--2016 exclusions; rejects an
incomplete production year set; and verifies that missing or invalid
production authorization stops before loader or engine access. The independent
static/receipt validator passes 12 checks, including ordering of authorization,
loader access, sample selection, and engine invocation.

The test process peaked at 153,485,312 bytes and the independent validator at
25,362,432 bytes, both below the still-binding 536,870,912-byte contract. The
broader user resource allowance was not needed.

Primary receipts:

- `data/provenance/soybean_pooled_response_execution_adapter_tests_20261003.json`
- `data/provenance/soybean_pooled_response_execution_adapter_validation_20261003.json`

## Claim boundary and next gate

No real outcome magnitude was read, no production token was created, no real
fit was invoked, and no coefficient, yield effect, geographic winner/loser,
damage, SCC, or GIVE input was produced. All claim gates remain closed.

The nearest scientific milestone is still the preregistered pooled soybean
associational fit. It requires the exact explicit authorization statement and
hash-bound production token specified by
`config/soybean_pooled_response_execution_gate_v1.toml`. A production level
reader also remains deliberately absent from the committed adapter; it should
be implemented only behind that validated token and should stream projected
columns rather than materializing all three source families. Even a successful
fit would remain associational and would still need the locked 2012--2016
transport gate plus a matched marginal-CO2 soybean climate path before any
damage or GIVE SCC calculation.
