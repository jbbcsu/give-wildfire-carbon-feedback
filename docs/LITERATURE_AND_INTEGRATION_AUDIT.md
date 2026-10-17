# Freshwater fisheries and angling audit

## Decision

Retain the published CIRA II numbers as a U.S. external scenario benchmark only. Do not convert them into an SCC or add them to GIVE. The integrated biological-to-consumer-surplus chain is unusually relevant, but the released temporal resolution, marginal-pulse incompatibility, and overlap with the FrEDI water-quality recreation bundle block inclusion.

## GIVE and FrEDI coverage

Published GIVE (Rennert et al. 2022, DOI `10.1038/s41586-022-05224-9`) has no named freshwater-fisheries or recreational-angling endpoint. FrEDI does include a water-quality sector with lost recreational value (Fant et al. 2017, drawing on Boehlert et al. 2015 and Yen et al. 2016), but does not list the CIRA II freshwater-fish model as a current FrEDI sector. The water-quality endpoint may include fishing services; therefore absence of a named fish sector does not establish additivity.

## Strongest integrated published evidence

Jones et al. (2013; DOI `10.1007/s11027-012-9385-3`) model climate-driven temperature and precipitation, stream temperature and flow, thermal habitat for coldwater, warmwater, and rough fish guilds, angling participation and fishing days, and economic value across the conterminous United States. Lane et al. (2015; DOI `10.1007/s10584-014-1107-2`) use the same core fish chain in the CIRA framework and explicitly define the economic endpoint as consumer surplus above actual trip cost, with current substitutes incorporated. The model covers rivers and streams, not lakes and reservoirs.

EPA's CIRA II report updates the calculation using five CMIP5 GCMs under RCP4.5 and RCP8.5. The report gives cumulative changes in national recreation value for 2011-2100 in million 2015 dollars discounted at 3 percent. The all-fishing five-GCM averages are losses of $45 billion under RCP8.5 and $38 billion under RCP4.5; one GCM produces a small gain under RCP8.5. Coldwater-only losses are much larger because gains in lower-valued warmwater and rough fishing partially offset lost coldwater fishing in the all-fishing total. The exact reported table is pinned in `data/reference/cira2_freshwater_fish_reported_npv_v1.csv`.

These values are scenario impacts relative to the 2011 reference, not marginal damages of an extra tonne of CO2. The posted CIRA data summary identifies freshwater-fish recreation value only at NCA-region and era resolution, and physical habitat/precipitation at HUC8 and era resolution. That is insufficient for a matched annual GIVE pulse.

## Newer global biological evidence

Brown, O'Connor, and Genner (2024; PNAS, DOI `10.1073/pnas.2410355121`) provide open analyzed data and code for historical global freshwater-fish population trajectories under warming (archived at DOI `10.5281/zenodo.14037297`). This is valuable for biological validation and transferability assessment. It does not link abundance to recreational catch, participation, consumer surplus, or a future marginal climate pulse, so it cannot support a global benefit transfer.

## Why the result is not additive

1. **Marginal pulse:** RCP scenario totals cannot be divided by cumulative emissions to recover the SCC of one tonne because response timing, nonlinearity, discounting, and carbon-cycle persistence differ.
2. **Temporal resolution:** era-level values do not provide annual baseline and pulse damage flows.
3. **Water-quality overlap:** FrEDI's water-quality willingness-to-pay endpoint is a recreation bundle potentially including fishing. A service-specific crosswalk or mutually exclusive choice is required.
4. **Behavior and management:** stocking, access, fish movement barriers, substitute sites, water management, and evolving preferences affect realized angler welfare.
5. **Geographic scope:** the integrated economic model is CONUS-specific. Global fish abundance data do not supply global angling demand or welfare functions.

## GIVE-compatible target interface

Future physical inputs should be annual HUC8 temperature, precipitation, streamflow, and stream-temperature distributions under matched baseline and one-ton-pulse climate runs. The biological layer should output accessible habitat or abundance by fish guild with stocking and migration assumptions. The economic layer should output annual consumer-surplus changes, not expenditure or revenue, with participation and substitution modeled explicitly.

The final aggregator must either remove angling services from the FrEDI water-quality WTP bundle or exclude that broader bundle when the fish endpoint is selected. U.S. results must remain a regional component; no global scaling by population, GDP, freshwater area, or fishing participation is authorized.
