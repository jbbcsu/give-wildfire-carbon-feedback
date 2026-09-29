# Blue-SCC market pathway: multiplier and welfare decomposition audit

## Decision

The published regional output multiplier is algebraically separable from the
released country temperature coefficient, but an exact multiplier-free
coefficient set is **not reproducible from the pinned tracked repository**.
The decomposition gate therefore remains closed rather than manufacturing a
country assignment or silently applying a modern geography package.

The released workflow first computes a direct profit contrast relative to
RCP2.6. It then multiplies both scenario and baseline profit by a country-level
regional multiplier before expressing their difference as a GDP fraction and
fitting the country temperature slope. Because that multiplier is constant
within country in the released code, the multiplier-free slope is
mathematically the published slope divided by the exact country multiplier.

## Why the numerical decomposition is blocked

The pinned repository does not track any of the ten registered upstream or
intermediate files checked by the audit, including the Free et al. profit RDS,
the derived pre-regression fisheries panel, the SSP GDP input, and the four
temperature scenario files. The GDP normalization also calls the World Bank
API live without preserving the response. The repository tracks none of
`renv.lock`, `DESCRIPTION`,
or the `setup.r` referenced by the README. The code assigns multiplier regions
with the unversioned R `countrycode` package and does not persist the resulting
country-to-multiplier table.

Consequently, the source-pinned artifacts do not establish which of the six
regional multipliers—or the 4.55 unmatched default—was applied to every one of
the 143 coefficient rows. Dividing coefficients using a newly reconstructed
mapping would introduce an unregistered assumption and would not be an exact
replication.

## Welfare boundary

Removing the indirect and induced output multiplier would recover a
multiplier-free **profit/GDP response**, conditional on the missing exact
assignment. It would not create consumer surplus, and the released materials
do not establish that the dynamic modeled profit measure equals the producer
surplus required by the local contract. Thus even the six fully covered FUND
regions from the country-transfer audit are not welfare-ready.

No country coefficient was derived, no missing country was filled or treated
as zero, no incomplete region was renormalized, and no SCC was calculated.

## Required evidence to reopen the gate

A licensed release must provide either the exact country-to-multiplier mapping
or the source/intermediate profit panel plus versioned dependencies. A
multiplier-free refit can then be checked against the algebraic division result.
Consumer surplus and the interpretation of modeled profit as producer surplus
still require separate evidence.

Reproduce against a separate checkout of the pinned commit:

```bash
python3 scripts/audit_blue_scc_market_welfare_decomposition.py \
  --source-root /path/to/blue-scc
python3 test/test_blue_scc_market_welfare_decomposition.py
```
