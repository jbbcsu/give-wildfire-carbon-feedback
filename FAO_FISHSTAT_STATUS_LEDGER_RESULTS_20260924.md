# FAO FishStat marine-tonnage status ledger

## Result

The 27,625-record marine live-weight panel was reduced to a lossless annual
status ledger for 1950--2024. The output contains all 75 years by the seven
status codes present in this slice (`A`, `E`, `I`, `N`, `O`, `Q`, and `X`), or
525 rows. A separate implementation reconstructed every cell count, positive-
cell count, and tonnage sum directly from the full 30,918-record reconciled
export; all values match exactly.

Across the full period, positive tonnage is carried by `A` (4.527 billion
tonnes), `I` (331.022 million), `E` (12.882 million), and `X` (0.145 million).
Codes `N`, `O`, and `Q` have no positive cells but remain distinct source
states rather than observed zero catch.

Status composition changes materially. Code `I` supplies only 0.024% of 1950
positive tonnage, 2.92% in 1980, 11.45% in 2014, and 12.06% in 2024. Code `E`
supplies 4.52% in 2024. A calibration that pools all positive statuses therefore
embeds a time-varying observation-quality mixture.

## Decision boundary

This result does not decide which status codes are admissible for FishMIP
calibration. The primary calibration family and status sensitivity must be
pre-registered before fitting. The ledger does not identify effort,
management, biomass, climate causation, EEZ production, welfare, damage, or
SCC.

The generated CSV remains ignored by Git. Versioned build and independent-
validation receipts preserve its checksum and exact reconstruction evidence.
