# LOCA2 direct native-chunk reader result

## Engineering result

The Box Butte County 2001--2012 LOCA2 sentinel now has substantially more
memory headroom under the fixed 512 MiB worker ceiling. The established
prepared-input route was scientifically successful but peaked at 506.84 and
506.33 MiB for its two six-year partitions. The new route preserves the same
county, model, member, dates, cells, weights, feature definitions, and
outcome-blind distribution comparison while changing only data access:

1. decode one native Zarr time/spatial chunk directly;
2. select the county cells locally rather than through xarray vectorized
   indexing; and
3. release precipitation before decoding the temperature pair.

The full 2001--2006 and 2007--2012 partitions now peak at **352.38 MiB** and
**368.72 MiB**, respectively. This reduces peak memory by 138--154 MiB without
shortening the established twelve-year support. Their local combination peaks
at 137.81 MiB.

## Independent parity validation

Synthetic tests establish exact selected-cell reconstruction and feature-basis
agreement to `1e-12`. All 24 LOCA2 tests pass. An independent validator then
compares the new twelve-year result with the established prepared-input result:

- maximum absolute difference across all common county-year climate features:
  `3.55e-15`;
- maximum absolute difference across all saved means, standard deviations,
  biases, quantiles, and quantile RMSE values: `3.55e-15`; and
- both climate workers complete below 512 MiB.

The scientific Box Butte diagnostic is therefore unchanged: GFDL seasonal
precipitation is 9.61 mm below nClimGrid, maximum dry spell is 1.62 days
longer, RX5day is 5.63 mm lower, and mean seasonal temperature is 0.89 °C
higher. Standard-deviation ratios remain 0.620, 1.245, 0.715, and 0.513.

## Claim boundary and next step

This is an exact engineering improvement, not a new climate-impact result. It
opens no PDSI, crop-response, damage, or SCC gate. Its value is that the same
bounded reader can now be scaled to additional counties and models with much
less risk of freezing the machine. A climate-to-PDSI bridge still requires a
water-balance calculation using precipitation and atmospheric demand or a
published transferable drought projection.

## Reproduction

- `scripts/build_historical_climate_sentinel.py`
- `scripts/combine_historical_climate_partitions.py`
- `scripts/validate_direct_v2_parity.py`
- `config/loca2_us_box_butte_gfdl_historical_2001_2006_variable_serial_v2.toml`
- `config/loca2_us_box_butte_gfdl_historical_2007_2012_variable_serial_v2.toml`
- `data/provenance/loca2_box_butte_gfdl_historical_climate_sentinel_2001_2012_direct_v2_20261013.json`
- `data/provenance/loca2_box_butte_gfdl_historical_direct_v2_parity_validation_20261013.json`
