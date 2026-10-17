# Literature, coverage, and overlap audit

## Exact GIVE gap

Rennert et al. (2022) identify GIVE's damage components as agriculture, temperature mortality, energy consumption, and coastal sea-level rise. Tourism and outdoor recreation are not separate GIVE components. This project excludes coral tourism and freshwater recreation because those endpoints were audited in separate projects.

## Executable evidence selected

Wobus et al. (2017, DOI: 10.1016/j.gloenvcha.2017.04.006) simulate natural snow at 247 U.S. recreation locations, incorporate snowmaking conditions for alpine skiing, translate season changes into visits for alpine skiing, cross-country skiing, and snowmobiling, and monetize visits using ticket or entry prices. EPA's FrEDI v4.1.1 publishes state/GCM response surfaces and describes the economic outputs as lost ticket sales/revenues and direct costs. This is the shortest published, executable link from temperature to an omitted recreational market endpoint.

The implementation reproduces FrEDI mechanics: a zero response at zero temperature anomaly; piecewise-linear response; linear extension from the final two nonmissing response points to 30 C; annual state population scaling; linear interpolation between 2010 and 2090 socioeconomic response snapshots; and the 2090 response held after 2090. Six source GCM response patterns are retained as structural climate-pattern uncertainty.

## Claim and overlap gates

The source endpoint is revenue, not compensating variation or consumer surplus. Lost local ticket sales are not necessarily a national social loss because visitors can substitute other places or activities, and revenue is not profit. Operating costs, closures, and local spillovers are not identified. Consequently:

- the numeric output is not additive to GIVE;
- it must not be called a consumer-surplus or total-tourism SCC;
- no global scaling is allowed;
- coral and freshwater recreation are excluded;
- lodging/property revenue, labor income, and ecosystem services are excluded to avoid overlap with other modules.

## Broader tourism decision

Broader tourism has heterogeneous climate drivers, destination substitution, origin-destination trade, adaptation, and both market and nonmarket welfare channels. The audit did not identify an open, globally executable marginal-welfare damage function with transparent overlap treatment that could be connected to GIVE without speculative assumptions. Broader tourism therefore remains `BLOCKED_NO_EXECUTABLE_WELFARE_FUNCTION`.

## What would unlock an additive module

An additive module needs a published or newly estimated welfare response measuring compensating variation (or a producer-surplus measure net of variable costs), explicit origin-destination substitution, national incidence, climate attribution, and non-overlap with labor/property/ecosystem modules. It must expose a temperature or climate-driver response suitable for matched baseline/pulse runs and quantify parameter uncertainty.

## Primary and authoritative sources

- Rennert et al. (2022), *Nature*, DOI: 10.1038/s41586-022-05224-9.
- Wobus et al. (2017), *Global Environmental Change* 45:1-14, DOI: 10.1016/j.gloenvcha.2017.04.006.
- U.S. EPA (2024), *Technical Documentation for the Framework for Evaluating Damages and Impacts (FrEDI)*.
- EPA `FrEDI_Data`, pinned commit `b506a3e0085bb446f56acc8c7076a1aea599fbb6`; EPA `FrEDI` release v4.1.1.
