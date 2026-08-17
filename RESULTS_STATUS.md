# Analysis status and claim ledger

Updated: 2026-08-17. This file records completed computational milestones; it
does not report final response estimates or SCC values.

| Item | Status | Permitted use |
|---|---|---|
| GDHY v1.2/v1.3 yields | Acquired and checksum-verified | Outcome panel after coordinate checks |
| GGCMI Phase 3 2015soc calendars | 12 crop/irrigation files acquired and SHA-512 verified | Crop-year/stage windows |
| ISIMIP3a daily `pr` | 1981–2019 acquired; source sizes and SHA-512 recorded | Seasonal, dry-spell, wet-day, and extreme features |
| ISIMIP3a daily `tas` | 1981–2019 acquired; source sizes and SHA-512 recorded | Joint temperature control |
| `tasmax` / `tasmin` | Download in progress | Required before final heat-extreme specification |
| Maize/rainfed pilot | Real 2-latitude, 1982–89 feature and GDHY join completed | Pipeline/coordinate/feature validation only |
| Global maize/rainfed, 1982–89 | Season-level feature panel and GDHY join complete: 539,360 potential crop-year rows; 120,399 observed-yield rows across 15,103 cells | Workflow/scaling diagnostic only; no SCC input |
| Other crops/periods/scenarios | Not yet complete | No global response or SCC claim |

## Completed empirical checks

The pilot produced 5,488 crop-year feature rows, had no duplicate crop-year
grid keys, and passed nonnegative precipitation and stage-to-season
reconciliation checks. The exact ISIMIP/GDHY coordinate conversion was
validated; 43.4% of potential calendar cells in this pilot had an observed
GDHY yield. That coverage rate is a data-support diagnostic, not a global
agricultural coverage estimate.

The fixed-effects pilot fit exists only to test panel dimensionality and
numerical conditioning. Its coefficients and in-sample fit are not reported
in the manuscript and are prohibited from SCC integration by the validation
protocol.

The global maize/rainfed panel passed the same coordinate and uniqueness
checks and supported a scalable two-way within-estimator run. This does not
clear the main-analysis gate: stage-resolved features, remaining crops/years,
holdouts, uncertainty, CO2 treatment, welfare translation, and matched future
baseline/pulse paths remain outstanding.
