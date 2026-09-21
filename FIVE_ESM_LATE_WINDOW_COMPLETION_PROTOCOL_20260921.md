# Five-ESM late-window rainfed-maize weather completion protocol

## Purpose

Complete the already source-pinned 2092--2099 direct-daily weather matrix for
five ISIMIP3b climate models, three SSPs, and one fixed rainfed-maize calendar.
The existing matrix is complete for UKESM1-0-LL, IPSL-CM6A-LR and
MPI-ESM1-2-HR. It is missing 2093--2099 for GFDL-ESM4 under SSP3-7.0 and
SSP5-8.5 and for MRI-ESM2-0 under SSP1-2.6 and SSP3-7.0: 28 annual panels.

This is a climate-exposure analysis only. It reads no yield observations,
estimates no crop response, and produces no agricultural damage or SCC.

## Frozen construction

- Sources: the registered version-`20210512` ISIMIP3b `pr` and `tas` files,
  exact ESM member, scenario, decade, bytes and SHA-512 already recorded in
  `data/provenance/isimip3b_later_century_*_2091_2100.toml`.
- Crop/calendar: `mai`, `noirr`, the existing fixed GGCMI Phase 3 calendar,
  and unchanged 0/30/70/100-percent season partitions.
- Years: harvest years 2092--2099. Previously validated 2092 anchors are read
  but never overwritten.
- Daily features: seasonal and stage rainfall, wet-day count at 1 mm/day,
  maximum consecutive dry days, Rx1day, Rx5day and seasonal mean temperature.
- Support: exact source/calendar cells. Missing or unsupported cells are not
  imputed. The agricultural summary uses the existing fixed MIRCA-OS v2
  rainfed-maize area for year 2000 and separately reports equal-cell values.
- Contrasts: within ESM, the eight-year SSP3-7.0 and SSP5-8.5 means minus the
  SSP1-2.6 mean. All five ESM values, signs and ranges are retained. Models are
  not treated as probability draws and are not selected by result magnitude.

## Validation and resource gates

Each annual panel must retain 36 disjoint ten-latitude-row tiles, exact source
hashes, 67,420 seasonal rows, 202,260 stage rows, three-stage additivity and
21 fixed raw-daily recomputations in an independent validator. Each ESM/SSP
eight-year panel then receives a cross-year hash/support audit. The final
fixed-area ledger is independently reconstructed from its tile numerators and
a fixed sample of source tiles.

Run one worker at a time with one numerical thread, at most 512 MiB sampled
process-group RSS, 64 MiB new output per bounded child, and at least 130 GiB
free disk. Stop on a changed source identity, partial prior output, resource
limit, nonphysical weather value, shifted support or failed validation.

From the isolated project root, the resumable controller is:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
NUMEXPR_NUM_THREADS=1 PYTHONPATH=scripts \
./.venv/bin/python -u scripts/continue_five_esm_late_completion.py
```

The controller writes ignored annual panels and resource receipts beneath
`data/interim/`, followed by
`data/interim/five_esm_maize_area_weather_20260921/result.json` and an
independent `validation.json`. The versioned report is rendered only from
that audited pair with `scripts/render_five_esm_maize_area_weather_report.py`.

## Interpretation boundary

The comparison estimates neither an anthropogenic effect nor a per-kelvin
response. Scenario differences combine forcing differences, one realization's
internal variability and bias-adjustment behavior. Eight terminal years do not
provide a sampling distribution. No result may be multiplied by a historical
yield coefficient or promoted to welfare/GIVE until the separate crop-response,
transport, adaptation, market and matched-CO2-pulse gates pass.
