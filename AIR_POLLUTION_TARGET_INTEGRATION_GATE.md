# Air-pollution target integration gate

## Finished result

The published McDuffie et al. (2026) scalars are now price-year harmonized from
2024 USD to GIVE's 2020 USD using a pinned BEA GDP implicit price deflator. The
2026-vintage factor is `105.377 / 125.587 = 0.839075700510403...`.

| Source-reported pathway | Source scalar | Harmonized scalar | Status |
|---|---:|---:|---|
| Wildfire-smoke PM2.5 mortality | +$50.00 (2020 USD, 2025 pulse) | +$50.00 | benchmark only |
| Surface-ozone health | +$23.00 (2024 USD, 2030 pulse) | +$19.298741 | benchmark only |
| Nonwildfire meteorological PM2.5 health | -$38.00 (2024 USD, 2030 pulse) | -$31.884877 | benchmark only |
| Published ozone-plus-PM2.5 net | -$15.00 (2024 USD, 2030 pulse) | -$12.586136 | preferred EPA bundle benchmark |

The conversion changes only the price year. It does not convert McDuffie's 2030
pulse to GIVE's 2025 target pulse and does not create annual damage paths.

## Overlap decisions

- McDuffie excludes open burning, including wildfires. Its modeled physical
  pathway is therefore separate from direct wildfire-smoke PM2.5 in the source
  study.
- Direct wildfire-smoke mortality and the separate wildfire-CO2 feedback are
  different endpoints. The smoke scalar is nevertheless not operationally
  admitted because none of the eight required draft artifact groups has passed.
- No air-pollution mortality component is currently additive to baseline GIVE.
  GIVE's Cromar component values temperature-associated **net all-cause
  mortality**. Cromar et al. report that air pollution was often handled as a
  potential mediator in the underlying temperature-health literature. Without
  a source-study decomposition or a replacement joint mortality module,
  endpoint double counting cannot be ruled out.

## Remaining gates

1. Obtain final article-consistent annual marginal damage streams, or rerun the
   McDuffie system, to harmonize the 2030 pulse without inventing a path.
2. Resolve mortality overlap through a mutually exclusive baseline or a joint
   replacement mortality module.
3. Reproduce the final McDuffie and Williams results locally.
4. Preserve the published McDuffie net as the preferred bundle until joint
   component draws or covariance are available; do not combine marginal
   component intervals independently.

Until all applicable gates pass, the target table is usable for benchmark and
sensitivity comparisons only—not for addition to the headline GIVE SCC.
