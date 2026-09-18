# Published GMT-to-rainfall route for GIVE agriculture

Status: source and implementation feasibility assessment, 17 September 2026.
This is **not** a fitted yield response, monetary damage function, or SCC result.

## Correction and decision

The climate-to-rainfall response does not have to be newly estimated as a
prerequisite. A published-response route should be evaluated alongside the
direct daily ISIMIP route, not held back until the latter is complete. The
published route is an efficient first candidate for **monthly amount and
seasonality**; the direct daily route remains the reference for dry spells,
within-month timing, heat--moisture dependence, and extremes. The two routes
must not be counted as separate damage sectors.

| Link | Most relevant published source | What may be imported | What is not supplied |
|---|---|---|---|
| GMT to gridded monthly rainfall | Kravitz and Snyder, PEEPS (2023), https://doi.org/10.1371/journal.pclm.0000159 | Model/scenario/month-specific gridded intercepts and slopes, with source code and validation | Daily spell structure, intensity tails, internally variable paired trajectories |
| GMT to joint monthly temperature/rainfall | Schöngart et al., MESMER-M-TP (2024), https://doi.org/10.5194/gmd-17-8283-2024 | Published positive gamma-log monthly precipitation formulation, conditional on gridded monthly temperature, with paper-version code | Ready-made precipitation parameters in MESMER v1.0.0; daily sequences |
| GMT to daily occurrence/amount | Kemsley et al. (2024), https://doi.org/10.1002/joc.8320 | Published wet/dry Markov and wet-day gamma parameter scaling design | Globally validated joint daily crop-weather draws or pinned fitted parameter release |
| GMT to one heavy-rain index | Pierini et al. (2026), https://doi.org/10.1088/1748-9326/ae5fad | Spatial Rx1day response and archived code | Full crop-year daily sequence or Rx5day/drought process |
| Crop weather to yield and welfare | Hultgren et al. (2025), https://doi.org/10.1038/s41586-025-09085-w | Global empirical yield responses including nonlinear rainfall by growing-season phase, temperature interaction, irrigation/adaptation heterogeneity; market-accounting precedent | A validated plug-and-play precipitation-only GIVE replacement; the exact welfare export remains unresolved in this project (see `HULTGREN_WELFARE_SOURCE_REVIEW_20260908.md`) |

PEEPS version 1.1 is openly licensed CC BY 4.0, but the Zenodo record
https://zenodo.org/api/records/7557622 packages published patterns in one
`outputs.tar.gz` of **3,244,457,764 bytes** (MD5
`eed1a0e8a43bf915c78ec68d0f37e357`). This is not an individual-model
small-file release. Under the current <=64 MiB owned-output/job and >=130 GiB
free-space constraints, a full local download is disallowed. Metadata and
small code assets can be read safely; a remotely streamed selective extraction
or external-drive staging requires its own source/member/size and integrity
check before any job. The project-specific two-ESM PEEPS-*style* fits already
completed here are methodological benchmarks, **not** the authors' published
coefficient files. Their negative rainfall forecasts fail the physical gate.

The release layout was tested without saving large files: Zenodo honors HTTP
byte ranges (206, `Accept-Ranges: bytes`). The first 1 MiB of the outer gzip
tar lists a 174,351-byte `outputs/global_temp.tar.gz` and then a
249,731,330-byte `outputs/dec_patterns.tar.gz`. Streaming only the first
270 MiB through nested tar readers revealed separate December NetCDF pattern
files, often below 1 MiB, named like
`ACCESS-CM2_ssp585_pr_monthly_patterns_dec.nc`. The 38 distinct model
prefixes in this *December archive* include MPI-ESM1-2-HR, MRI-ESM2-0 and
UKESM1-0-LL, which overlap the ISIMIP project catalogue, but **exclude
GFDL-ESM4 and IPSL-CM6A-LR**. No pattern NetCDF was retained in this check.
A later selective extractor can stream a named monthly inner archive and
write only prevalidated, size-capped model/scenario/variable members into an
ignored directory, then decode and checksum those files. A partial HTTP
range cannot validate the MD5 of the *whole* 3.2-GB archive, so the
member-level and whole-source integrity claims must remain distinct.
The first bounded author-file pilot now succeeded for MPI-ESM1-2-HR,
SSP5-8.5, December precipitation; see
`PUBLISHED_PEEPS_AUTHOR_DECEMBER_PILOT_RESULTS_20260917.md` for its exact
source hash, structural validation and remaining gates. This does **not**
replace the need for all crop-season months or held-out validation.
The follow-on preregistered rainfed-maize center-mapping screen finds a
nonzero crop footprint with negative published December rainfall in the
author's own SSP5-8.5 path; see
`PUBLISHED_PEEPS_CROP_SUPPORT_POSITIVITY_RESULTS_20260917.md`. This is a
physicality diagnostic, not evidence of agricultural damage.

The MESMER v1.0.0 [calibrated-parameter documentation](https://mesmer-emulator.readthedocs.io/en/latest/parameters.html)
lists temperature, heat, soil moisture, and fire-weather products, but **no
precipitation parameters**. Its [software paper](https://doi.org/10.5194/gmd-19-5669-2026)
says MESMER-M-TP is not fully integrated in v1.0.0. Thus it is incorrect to
say the currently downloadable 58-model parameter set gives an immediately
executable precipitation emulator. The 2024 paper's exact version of the
precipitation code is archived at https://doi.org/10.5281/zenodo.11086167;
calibration/parameter acquisition would still be required.

## Pairing with the existing GIVE pulse experiment

For each matched ESM/pattern draw and GIVE baseline/pulse temperature path,
construct the **same** crop-area-weighted monthly rainfall fields under both
paths, with no-pulse identity and physically nonnegative rainfall. Convert
them to crop-calendar/stage monthly totals and shares. Separately evaluate
actual direct-daily climate fields for wet-day counts, dry spells, Rx1day,
Rx5day, PDSI/SPEI or water-balance metrics. A monthly pattern coefficient
cannot identify those daily variables.

The global joint agricultural response should evaluate the matched
temperature, rainfall, CO2, irrigation, and adaptation scenario together.
If a precipitation-attributed component is reported, specify the conditional
counterfactual (e.g., change rainfall while fixing the temperature and CO2
inputs to a named path) and label it an attribution convention, not a unique
physical causal separation. Replace GIVE's existing MooreAg agriculture
sector for the joint welfare result; never append the same crop damage to it.

## Promotion gates

1. Inspect/pin actual published coefficient files, variable units, GMT
   baseline, model/member/scenario, grid, checksum, licence, and permitted
   pulse-domain support. If an archive cannot be selectively obtained within
   resource constraints, report that rather than substituting our fits while
   calling them published estimates.
2. Compare the imported monthly route against actual held-out ESM monthly
   rainfall on native and rainfed/irrigated crop support: annual amount,
   crop-season amount, month shares, onset proxy, positivity, and spatial
   errors. Preserve the failed linear-fit diagnostics as a warning, not a
   reason to discard published methods wholesale.
3. Compare daily/extreme indicators against direct-daily ISIMIP crop-year
   features. Never infer daily spells from monthly coefficients alone or add
   separately valued drought losses to the same rainfall-induced yield loss.
4. Use the selected global crop-response surface only after checking
   out-of-sample support, temperature/precipitation separation, irrigation,
   adaptation and CO2 treatment, and the exact welfare-export contract.
5. Run paired GIVE baseline/pulse draws only after a joint yield-to-welfare
   replacement is validated. Keep published-method, internally calibrated,
   observational, and sensitivity estimates distinctly labelled.

This two-track framing is analogous to the published wildfire-smoke exposure
chain, but precipitation-to-crop welfare is not just an exposure conversion:
the baseline GIVE agriculture sector already embeds agricultural climate
effects, and the crop response depends on multiple correlated climate and
management inputs.
