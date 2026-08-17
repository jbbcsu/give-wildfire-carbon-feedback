# Crop-calendar to yield-outcome crosswalk

| ISIMIP calendar code | Calendar meaning | GDHY outcome directory | Status / rationale |
|---|---|---|---|
| `mai` | single primary maize growing period | `maize_major` | The GGCMI input-data documentation provides one maize season per grid cell; GDHY documents separate `maize_major` and `maize_second` files. The primary-season match is used; the second maize season is a future extension requiring a separately sourced calendar. |
| `ri1` | first/main rice growing period | `rice_major` | ISIMIP explicitly supplies two separate rice growing periods; GDHY explicitly supplies major and second rice outcomes. |
| `ri2` | second rice growing period | `rice_second` | Direct season-specific match. |
| `soy` | soybean | `soybean` | One season in both inputs. |
| `swh` | spring wheat | `wheat_spring` | Direct season-specific match. |
| `wwh` | winter wheat | `wheat_winter` | Direct season-specific match. |

The mapping follows the documented GDHY data-record naming convention
(`maize_major`, `maize_second`, `rice_major`, `rice_second`, `wheat_winter`,
`wheat_spring`, and `soybean`) in Iizumi and Sakai (2020),
doi:[10.1038/s41597-020-0433-7](https://doi.org/10.1038/s41597-020-0433-7), and
the ISIMIP crop-calendar documentation, which states that one growing season
is specified per crop/grid except for separate rice and wheat seasons. The
ISIMIP source is [Crop calendar input data](https://www.isimip.org/gettingstarted/input-data-bias-adjustment/details/115/).

This crosswalk makes no claim that GDHY values are direct measurements: GDHY
is a census- and satellite-informed gridded yield product. It prevents an
unjustified aggregation of second seasons and provides a clear gap for maize
double-cropping coverage.
