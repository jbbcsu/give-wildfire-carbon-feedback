# Sorghum/cotton direct-weather input results

The previously acquired NOAA nClimGrid-Daily county-average archive remains
locally available and complete: 2,700 certified source objects totaling
2,362,010,369 bytes. No new weather download was required.

Thirty-eight one-year jobs ran sequentially with peak concurrency one. Each
job revalidated its two half-year receipts and every source object used by the
existing county-average loader. The jobs produced 21,141 crop/state/county/
year feature rows before exact outcome filtering. Joining to the geography-
eligible outcome support yields 17,454 practice rows and all 8,727 paired
crop--county--years, with no missing cells in 14 checked direct-weather fields.

The fields include seasonal precipitation total, wet days, maximum consecutive
dry days, Rx5day, mean temperature, heat exceedance, three stage precipitation
amounts and shares, and precipitation concentration. Stage amounts reconcile
exactly to seasonal rainfall within `1e-6` mm. Both practices receive identical
county-average weather.

This panel is a direct-precipitation family with candidate temperature
controls. PDSI, SPEI, and scPDSI are not co-included. County averages are not
field-level weather, fixed state calendars are not realized phenology, and no
response, causal irrigation effect, national damage, or SCC is estimated.
