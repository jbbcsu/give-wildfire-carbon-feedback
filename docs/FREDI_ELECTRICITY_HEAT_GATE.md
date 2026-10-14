# FrEDI v4.1.1 electricity heat gate

Date: 2026-10-14

Status: combined transmission/distribution interface reproduced; generation/capacity, building demand, component split, matched-pulse, global, and SCC gates closed.

## Released surface and admission decision

The audit uses the official EPA [FrEDI v4.1.1 release](https://github.com/USEPA/FrEDI/releases/tag/v4.1.1), [FrEDI source](https://github.com/USEPA/FrEDI), [FrEDI_Data](https://github.com/USEPA/FrEDI_Data), and [2024 Technical Documentation](https://www.epa.gov/system/files/documents/2024-08/technical-documentation-for-fredi_aug2024.pdf). The package and data repositories use the MIT license; the package license also carries EPA's disclaimer.

The public runtime has two state-level GCM sectors:

| Runtime sector | EPA description | Released separation | Admission |
|---|---|---|---|
| `ElecSD` | Change in power-sector costs, combining heating/cooling demand and required capacity expansion | `impactType=N/A`, one `variant=NA` surface | Excluded because the prohibited building-demand channel cannot be removed source-faithfully |
| `ElecTD` | Repair/replacement costs for transmission and distribution lines, poles/towers, and transformers | Distinct from `ElecSD`; `impactType=N/A`; NoAdapt, Proactive, and Reactive variants | Admitted as one combined T&D endpoint |

The release does not split generation from capacity, demand from capacity inside `ElecSD`, transmission from distribution inside `ElecTD`, or T&D repair from replacement. No shares were allocated. `Reactive` is the primary/include-in-aggregate `ElecTD` variant; NoAdapt and Proactive remain explicit alternatives.

Flood, coastal, wildfire, urban-drainage, and SLR endpoints are outside this configuration. Building heating/cooling demand is explicitly prohibited rather than silently relabeled as generation.

## Version and source checks

The selected files from FrEDI_Data commit `b506a3e0085bb446f56acc8c7076a1aea599fbb6` were compared with the electricity objects embedded in FrEDI v4.1.1 commit `08ead1b64821acd0ff0ee95fdf662a1a73f242e1`:

- all 1,519 `ElecSD` response rows matched, maximum numerical difference `5.960464e-08`;
- all 4,557 `ElecTD` response rows matched, maximum difference `7.450581e-09`;
- all 4,312 rows of each electricity scalar matched, maximum difference `4.440892e-16`;
- no unmatched rows occurred.

All differences are below the frozen absolute `1e-6` CSV-serialization tolerance. The alignment applies only to these electricity slices.

`ElecSD` has 49 state/DC units, six GCMs, one bundled variant, and bins 1–6 with counts 294, 294, 294, 245, 245, and 147. `ElecTD` has the same geographic/GCM support, three variants, and bin counts 882, 882, 882, 735, 735, and 441. Every state/model/variant combination required by the sentinel has exact 1°C and 2°C points. Both scalar files contain 4,312 rows: all 49 units for 2006–2090 annually plus 2100, 2200, and 2300.

## Deterministic sentinel

The sentinel uses a 1.5°C CONUS anomaly relative to 1995 and exact 2020 state `elecTD_growthFactor` values. FrEDI's pinned preprocessing uses piecewise-linear interpolation; no extrapolation occurs. For each state, GCM, and adaptation variant:

```text
annual ElecTD impact = interpolated ElecTD response × 2020 state electricity-demand growth factor
CONUS impact = sum across 48 contiguous states plus DC
```

The 18 output rows preserve six named GCMs and three variants; no GCM average is constructed. Units are annual 2015 USD. Independent Decimal reaggregation reproduced all rows with maximum absolute difference `0.000000` 2015 USD/year. Both the runner and the standalone validator remained below 25 MiB peak RSS.

Ranges across the six named response surfaces are recorded only as implementation checks:

| Variant | Minimum | Maximum |
|---|---:|---:|
| NoAdapt | 3,546,144,096.769383 | 5,836,150,432.973010 |
| Proactive | 2,062,395,394.022142 | 3,868,336,515.385208 |
| Reactive | 3,426,614,186.761054 | 5,321,462,507.554133 |

These are not uncertainty intervals, policy projections, marginal-pulse effects, or SCC values.

## Fail-closed route to GIVE

1. To include generation/capacity while excluding building demand, obtain an authorized, hash-bound component-resolved `ElecSD` preprocessing artifact. Without it, keep `ElecSD` excluded.
2. Freeze the admitted endpoint (`ElecTD` combined only), adaptation treatment, six-GCM handling, price-year conversion, overlap exclusions, and global-to-CONUS temperature mapping.
3. Construct baseline and 2025 marginal-pulse temperature paths for matched GIVE/RFF-SP seeds and draws; keep every non-temperature input identical within each pair.
4. Difference annual `ElecTD` outputs within draw/GCM/variant. Do not mix in building energy demand, wildfire outages, inland flooding, urban drainage, coastal, or high-tide-flooding costs.
5. Convert 2015 USD once, discount under the matched GIVE convention, and normalize by the exact marginal pulse only after pairing and support checks pass.
6. Report any admitted result as a CONUS partial contribution, never a global SCC.

No matched-pulse or SCC computation has been run.
