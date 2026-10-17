# Terrestrial ecosystem and biodiversity services: GIVE coverage and sector selection

## Coverage finding

The audited GIVE damage aggregator contains temperature mortality, agriculture, and energy damages, with coastal impacts supplied by CIAM. It contains no configured terrestrial biodiversity, freshwater-quality welfare, forestry, broad recreation, pollination, habitat, or other ecosystem-service damage term. Physical terrestrial carbon pools in climate modules are not welfare valuation modules.

The broader damage-expansion registry already contains a separate biodiversity **nonuse** track based on Wingenroth et al. (2024). That approximately USD 8/tCO2 published benchmark remains external and non-additive because the public release lacks the full calibration, regional valuation, joint-draw, and annual pulse artifacts required by its admission gate. This project does not duplicate or weaken that gate.

## Evidence hierarchy

### Selected bounded benchmark: freshwater-quality recreational welfare

Fant et al. (2017), DOI `10.3390/w9020118`, link climate projections to hydrology and water-quality models, aggregate temperature, dissolved oxygen, nitrogen, and phosphorus into a water-quality index, and monetize changes using transferred willingness-to-pay estimates for users and nonusers. EPA FrEDI v4.1.1 publishes executable GCM-specific, state-level response functions and population scaling for CONUS.

This is the strongest immediately executable terrestrial/freshwater ecosystem-service benchmark because it provides a complete climate-response-to-welfare chain, peer-reviewed primary evidence, official open code, multiple climate-model surfaces, and an explicit welfare rather than market-revenue endpoint.

Important boundary: the source describes recreation opportunities including boating, swimming, and fishing. The estimate may therefore include freshwater recreational fishing use value and some nonuse value. It must not be combined with a future freshwater-fisheries recreation module or a broad biodiversity valuation without an endpoint-level overlap reconciliation. It excludes health effects and other clean-water amenities according to the FrEDI appendix.

### Secondary comparator: winter recreation

EPA FrEDI also implements Wobus et al. (2017) for alpine skiing, cross-country skiing, and snowmobiling. Those outputs are lost ticket revenues—market activity, not nonmarket ecosystem welfare—and adaptation is partly embedded through current and expanded snowmaking. This comparator is excluded from the primary benchmark to preserve the requested market/nonmarket distinction.

### Other terrestrial services

Commercial forestry, timber, pollination, pest regulation, habitat, erosion control, fire mitigation, and cultural heritage remain genuine gaps. The audit did not identify an open, peer-reviewed global package that maps a marginal CO2 pulse through climate into each service and welfare without benefit transfer. No coefficient or global scaling is fabricated here.

## Benchmark contract

- Geography: CONUS only (48 contiguous states and DC).
- Endpoint: freshwater-quality recreational user and nonuser willingness to pay.
- Response: five official FrEDI GCM surfaces; common support is 0-3 degrees C CONUS anomaly.
- Time support: 2025-2092, the years in which both matched GIVE paths remain within all five response surfaces.
- Socioeconomics: official FrEDI state population scaling; other socioeconomic quantities held as encoded in the response.
- Currency: 2015 USD converted to 2020 USD with BEA GDPDEF via FRED.
- Discounting: GIVE 2% Ramsey discount factor from the matched baseline.
- Claim: bounded partial SCC benchmark, not global and not approved for addition to GIVE.

## Overlap roadmap

Before combined-SCC inclusion, decompose or otherwise reconcile freshwater fishing use value with fisheries, nonuser WTP with the biodiversity nonuse module, water-related recreation with broader recreation, and water-quality changes with municipal water treatment/scarcity. Agriculture, forestry, health, and property amenities are explicitly outside the selected endpoint.
