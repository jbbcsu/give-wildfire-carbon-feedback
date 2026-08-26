# Ram Fishman literature screen

## Scope

Google Scholar did not permit automated access on 2026-08-20.  This screen
uses Fishman's public publication list and primary publisher/institutional
records, prioritizing work relevant to precipitation distribution, crop
outcomes, irrigation, and water-constrained adaptation.

## Directly relevant to the main precipitation estimand

### Fishman (2016), *More uneven distributions overturn benefits of higher precipitation for crop yields*

DOI: https://doi.org/10.1088/1748-9326/11/2/024004

This is a central precedent, not merely adjacent economics.  Using daily
rainfall and crop-yield data across India (1970--2003), it estimates the
separate roles of total precipitation and the number of rainy days.  The paper
reports that fewer rainy days have robust negative associations large enough,
in its rice illustration, to reverse the benefit implied by higher total
precipitation alone.  It is substantially closer to this project's target
than a generic seasonal-total crop regression.

**Use in this project:**

* Treat wet-day frequency separately from total precipitation and from
  conditional intensity in each crop stage.
* Include a parsimonious rainy-day-count specification among the primary
  interpretable candidates, before adding more elaborate concentration and
  sequence features.
* Reproduce its key accounting comparison in every projection: total-only
  response versus total-plus-distribution response, holding temperature, CO2,
  calendar, and irrigation assumptions fixed.
* Do not transfer its India/crop-specific coefficient, result magnitude, or
  scenario conclusion to global SCC.  Estimate the response on the project's
  harmonized crop-season panel and report regional heterogeneity.

## Irrigation and water-availability evidence

| Study | Relevant lesson | Proper use/boundary |
|---|---|---|
| [Fishman (2018)](https://doi.org/10.1007/s10584-018-2146-x), *Groundwater depletion limits the scope for adaptation to increased rainfall variability in India* | Historical irrigation can reduce yield exposure to rainfall variability, but physical water availability sharply limits an irrigation-expansion adaptation counterfactual. | Supports constrained `trend`/`upper` adaptation scenarios; not a global irrigation benefit coefficient. |
| [Asoka et al. (2018)](https://doi.org/10.1029/2018GL078466), with Fishman | Groundwater recharge can respond differently to low- and high-intensity rainfall across aquifer regions. | Motivates an intensity-to-recharge stage in a future irrigated-water module; not an agricultural-yield estimate. |
| [Jain et al. (2021)](https://doi.org/10.1126/sciadv.abd2849), with Fishman | Satellite/census evidence links groundwater depletion to lower cropping intensity; canal and groundwater irrigation are not necessarily substitutes. | Supports the non-substitutability and resource-constraint sensitivity; no addition to the present joint yield loss. |
| [Fishman, Gine, and Jacoby (2023)](https://doi.org/10.1016/j.jdeveco.2023.103051) | A randomized drip-irrigation intervention raised profitability and changed cropping/groundwater transfers without reducing pumping in that setting. | Rules out treating engineering efficiency as an automatic proportional water-saving credit in the `upper` scenario. |

## Resulting implementation choice

The global and US-rainfed **production candidate registries** include an
explicit rainy-day-frequency comparison alongside seasonal total,
within-season share, conditional intensity, CDD, and heavy-rain features. The
current frozen global diagnostic omits rainy-day frequency and therefore
cannot decide whether to retain it. It may enter a retained production response
only after purged outer validation and a stable paired baseline/pulse response.
The irrigation papers tighten the adaptation and non-overlap rules; they do
not expand the primary estimand or create a second agricultural damage
component.
