# Crop-area-weighted global rainfed-maize weather contrasts

**Superseded for model-robustness interpretation.** The validated five-ESM
extension in `FIVE_ESM_MAIZE_AREA_WEATHER_RESULTS_20260921.md` adds GFDL-ESM4
and MRI-ESM2-0 on the same fixed support. This three-model record is retained
as the dated intermediate result; its values are unchanged.

This is a **direct daily ISIMIP3b climate-input diagnostic**, not a
forced per-K response, agricultural yield effect, damage, or SCC result.
The fixed [MIRCA-OS v2 rainfed-maize area release](https://www.hydroshare.org/resource/e4582ca0042148338bb5e0148b749ed6/)
provides year-2000 harvested-area weights on 0.5-degree cells. Exact
coordinate matching retains 30,654 of 30,821 positive-area cells and
108,038,665 of 108,086,337 mapped hectares (**99.9559%**), identically
across all 72 source panels. The missing 167 cells/47,672 ha are not
imputed. Each cell uses the fixed MIRCA rainfed-maize crop calendar and
three equal-duration-proxy stages with boundaries 0/30/70/100% of season;
these are **not observed phenological stage dates**.

The table shows area-weighted 2092–2099 mean weather under SSP5-8.5
*minus* SSP1-2.6 within each ESM. The SSP3-7.0 contrasts are preserved
in the machine-readable result and show the same three-model signs for
wet days (negative), longest dry spell (positive), Rx1day and Rx5day
(positive), while seasonal rainfall and stage rainfall are mixed.

| Daily-derived crop-season feature | UKESM | IPSL | MPI |
|---|---:|---:|---:|
| Season rainfall (mm) | +20.124 | +5.737 | −6.940 |
| Early/middle/late rainfall (mm) | +8.192 / +11.941 / −0.009 | −5.718 / −0.703 / +12.158 | −11.289 / +0.306 / +4.043 |
| Wet days (days) | −0.404 | −2.206 | −2.659 |
| Longest dry spell (days) | +0.739 | +1.093 | +1.653 |
| Rx1day (mm) | +4.950 | +7.440 | +1.754 |
| Rx5day (mm) | +10.359 | +10.283 | +4.211 |
| Season mean temperature (°C) | +5.492 | +5.615 | +3.712 |

The seasonal **amount** response has no unanimous sign across the three
ESMs. On these fixed crop-area weights and short scenario windows, fewer
wet days, longer maximum dry spells, and larger one-/five-day rainfall
maxima have the same sign across all three ESMs and both higher-SSP
contrasts. Area weighting changes the interpretation materially: on the
same matched crop cells, the SSP5-8.5-minus-SSP1-2.6 equal-cell rainfall
changes are +3.378/+28.276/−2.333 mm rather than the weighted
+20.124/+5.737/−6.940 mm (UKESM/IPSL/MPI). The earlier local
project diagnostic used **all** 67,420 eligible calendar cells, so its
equal-cell values are not directly a weighting-only comparison. The
new matched-support equal-cell ledger separates geographic selection
from weights but remains purely descriptive.

Every one of 72 ESM×scenario×year panels has a validated global source
manifest and 36 exact SHA-256-bound season/stage tiles. The primary
worker checked unique keys, three-stage count and rainfall sums,
physical values, the same matched area in every panel, and all tile
hashes. A separate implementation rebound 72 manifest/validation pairs,
recomputed 1,296 annual means and 108 scenario contrasts from the tile
ledger, and independently re-read seven fixed source tiles for 147
additional support/numerator checks. Two synthetic tests passed. The
primary result SHA-256 is
`027bd174738cb8de16c218b4674c33e7360c88f50bf719ef9a901769976b44f1`.
The monitored primary job sampled 219.77 MB group RSS, used <3 MB new
owned output and preserved the >=130 GiB disk-free floor. Raw feature
panels and detailed ledgers remain ignored; safe code/protocol and this
aggregate report are versioned.

These are **one realization per ESM and only eight terminal years**.
Scenario differences combine emissions, non-CO2 forcing, natural
variability, and possibly bias-adjustment behavior. Three agreeing signs
are not a confidence interval, a robust five-ESM forced response, or
evidence that rain timing independently damages yields. No yield, crop
price, irrigation adaptation, agricultural welfare, or GIVE SCC pathway
was evaluated. Next test broader ESM/time support and matched
temperature/precipitation dependence before assigning this pattern to
a climate-emissions pulse; the crop-yield response remains a separate
empirical gate.
