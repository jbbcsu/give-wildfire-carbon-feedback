# Fixed positive crop support: invalid corners are small but not ignorable

## Result

The fixed all-case positive-support audit is complete. Across the existing
common EPIC-TAMU/CARAIB maize footprint, 186 unique cell/regime locations have
at least one nonpositive finite yield corner in one of the 32 audited physical
ledgers. No nonfinite corner was found. Requiring every corner to be positive
for both crop models, both climate models, both scenarios and both calendars
retains:

- 99.95451% of common-support area;
- 99.98249% of common-support external production; and
- 99.97746% of covered baseline value.

The excluded footprint is 186 unique cell/regime locations and 24.584 million
USD2005 of the 109.047-billion covered value denominator. Rainfed exclusions
account for nearly all of it: retained production/value are 99.97809% and
99.96931% for rainfed maize, versus 99.99876% and 99.99931% for irrigated
maize.

Model-specific masks differ. CARAIB has 49 unique all-case nonpositive
cell/regime locations and retains 99.99289% of value. EPIC-TAMU has 149 and
retains 99.98437%. Their union is 186 rather than 198 because some cells overlap.
The excluded value is geographically dispersed; the largest country allocations
are Israel (4.551 million USD2005), India (4.380 million), China (4.061 million),
Iran (3.009 million) and Brazil (2.340 million). Morocco ranks tenth by excluded
value (0.681 million), confirming that the previously invalid Moroccan aggregate
is not the only physical-tail issue.

## Interpretation

The invalid corners occupy a very small share of the fixed global denominators,
but this does not validate them or authorize clipping. Their economic influence
can be disproportionate in segmented, inelastic markets. A common-positive
support sensitivity is now technically defensible because the mask was defined
across **all** models/cases/corners before any restricted-support welfare result,
and the lost area, production and value are explicit.

Such a sensitivity would still estimate only the retained partial population.
It may test whether structural attribution is robust to known invalid emulator
tails; it cannot replace the full-support result, be rescaled to 100%, or be
called global validation. No welfare was recomputed in this audit.

## Reproduction

- Protocol: `FIXED_POSITIVE_CROP_SUPPORT_PROTOCOL_20260919.md`.
- Builder: `scripts/audit_fixed_positive_crop_support.py`.
- Independent validator: `scripts/validate_fixed_positive_crop_support.py`.
- Ignored result SHA-256:
  `aaae396e1af1aeac6586bba5a1e81304e310b302aad7b1cb703f6b383a2de079`.
- Validation output SHA-256:
  `8032e317ad9182fc8e3e58480df6624390fd9a907fd99c31149827c5a69f3a62`.
- The independent implementation passed 154 source, mask, coverage, value and
  gate checks. Builder/validator sampled peaks were 151.22/176.62 MB and added
  less than 0.04 MB combined.

No crop model was repaired, no welfare was recomputed, and all empirical-
damage, GIVE-export and SCC gates remain false.
