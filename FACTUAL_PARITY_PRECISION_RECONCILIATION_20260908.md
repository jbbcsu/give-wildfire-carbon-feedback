# Reproduce the historical arithmetic before accepting factual parity

The original1e-8absolute/1e-10relative parity gate failed. Aggregate differences
are confined to seasonal totals and their log/share/concentration transforms;
largest total differences are9.14e-5mm maize/8.53e-5mm soy. Dry spells,Rx5day,
stage temperatures,all heat fields and zero-rain flags agree exactly. No
counterfactual climate contrasts have been accepted or interpreted.

Git history independently records changes from float32 rain.sum() and
stage_rain.sum() to float64 accumulation in commits
42772db761377936f2ee9dc110921c29d38dd56c and
06628fbe4d6ed911189ba91d9ce605824d12ce5a. The retained early candidate source
covers1982–1989 and predates these changes; later source periods are separately
identified in the assembly receipt. The hypothesis is a precision difference,
not incorrect weather, calendars or irrigation allocation. Verify it below;
do not accept the hypothesis from small magnitude alone.

Reconstruct BOTH float32 and float64 season/stage totals from the acquired
factual daily precipitation on exact existing calendar windows, every cell,
1982–2010. Require current primitive totals to equal reconstructed float64
totals exactly. Reproduce legacy arithmetic for1982–1989 only, keeping later
float64 totals and every other primitive unchanged. Recompute the same
nonlinear basis BEFORE fixed irrigation weighting. Require all precipitation
features of this legacy reconstruction to match retained historical features
at the original tight tolerance on every shared observed key.

If both checks pass, a hash-bound reconciliation receipt can document why old
and new representations differ while validating the new float64 inputs.
The final comparison must still separately match all unaffected fields at the
original tolerance, verify exact new/old product identities and use unchanged
float64 arithmetic on both factual/counterclim paths. Do not overwrite old
results, manufacture matching rows, round away differences, or change the
numeric tolerance. Preserve the original failed comparison. Any discrepancy
not explained by this predeclared reconstruction remains a failed gate.

The first attempted uniform early-period float32 reconstruction did not pass;
its failed log is preserved. Before another check, refine the audit to the
actual hash-bound early unweighted source panels: require every retained
season/stage total to equal either the EXACT reconstructed float32 result or
the EXACT reconstructed float64 result. Report counts by crop/regime/primitive,
including values matching both. This can identify mixed source precision,
without guessing that every early irrigation panel used the same arithmetic.
Any value matching neither fails. Reassemble the retained reference only from
those verified original primitives, then apply the original tight weighted-
feature parity gate. The new float64 raw-reconstruction requirement remains
unchanged. No counterfactual contrast has informed this audit refinement.
