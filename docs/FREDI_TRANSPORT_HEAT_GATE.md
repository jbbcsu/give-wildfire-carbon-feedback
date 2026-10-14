# FrEDI v4.1.1 transport-heat gate

Date: 2026-10-14

Status: aggregate interface reproduced; component-resolved transport, matched-pulse, global, and SCC gates closed.

## Authoritative source surface

The audit pins the official EPA [FrEDI v4.1.1 release](https://github.com/USEPA/FrEDI/releases/tag/v4.1.1), the official [FrEDI repository](https://github.com/USEPA/FrEDI), the official [FrEDI_Data repository](https://github.com/USEPA/FrEDI_Data), and EPA's [2024 Technical Documentation](https://www.epa.gov/system/files/documents/2024-08/technical-documentation-for-fredi_aug2024.pdf) and [appendices](https://www.epa.gov/system/files/documents/2024-08/technical-documentation-for-fredi_appendices_aug2024.pdf).

Because the pinned FrEDI_Data commit postdates the package tag, it was compared directly with the `sysdata.rda` embedded in v4.1.1. Both scaled-response tables matched all 4,557 rows, all scalar tables matched every selected row, and the maximum numerical difference was `2.273737e-13`, below the frozen `1e-12` tolerance. This establishes version alignment for the selected transport surface; it does not assert alignment for any other FrEDI sector.

FrEDI is an R package released under the MIT license with an EPA disclaimer. FrEDI_Data is also MIT-licensed. The runtime scope is the contiguous United States: 48 states plus the District of Columbia. Temperature input is a CONUS annual anomaly in degrees Celsius relative to 1995, the central year of the 1986–2005 baseline. FrEDI economic outputs are annual 2015 USD.

The pinned runtime metadata reports:

- `Roads`: GCM-driven, state-level, physical measure `Road Miles`, `impactType=N/A`, economic scalar `none`;
- `Rail`: GCM-driven, state-level, physical measure `Rail Miles`, `impactType=N/A`, economic scalar `none`;
- `NoAdapt`, `Proactive`, and `Reactive` variants for both sectors;
- `Reactive` is the primary/include-in-aggregate variant; the other variants are alternatives.

The official preprocessing code constructs piecewise-linear impact functions with R `approxfun(method="linear", rule=1)`. The runtime computes `physScalar = physScalarValue * physAdjValue * damageAdjValue`, `physEconScalar = econScalar * physScalar`, and `annual_impacts = scaled_impacts * physEconScalar`. For Roads and Rail the economic scalar is one. In the bounded 2020 sentinel this reduces to:

```text
Roads = interpolated scaled response × fixed road miles × 2020 variant-specific road adjustment
Rail  = interpolated scaled response × fixed rail miles × 2020 national rail-growth factor
```

The effective scaled-response unit is 2015 USD per infrastructure mile per year; after the mileage and adjustment scalars, the reported annual-impact unit is 2015 USD per year.

## Exact support and exclusions

Each released aggregate response file has 4,557 rows, 49 state/DC units, six GCMs, three variants, and integer temperature bins 1–6. Counts by bin are 882, 882, 882, 735, 735, and 441. Every state/model/variant combination is present at both 1°C and 2°C, so the 1.5°C sentinel requires no extrapolation. The road adjustment files cover every year 2010–2090 for all 49 units. Road and rail mileage files have identical 2010 and 2090 endpoints. The rail-growth file includes an exact 2020 value.

The execution surface admits only `Roads` and `Rail` with `model_type=GCM`. It never reads SLR files and excludes Coastal Properties, High-Tide Flooding, Inland Flooding, and Urban Drainage. No global extrapolation is allowed.

## Component-resolution blocker

EPA's technical documentation describes study-level costs including road repair/user/delay and rail repair/delay. The released v4.1.1 runtime does not retain those as separate output types: the runtime metadata gives both sectors `impactType=N/A`, and every row in both public scaled-impact CSVs likewise has `impactType=NA`. Consequently:

| Requested endpoint | Public v4.1.1 status |
|---|---|
| Road repair | unavailable separately; included in combined `Roads` |
| Road user | unavailable separately; included in combined `Roads` |
| Rail replacement | unavailable separately; included in combined `Rail` |
| Rail delay | unavailable separately; included in combined `Rail` |

The audit does not divide either aggregate using assumed shares. A component-resolved implementation requires source-faithful component tables or preprocessing artifacts from EPA/the underlying transport analysis. Treating the two aggregates as an admissible bundled alternative would require an explicit protocol decision; it is not implied here.

## Deterministic smoke test

The runner evaluates a uniform 1.5°C CONUS anomaly at economic year 2020, independently for each of six GCM response surfaces and three adaptation variants. It linearly interpolates only between the 1°C and 2°C source points, applies the exact 2020 scalars, and sums the 49 state/DC values. It does not average GCMs.

The result has 36 rows: 2 released aggregates × 3 variants × 6 GCMs. Independent Decimal arithmetic reproduced every reported value to the output precision (maximum absolute difference 0.000000 2015 USD/year). After the shared source manifest was extended for the separate electricity audit, the refreshed transport runner peak RSS was 27.562 MiB and validator peak RSS was 23.734 MiB, both far below 512 MiB.

These figures are implementation sentinels. The 1.5°C/2020 combination is not a GIVE scenario, a marginal emissions experiment, a probability-weighted estimate, or an SCC.

## Fail-closed path to matched GIVE pulse runs

1. Resolve the component blocker by obtaining hash-bound, public-or-authorized component-resolved response artifacts for all four endpoints. Otherwise keep the component gate closed.
2. Freeze the FrEDI version, adaptation variant (the released primary is `Reactive`), GCM treatment, CONUS conversion, price-year conversion, and overlap boundary before running outcomes.
3. For each matched RFF-SP/GIVE draw and seed, construct baseline and 2025 marginal-pulse global-temperature paths, then apply the same pinned global-to-CONUS temperature mapping to both. Keep all non-temperature inputs identical within a pair.
4. Evaluate baseline and pulse paths without model averaging or endpoint stacking; difference annual CONUS damages within draw, GCM, variant, and endpoint.
5. Convert 2015 USD to the predeclared GIVE price year once, discount under the matched GIVE convention, and normalize by the exact marginal pulse only after all pairing checks pass.
6. Report the result as a CONUS partial contribution. Do not label it a global SCC and do not add flood/coastal transport sectors to this heat-only module.

No step in this project has crossed gates 1–6.
