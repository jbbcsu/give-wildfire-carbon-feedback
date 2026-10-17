# Literature and overlap audit

## Selected executable benchmark

FrEDI v4.1.1 is the shortest defensible marginal-pulse route. Its inland-flooding
sector is based on Wobus et al. (2019, 2021) and values climate-attributable
changes in expected annual **riverine-flood property damage** for the contiguous
United States. The study begins from property-level flood frequency-loss curves,
FEMA HAZUS depth-damage functions, and currently implemented property and
collective protection. FrEDI releases one GCM-ensemble response at 1--5 degrees C
of CONUS warming for each of 48 states and DC. The underlying analysis holds
property values constant and assumes no additional adaptation.

This endpoint is cleanly distinct from CIAM coastal inundation/storm-surge
damages and from FrEDI Roads/Rail. EPA also states that it excludes urban-drainage
floods; therefore this benchmark does **not** cover pluvial flooding. It excludes
mortality, morbidity, business interruption, agriculture, and indirect macroeconomic
effects. These boundaries make it additive only if those same property losses are
not counted elsewhere.

Primary sources:

- U.S. EPA, *FrEDI Technical Documentation* and Appendix B (2024).
- Wobus et al. (2019), DOI 10.1029/2018EF001119.
- Wobus et al. (2021), DOI 10.1088/1748-9326/ac1bd7.
- USEPA/FrEDI and USEPA/FrEDI_Data, exact revisions in the source manifest.

## Global literature screen

Dottori et al. (2018, *Nature Climate Change*, DOI
10.1038/s41558-018-0257-z) supplies an open global warming-level dataset at
current, 1.5, 2, and 3 degrees C and is the leading global benchmark. Its direct
economic loss total combines residential, commercial, industrial, infrastructure,
and agricultural damage. That bundle overlaps the separate GIVE agriculture and
roads/rail work, and the released warming-level tables do not provide a matched
marginal carbon pulse. It is therefore retained as an external magnitude and
geographic-coverage benchmark, not added to the SCC.

Global hazard frameworks such as GloFAS/JRC depth-damage implementations and
CLIMADA can construct river-flood losses, but they require a new hazard/exposure
pipeline and adaptation choices; they are not a published ready-to-add marginal
damage function. Published global totals also vary in exposure growth, protection,
and damage classes, so using a scalar multiplier on the CONUS FrEDI estimate would
be indefensible.

## Interface contract for a future global module

A global replacement must deliver annual, country-level incremental **residential
and commercial property** losses under the same baseline and pulse climate paths.
It must separately tag riverine and pluvial hazards; exclude coastal surge/SLR,
transport infrastructure, agriculture, mortality, and indirect GDP effects; state
the exposure year and adaptation/protection assumptions; preserve negative regional
changes; and carry hydrologic/GCM, vulnerability, and exposure uncertainty jointly.
Until those conditions are met, `global_scc_authorized=false`.

