# Hultgren rice recoverable-gates results

Date: 2026-09-25

## Outcome

Both investigated rice gates were recoverable without inventing data.

The public Git history contains a deleted prepared regression panel at
`Fig1/Local_Impacts/data/crop_data/rice_gmfd_v1_ready.dta`. Its Git blob is
`3bf4ad7bea38a217f752328c20851e0175582c4f`; the 143,208,457-byte file has
SHA-256 `a118f3ce5dd54f506b75de9fc1dff0b01a9e9034509f6b9b925b937a1beb63b4`,
178,157 rows, and 180 columns. It is reachable at historical commit
`dae5fe8d0d4a260328e4baa45b547368bd6790b3` but absent from the pinned current
commit. No repository license was located, so the raw file remains in ignored
storage and is not redistributed.

The prepared panel yields 166,354 rows complete on log yield, the four
published moderators, and the nine rice weather primitives. Iterative removal
of absorbed-effect singletons removes exactly 180 rows—163 singleton `uid`
rows, 17 singleton country-year rows, and two singleton ADM1 rows before the
union—and reproduces the published 166,174 estimation observations. It also
reproduces 656 country-year and 581 ADM1 clusters. An independent pass matches
all min/max and p01/p99 summaries exactly.

## Historical application-domain diagnostic

Applying the recovered source weather bounds to the India-corrected historical
`ri1` ledgers gives 545,616 unweighted cell-years. Across all nine weather
primitives jointly, 97.0613% lie inside the author estimation-sample min/max
box and 57.6816% lie inside the joint p01--p99 box. These are unweighted
cell-level support diagnostics, not response or damage estimates. Full response
domain validation remains incomplete because a season-separated cell moderator
ledger has not yet been built.

## India reporting-year correction

The validated author-region/cell geometry identifies 423 retained cells lying
exclusively within India and 77 cells intersecting both India and another
country. Only 12 retained cells have calendars for which the India and generic
report-year mappings differ. All 12 lie exclusively within India, so there are
zero rule-sensitive India-border ambiguities.

For those cells, the source India rule shifts the cross-year crop season from
the generic previous-year/harvest-year pair to the report-year/following-year
pair. Rebuilding 27 historical years in both calendar branches changes 648 of
545,616 cell-years. All 544,968 unflagged rows remain bit-for-bit unchanged.
Independent validation finds:

- 576 corrected rows agree with the following generic crop-year row within
  `5.82e-11`;
- all 648 corrected rows match direct daily reconstruction exactly;
- corrected `ri1_noirr` and `ri1_firr` branches remain identical; and
- no area, production, season, or irrigation weights are introduced.

The correction builder peaked at 494,436,352 bytes RSS and the streaming
validator at 369,590,272 bytes, both below 512 MiB.

## Artifacts

- Public-history audit:
  `data/provenance/hultgren_rice_public_history_domain_audit_20260925.json`
- Exact author support:
  `data/provenance/hultgren_rice_author_sample_support_20260925.json`
- Independent support validation:
  `data/provenance/hultgren_rice_author_sample_support_validation_20260925.json`
- India correction receipt:
  `data/provenance/hultgren_rice_india_reporting_year_correction_20260925.json`
- India validation:
  `data/provenance/hultgren_rice_india_reporting_year_validation_20260925.json`
- Historical weather-domain diagnostic:
  `data/provenance/hultgren_rice_historical_weather_domain_20260925.json`
- Corrected ledgers and cell diagnostics:
  `data/interim/hultgren_rice_historical_preflight_india_corrected_20260925/`

## Remaining limitations

- The source panel and code repository have no located license; raw historical
  files must remain untracked and cannot be redistributed.
- Moderator support bounds are recovered, but those moderators have not yet
  been constructed on the season-separated historical grid.
- MIRCA rice-season reconciliation remains unresolved; nothing here supplies
  `ri1`/`ri2`/Rice3 aggregation weights.
- No response contrast, weighted global response, damage estimate, or SCC is
  produced.
