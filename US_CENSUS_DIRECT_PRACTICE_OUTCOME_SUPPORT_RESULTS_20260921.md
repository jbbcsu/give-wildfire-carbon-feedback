# Census direct-practice outcome route: no matched yield support

## Finding

The exact USDA Census of Agriculture query does not provide the matched county
production and harvested-area records needed to construct newer
practice-specific corn or soybean yields. Twenty-four count-only official API
queries crossed two crops, two practices, three Census years, and the two
required quantities. No values were downloaded.

Corn irrigated harvested-area support is large (1,852 county rows in 2012,
1,591 in 2017, and 1,710 in 2022), but the identically filtered production
queries return zero rows. Every corn non-irrigated and soybean practice-specific
area and production query also returns zero. Consequently, zero of the 12
crop/practice/year cells passes the preregistered requirement that both source
queries contain at least 100 rows.

The area counts are useful for irrigation-share screening, as already done in
the project, but they cannot be divided into absent production records to
construct yield. We do not substitute all-practice production, infer
non-irrigated area as a residual, mix unmatched filters, or treat suppressed
records as zero.

## Implication

This closes a second proposed route to post-2019 direct-practice crop yields.
The U.S. evidence hierarchy remains:

1. the regional 1981--2019 paired reported-practice panel for historical
   associations and competing-moisture validation;
2. the nationwide 1981--2025 all-practice panel in counties selected by a
   pre-outcome low-irrigation-share screen for terminal prediction; and
3. explicit recognition that item 2 is not observed non-irrigated yield.

An alternative independent outcome source would need genuinely matched
practice-specific production and area or a directly reported practice-specific
yield. This result does not establish that no such source exists; it establishes
that the exact Quick Stats Census route tested here does not supply it.

## Reproduction and boundaries

- Count result SHA-256:
  `719d8e7fa12fd05c39da70c49530e50b730957ec88b477f5cbacdbba1729091e`.
- Structural validation SHA-256:
  `79b64af05f660e7cb179214c552d64377fdc84b218fde26d000c5006a33ee237`.
- The separate validator passed 435 query-identity, matrix-completeness,
  arithmetic, credential-exclusion, and claim-boundary checks.
- Count and validation workers used 32,489,472 and 212,992 bytes sampled peak
  process-group RSS, below 512 MiB, with the 130 GiB disk floor intact.
- The ignored API key is absent from parameters, outputs, logs, and Git.

No yield ratio, climate response, damage, or SCC estimate was calculated.
