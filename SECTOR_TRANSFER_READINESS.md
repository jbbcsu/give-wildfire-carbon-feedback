# Moore labor/agriculture transfer readiness

Status date: 13 October 2026.

## Result

The Moore et al. (2026) labor pathway is the closest reproducible missing
sector to GIVE. Both 10,000-draw response-function runs are locally reproduced
under the same 2025 pulse, RFF-SP socioeconomic uncertainty, 2% Ramsey
schedule, currency basis, seed, and Julia environment. Their labor means are
$51.86/tCO2 (ISO) and $29.26/tCO2 (Lancet); the transparent equal-weight mean
is $40.56/tCO2, consistent with the article's rounded $41 headline.

`scripts/build_sector_transfer.py` now exposes only the labor and updated
agriculture partial-sector means through a hash-bound interface. It rejects
the source model's total, mortality, energy, and sea-level outputs because
those are existing GIVE sectors, not new transfer candidates. It also rejects
any attempt to label updated agriculture additive: its $29.07/tCO2 structural
mean is a replacement candidate, not an increment and not a quantity to add to
the precipitation-agriculture work.

## Overlap and claim status

- Labor: replicated global partial-SCC benchmark; candidate addition; not yet
  installed in the target GIVE model.
- Agriculture: replicated updated total-sector benchmark; replacement-only;
  the like-for-like legacy agriculture SCC and hence the replacement delta are
  not yet computed.
- The source implementation separately aggregates labor, agriculture,
  mortality, energy, and sea-level damages, and its reported component means
  sum to its total in both reproduced runs. This establishes bookkeeping
  separation, not empirical absence of cross-sector adaptation interactions.
- Agricultural labor productivity is part of the labor endpoint, while crop
  yield/market welfare is part of agriculture. They are additive in the
  published implementation; no broader claim is made for other agriculture
  or heat-adaptation modules.
- Summary receipts do not retain joint trial draws. No cross-function
  confidence interval, combined uncertainty distribution, target-model SCC,
  or grand missing-sector SCC is authorized.

## Fastest path to an integrated SCC

1. Run the source's legacy and updated agriculture configurations under the
   identical RFF-SP, pulse, discount, seed, and draw contract and retain their
   like-for-like partial-sector outputs. Use the difference only as a
   replacement delta; never add both totals.
2. Export compatible trial-level labor draws (and country paths if geographic
   allocation is required) for both ISO and Lancet specifications. Freeze or
   source-verify the structural pooling rule.
3. Install labor as a new target component and replace legacy agriculture in
   one integration branch. Prove existing mortality, energy, coastal, and
   precipitation components are not duplicated, then rerun the marginal 2025
   CO2 pulse end to end.

Until those steps pass, the transfer interface is suitable for an
overlap-controlled evidence table and implementation testing, not a combined
GIVE SCC claim.
