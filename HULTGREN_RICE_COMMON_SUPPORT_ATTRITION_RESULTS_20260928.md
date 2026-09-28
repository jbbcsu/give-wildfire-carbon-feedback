# Rice common-support attrition audit results

## Decision

Neither rice season passes the frozen low-attrition gate. A simple complete-case
restriction would be mildly selective for first rice and strongly selective
for second rice. It is not promoted as the rice response estimand.

| Outcome | Cells retained | Cell-years retained | Minimum annual retention | Largest absolute standardized difference | Gate |
|---|---:|---:|---:|---:|---|
| First rice | 9,298/9,564 (97.22%) | 74,234/76,348 (97.23%) | 97.21% | 0.329 | Fail |
| Second rice | 1,419/1,587 (89.41%) | 11,350/12,694 (89.41%) | 89.40% | 1.196 | Fail |

First-rice retention clears the count thresholds but fails balance. Retained
cells average 3.44 t/ha versus 4.52 t/ha among excluded cells (standardized
difference -0.329). Rx5day also narrowly exceeds the threshold (-/+
orientation retained minus excluded: +0.253), while the other registered
weather differences are at or below 0.224 in absolute value.

Second-rice attrition is materially nonrandom. Retained cells average 4.60
t/ha versus 1.24 t/ha among excluded cells (standardized difference +1.196).
The retained group is cooler (25.09 versus 28.15 C), wetter (449.7 versus
155.6 mm), has more wet days (35.4 versus 12.6), shorter maximum dry spells
(36.2 versus 73.2 days), and larger Rx1day/Rx5day. Every registered second-rice
weather contrast has an absolute standardized difference between 0.876 and
1.183.

The excluded second-rice cells are geographically concentrated: the unique
country proxy assigns 89 to Nigeria and 19 to Cambodia; 41 are geographically
ambiguous, 10 map to Mauritania, and six lack a unique proxy. These are support
diagnostics, not country damage estimates or winners/losers.

## Consequence

Using only exact MIRCA-matched second-rice cells would select a substantially
higher-yield, cooler, wetter sample and cannot be treated as a nearly complete
global second-rice estimand. First rice is closer but still fails the frozen
balance rule. No missing weights are imputed. A defensible next step must seek
a better season-area source or explicitly model/bound missing support and show
results under excluded-region sensitivities before evaluating the published
rice response.

No causal response, geographic welfare ranking, damage, or SCC is produced.

## Artifacts

- Protocol: `HULTGREN_RICE_COMMON_SUPPORT_ATTRITION_PROTOCOL_20260928.md`
- Audit: `scripts/audit_hultgren_rice_common_support_attrition.py`
- Validator: `scripts/validate_hultgren_rice_common_support_attrition.py`
- Receipt: `data/provenance/hultgren_rice_common_support_attrition_20260928.json`
- Validation: `data/provenance/hultgren_rice_common_support_attrition_validation_20260928.json`
- Compact observed-row audit table: ignored
  `data/interim/hultgren_rice_common_support_attrition_20260928.parquet`
