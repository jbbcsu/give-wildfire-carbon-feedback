# Low-storage five-ESM late-century drought protocol

## Purpose

Extend the completed five-ESM direct-rainfall matrix with crop-calendar SPEI
while preserving the 130-GiB free-space floor. This is an exposure comparison,
not a crop response, damage estimate, or SCC input. Direct precipitation and
SPEI remain competing moisture representations and cannot be added as separate
damage terms.

## Frozen scientific design

- Climate models, members and scenarios match the validated direct-daily
  matrix: GFDL-ESM4, IPSL-CM6A-LR, MPI-ESM1-2-HR, MRI-ESM2-0 and
  UKESM1-0-LL under SSP1-2.6, SSP3-7.0 and SSP5-8.5.
- The target source period is 2091--2100; crop-window summaries use harvest
  years 2092--2099 so all SPEI-1/3/6 antecedent months and cross-year seasons
  are contained in the source block.
- Precipitation is the already resident, SHA-512-pinned ISIMIP3b daily source.
  Minimum and maximum temperature use the exact same ESM member, scenario,
  bias adjustment, grid, calendar, version and decade.
- Hargreaves-Samani reference evapotranspiration and the three-parameter
  log-logistic standardization are unchanged from the historical global
  candidate construction. Cell-by-calendar-month SPEI-1/3/6 parameters remain
  frozen to the observational 1982--2011 fit; no future value is refitted.
- Maize and soybean crop windows, proportional stages, preplant interval,
  irrigation regimes and MIRCA-OS v2 shares remain fixed and outcome-blind.
  Tail clipping and unsupported values remain explicit.

## Low-storage acquisition contract

The exact 15 `tasmin` and 15 `tasmax` decade objects must first be frozen in a
versioned metadata manifest containing dataset/file IDs, URLs, byte counts,
SHA-512 checksums, rights, DOI and source specifiers. Processing then occurs
one ESM-scenario pair at a time:

1. require at least 135 GiB free before the pair and enough room for both
   declared raw files plus 1 GiB of bounded derived/scratch output;
2. stream each object to an atomic temporary path and verify byte count and
   SHA-512 before opening it;
3. validate variable names, units, grid, daily chronology, declared calendar,
   and `tasmin <= tas <= tasmax` against the resident mean-temperature source;
4. read one day at a time, selecting only the frozen crop-support cells, and
   write a checksum-bound monthly/SPEI output plus validation receipt;
5. only after independent validation and output rehashing, delete the two raw
   temperature-extreme files and record their deletion/reacquisition contract;
6. stop on a partial download, changed source identity, failed content check,
   failed derived audit, less than 130 GiB free, more than 512 MiB sampled RSS,
   or more than 1 GiB retained derived output per pair.

At no time may more than one unprocessed `tasmin`/`tasmax` pair be resident.
Previously resident rainfall, mean temperature, historical fits and derived
results are not deleted by this protocol.

## Validation and interpretation

The final comparison must use one exact cell set across all 15
ESM-scenario combinations and retain named-model contrasts. Independent code
must reconstruct source identities, monthly water balance, rolling
accumulation, standardization, crop-window weighting, regime aggregation and
summary arithmetic from fixed samples. Five model signs are not probabilities
or confidence intervals. Scenario differences are not anthropogenic
attribution or marginal CO2-pulse responses.

No drought-yield relationship is promoted by this work. Historical SPEI,
scPDSI/PDSI and direct-rainfall families remain subject to the existing
geographic, terminal, interval and temperature-control gates. A completed
drought exposure matrix therefore does not authorize monetization or GIVE use.
