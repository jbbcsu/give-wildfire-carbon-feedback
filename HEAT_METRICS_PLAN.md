# Heat-extreme feature plan

Daily ISIMIP3a `tasmax` and `tasmin` are present in the isolated raw-data
manifest. Heat is constructed in a key-compatible table separate from direct
precipitation-pattern features, then joined only within a declared response
specification.

## Implementation rule

`scripts/build_crop_heat_features.py` requires one or more explicit
daily-maximum thresholds in Celsius. It calculates, for each calendar-aligned
crop year, the number of days at/above each threshold and the associated
degree-day excess, plus mean daily maximum temperature. It has no default
threshold because a universal threshold would be an unrecorded modeling
choice. It excludes seasons incomplete at a climate-file edge rather than
filling them.

## Estimation rule

Lock crop-specific candidate thresholds and functional form before the main
outcome fit, compare them only within nested spatial/time/extreme holdouts,
and retain threshold uncertainty when validation does not identify one clear
specification. Temperature and precipitation terms are estimated jointly; the
heat feature is not an independent precipitation damage add-on.

## SCC rule

For every matched climate draw, heat changes are calculated from the paired
baseline and CO2-pulse paths. The agricultural response is applied once to
the joint feature vector, then passed once through the agricultural welfare
replacement. No separate heat SCC is added to the precipitation SCC.
