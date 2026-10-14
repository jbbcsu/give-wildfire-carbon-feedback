# FrEDI transport-heat deterministic smoke result

The v4.1.1 aggregate interface passed on 2026-10-14. The hash-bound output contains 36 CONUS rows at 1.5°C relative to 1995 and economic year 2020. Each row remains separate by released aggregate, adaptation variant, and GCM.

Support checks:

- 49 aligned state/DC units;
- 6 GCM response surfaces;
- 3 adaptation variants;
- 2 released aggregates;
- exact 1°C/2°C interpolation support for all 1,764 state/model/variant/bin keys per aggregate;
- exact 2020 adjustment support;
- independent reaggregation maximum absolute difference: 0.000000 2015 USD/year.

For a compact diagnostic only, the ranges across the six GCM surfaces are:

| Released aggregate | Variant | Minimum annual impact | Maximum annual impact |
|---|---:|---:|---:|
| Rail | NoAdapt | 1,302,385,637.638324 | 4,168,205,869.268230 |
| Rail | Proactive | 25,178,743.279274 | 245,536,280.797054 |
| Rail | Reactive | 1,301,042,487.815411 | 4,142,836,173.194722 |
| Roads | NoAdapt | 7,378,670,592.907807 | 141,029,692,012.372397 |
| Roads | Proactive | 3,950,848,033.180783 | 12,268,018,962.848760 |
| Roads | Reactive | 5,086,251,298.774768 | 14,886,510,077.332801 |

Units are 2015 USD/year. These are neither uncertainty intervals nor policy results. They are min/max inventory checks over six named source response surfaces at a synthetic sentinel. Component-level outputs remain unavailable, and all matched-pulse, global extrapolation, damage-integration, and SCC gates remain closed.

Artifacts:

- output SHA-256: `410dca12b52ae61ba9d6a881bcfc7d67207ba9a439f84bf7ebbd12fde4f69094`
- runner peak RSS: 29.328 MiB
- final standalone validator peak RSS: 23.812 MiB
