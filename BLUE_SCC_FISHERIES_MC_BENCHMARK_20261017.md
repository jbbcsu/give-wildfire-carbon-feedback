# Fast published fisheries SCC benchmark

## Result

The released Blue-SCC Monte Carlo artifact provides a fast, independently
auditable **external fisheries SCC benchmark**, not a GIVE fisheries SCC.  At
the pinned public commit, the deterministic fisheries values are
$0.0548/tCO2 for the market component and $28.6760/tCO2 for the
nutrition/non-market component, or $28.7308/tCO2 combined.  Across the 400
published Monte Carlo draws (excluding the deterministic row), the market
component has median $0.0617/tCO2 and 5--95% range $0.0376--$0.0963/tCO2; the
nutrition/non-market component has median $31.3610/tCO2 and 5--95% range
$16.6418--$58.1891/tCO2; combined, the median is $31.4138/tCO2 and the 5--95%
range is $16.6959--$58.2809/tCO2.

These are published-model results under Blue-SCC settings.  They are useful
now as scale and uncertainty benchmarks.  They must not be added to GIVE:
the release does not provide matched annual baseline/pulse country paths,
does not estimate direct consumer plus producer surplus, does not harmonize
discounting and socioeconomic draws with GIVE, and does not clear the large
nutrition/mortality overlap with GIVE mortality damages.

The market-only result is much smaller and has a cleaner overlap boundary,
but it is based on multiplier-expanded projected profit rather than direct
consumer plus producer surplus.  It therefore remains a sensitivity
benchmark, not an admitted replacement sector.

## Reconciliation warning

The deterministic Monte Carlo artifact does not equal the separate Figure 4
source workbook audited earlier: the former gives $0.0548235/tCO2 market and
$28.6760139/tCO2 nutrition/non-market, whereas Figure 4 gives $0.0570404 and
$22.0405095/tCO2.  The project does not select between them.  This release
discrepancy reinforces the need for matched annual source outputs or an author
clarification before transfer.

## Reproduction

The audit verifies commit and file hash, requires the complete 401-draw by
10-component rectangle, separates the deterministic row from 400 uncertainty
draws, and emits aggregate statistics without copying source rows:

```bash
python scripts/audit_blue_scc_fisheries_mc_benchmark.py \
  --source-root /path/to/blue-scc \
  --out data/provenance/blue_scc_fisheries_mc_benchmark_20261017.json
python test/test_blue_scc_fisheries_mc_benchmark.py
```

The fastest defensible next step is to treat the published market component
as a separately reported external sensitivity while pursuing either licensed
matched annual RICE50x outputs or a direct-surplus fisheries model.  The
nutrition component remains excluded from additive GIVE totals until mortality
overlap is resolved.
