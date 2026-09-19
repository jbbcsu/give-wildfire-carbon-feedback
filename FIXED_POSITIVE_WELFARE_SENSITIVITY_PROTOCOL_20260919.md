# Fixed-positive-support four-corner welfare sensitivity protocol

Status: frozen after the coverage audit and before restricted-support welfare
execution. This is a partial-population structural sensitivity, not a crop-model
repair, global damage estimate or SCC result.

Use the both-model-positive mask registered in
`FIXED_POSITIVE_CROP_SUPPORT_PROTOCOL_20260919.md`: retain a cell/regime only if
all four yield corners are finite and strictly positive in every CARAIB and
EPIC-TAMU climate/scenario/calendar case. Reconstruct that mask from all 32
hash-bound ledgers; do not alter it case by case.

Allocate each country/regime baseline value to retained cells in proportion to
the original fixed external production weights. Excluded value is removed from
the denominator, explicitly reported, and never redistributed or scaled back to
100 percent. Aggregate retained cell yield multipliers within country/regime,
then aggregate supply shifts into the prespecified single global maize market.

Evaluate all four physical corners under the same three elasticity pairs, two
yield-to-supply mappings and fixed-management assumption. Apply the same
two-driver welfare Shapley formulas as the full-support attribution. Compare
restricted with full-support precipitation, temperature and joint damage where
the latter is mechanically available. The previously inadmissible EPIC
IPSL/SSP5-8.5 case may be calculated only if every restricted country/regime
aggregate is positive; it must remain labeled a restricted-support diagnostic.

Report retained/excluded cells, production and value, corner supply multipliers,
Shapley closure and differences from the full-support result. Do not select a
model or support rule by damage magnitude. Interpretation, GIVE export and SCC
flags remain false regardless of arithmetic success.

An independent validator will reconstruct the fixed mask, value allocation,
four corners, market equations and Shapley arithmetic. One worker remains under
sampled 512 MiB RSS, 64 MiB output and 130 GiB free-disk safeguards.
