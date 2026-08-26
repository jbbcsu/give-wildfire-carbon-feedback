# Harvested-area, production-proxy, and value-support audit

## Purpose

Cell-count coverage is not a welfare-coverage measure. This audit asks how much
fixed-2000 MIRCA harvested area lies in cells with at least one observed GDHY
outcome in the current 1982--1989 maize and soybean panels. It also constructs
a deliberately conditional production proxy where a same-year GDHY yield is
available. It does not estimate damages or authorize SCC use.

The executable implementation is
`scripts/audit_mirca_welfare_support.py`; synthetic fail-closed tests are in
`scripts/test_audit_mirca_welfare_support.py`. Raw inputs and the generated JSON
audit remain ignored.

## Three distinct weight concepts

1. **Harvested area:** available here from the positive, fixed-vintage MIRCA
   modeled crop-grid area. Coverage is the share of all positive MIRCA area in a
   cell with at least one observed panel outcome. Irrigated and rainfed area are
   also reported separately.
2. **Conditional production proxy:** same-vintage MIRCA total harvested area
   multiplied by GDHY yield in cells where the GDHY baseline yield is observed.
   This is a constructed proxy, not observed production. The audit reports the
   share of MIRCA area for which the proxy is defined before reporting the
   conditional production fraction.
3. **Revenue or crop value:** not computed. No pinned, spatially compatible
   price or production-value input and geographic price crosswalk currently
   exists in the isolated project. A crop-wide scalar price would cancel from
   a within-crop coverage fraction and would not resolve the missing spatial
   support.

The script prohibits cross-crop aggregation without crop-value weights. It
also refuses ineligible season mappings, mismatched share/yield vintages,
non-unit irrigation shares, inconsistent area fields, negative yields, or
missing crop-specific baseline-yield inputs.

## Current fixed-2000 results

Inputs are the verified MIRCA-OS v2 2000 maize/soybean harvested-area table,
the current rainfed-calendar outcome panels (used only to identify observed
GDHY outcome support), and the GDHY 2000 maize-major and soybean yield files.

| Quantity | Maize | Soybean |
|---|---:|---:|
| Observed 1982--1989 GDHY cells | 15,098 | 6,123 |
| Observed cells with positive MIRCA area | 14,765 (97.794%) | 6,000 (97.991%) |
| Observed crop-grid-years with positive MIRCA area | 117,679 / 120,325 (97.801%) | 47,922 / 48,900 (98.000%) |
| Global positive MIRCA harvested area | 137.021 million ha | 74.093 million ha |
| MIRCA area in cells with any observed panel outcome | 108.273 million ha (79.019%) | 66.156 million ha (89.288%) |
| MIRCA area in cells with a consecutive observed-yield pair | 108.270 million ha (79.017%) | 66.156 million ha (89.288%) |
| Irrigated-area coverage | 77.688% | 84.478% |
| Rainfed-area coverage | 79.376% | 89.719% |
| MIRCA area with an observed GDHY-2000 yield | 79.016% | 89.287% |
| Conditional area-times-yield proxy in panel support | 99.99985% | 100.00000% |
| Conditional proxy in consecutive-pair support | 99.99974% | 100.00000% |

The high final row is **not** a global production-coverage result. The
production proxy is undefined on 28.752 million maize hectares and 7.937
million soybean hectares because those positive-MIRCA cells lack a GDHY-2000
yield. Consequently, the present inputs identify harvested-area coverage but
do not identify unconditional global production or crop-value coverage.
Consecutive-pair support is the pre-model support required by the current
first-difference design; later complete-case, influence, and holdout gates may
only reduce it.

Conversely, 333 GDHY-observed maize cells and 123 soybean cells have no
positive MIRCA row. Their exclusion is fully counted. MIRCA therefore supplies
no positive area weight for them, but source absence is not independent proof
that their real production or value is zero; no weight is imputed or
renormalized.

## Reproduction

```bash
./.venv/bin/python scripts/test_audit_mirca_welfare_support.py

./.venv/bin/python scripts/audit_mirca_welfare_support.py \
  --weights data/interim/mirca_os_v2/irrigation_shares_2000.parquet \
  --panel data/interim/maize_noirr_1982_1989_stage_pattern_panel.parquet \
  --panel data/interim/soy_noirr_1982_1989_stage_estimation_panel.parquet \
  --baseline-yield mai=data/raw/gdhy_v1.2_v1.3/maize_major/yield_2000.nc4 \
  --baseline-yield soy=data/raw/gdhy_v1.2_v1.3/soybean/yield_2000.nc4 \
  --baseline-year 2000 \
  --out data/interim/mirca_os_v2/irrigation_shares_2000_welfare_support_audit.json
```

The ignored JSON records exact input file sizes and SHA-512 digests. The
upstream archives and source roles are pinned in
`data/provenance/gdhy_v1.2_v1.3_20190128.toml` and
`data/provenance/mirca_os_v2_irrigation_shares.toml`.

## Remaining gate

Before welfare aggregation or an SCC claim, acquire and pin a compatible
baseline crop-production or crop-value source, document its crop and season
crosswalk, align its geography and vintage, and repeat this audit. National
totals without a defensible spatial allocation cannot by themselves value the
positive-MIRCA cells that lack GDHY yield. Until that gate closes, the current
result is an area-support diagnostic and a conditional production check only.
