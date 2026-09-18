# Published precipitation emulators after the PEEPS physicality screen

## Question

Can an existing, published emulator replace the raw linear PEEPS monthly
rainfall levels that become negative on mapped crop area, while also
capturing daily agricultural extremes? This is a literature/availability
screen, **not** a fitted emulator or crop-impact result.

## Monthly quantity and seasonality

[Schöngart et al. (2024), MESMER-M-TP v0.1.0](https://doi.org/10.5194/gmd-17-8283-2024)
emulates gridded **monthly** land precipitation conditional on gridded
monthly temperature, using a multiplicative gamma-GLM response and a
spatially coherent residual-variability module. The paper trains across
24 CMIP6 ESMs, validates against other ensemble members, and describes a
coupled temperature-emulator route from GMT to precipitation. It tests
month-to-month dependence and joint temperature–rainfall behavior. The
[author development code](https://github.com/sarasita/mesmer-m-tp) and
[paper-version archive](https://doi.org/10.5281/zenodo.11086167) are public.
This is a serious **physically positive monthly comparator** to PEEPS,
not a system we need to invent from scratch.

The open issue for GIVE is an exact, reproducible *calibrated-parameter*
and matched monthly-temperature path for the crops/ESMs and FAIR pulse,
not merely source code. An exact, non-truncated [paper-version GitHub
tree](https://api.github.com/repos/sarasita/mesmer-m-tp/git/trees/MESMER-M-TPv0.1.0?recursive=1)
(tree SHA `0228c434a26d09e3f5539bc58100d4601d5be106`, 49 blobs)
contains calibration/emulation scripts but no serialized precipitation
coefficient or parameter files. The current [official MESMER calibrated-
parameters list](https://mesmer-emulator.readthedocs.io/en/latest/parameters.html)
includes temperature, soil moisture, fire-weather and related variables,
but no precipitation. This establishes that the checked paper code and
current official parameter bundle are **not ready-to-run rainfall forcing**;
it does not prove that no author-held or other archive of fitted parameters
exists. None was downloaded or inferred.
Even if obtained, monthly means cannot by themselves identify daily dry
spells, Rx5day, wet-day counts or rainfall tails. The coupled GMT route
must retain temperature–precipitation covariance and uncertainty; using
independent PEEPS rain with a separate temperature path would not inherit
that validation.

## Daily heavy-rainfall tail

[Pierini et al. (2026), MESMER-X Rx1day](https://doi.org/10.1088/1748-9326/ae5fad)
is a published GMT/GSAT-conditioned **annual maximum one-day rainfall**
emulator. It fits 19 CMIP6 ESMs at 2.5-degree resolution and uses a GEV
framework with special near-zero/arid and heavy-tail/tropical treatment.
The authors provide a [paper-specific code archive](https://doi.org/10.5281/zenodo.19095277)
and state that integration into a future MESMER release is pending. This
is a defensible *Rx1day tail benchmark* and could later inform the
secondary flood pathway, but it does **not** supply daily sequences,
dry-spell duration, wet-day frequency, Rx5day or within-season timing.
Annual Rx1day and monthly rain cannot simply be summed as independent
damage terms without an explicitly joint event/exposure design.

## Decision and next gate

Keep direct-daily, source-matched ISIMIP crop features as the primary
research route. Evaluate MESMER-M-TP as a published positive monthly
alternative if exact calibrated parameters and temperature forcing can
be obtained and matched without exceeding storage/memory limits.
Register before scoring: crop-support mapping, total-rain and month-share
metrics, nonnegative support, temperature covariance, whole-scenario/
whole-ESM holdouts and FAIR pulse behavior. Use Pierini et al. for a
separate Rx1day benchmark only after verifying exact code/data/license
and spatial transfer; do not equate its annual maximum with the crop-
season Rx5day feature. Neither publication supplies an off-the-shelf
joint daily crop-weather path or an agricultural damage coefficient.
