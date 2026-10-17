# Climate conflict and crime audit

## Coverage and selection

GIVE has no explicit conflict or crime sector. The literature does not supply a
global, monetized, marginal-pulse damage function for organized armed conflict.
EPA FrEDI v4.1.1 does, however, release an executable CONUS benchmark for a
narrower endpoint: temperature-related changes in property and violent crime.
That crime benchmark is implemented here, while armed conflict remains fail-closed.

## Organized armed conflict

The published literature establishes that climate can affect some conflict risks,
but it does not justify a universal damage coefficient. Hsiang, Burke, and Miguel
(2013) synthesize diverse historical studies and report standardized effects for
interpersonal and intergroup conflict. The open replication data are valuable for
reanalysis, but the effect sizes pool different outcomes, climate variables,
spatial scales, and baseline risks. Buhaug et al. (2014) specifically challenge
cross-study independence, causal homogeneity, and representativeness. Koubi's
(2019) review finds no robust general effect on conflict onset, while Mach et al.
(2019) treats climate as one contextual risk factor among much stronger drivers.

None provides annual monetary welfare under a matched marginal carbon pulse.
Conflict losses also include mortality, injury, destroyed assets, lost output,
migration, fiscal/military expenditure, education, and institutional persistence.
Those channels overlap existing or separately planned GIVE sectors. Converting a
meta-analytic percentage change in conflict into GDP or VSL damages would require
unsupported baseline-risk, severity, duration, attribution, and valuation choices.
Accordingly, organized armed conflict has status `BLOCKED_NO_SCC`, not zero.

## Executable crime benchmark

FrEDI's CIL Crime sector derives temperature responses from Jacob, Lefgren, and
Moretti (2007), Ranson (2014), and the projections used by Hsiang et al. (2017).
It releases state-level crime-count changes for six GCM patterns and two aggregate
categories:

- Property: robbery, burglary, larceny, and motor-vehicle theft.
- Violent: murder, rape, and assault.

EPA monetizes each aggregate with a static, state-specific, incidence-weighted
cost from Heaton (2010). Property values cover property damage, enforcement, and
other indirect costs; violent values cover injury/loss of life, enforcement, and
other indirect costs. FrEDI assumes no additional adaptation and neither scales
crime incidence with future population nor grows unit costs. EPA notes both as
limitations.

The benchmark evaluates the published response functions under the matched GIVE
2025 CO2 pulse. The 2025--2092 result stays within the common 0--3 C response
support. The 2300 result follows FrEDI's endpoint linear extrapolation and is
reported separately. The six-GCM range represents spatial climate-pattern
variation, not econometric confidence intervals.

## Results and claim gate

Mean across six GCM surfaces, 2020 USD per tCO2:

| Horizon | Property | Violent | Total published-cost benchmark |
|---|---:|---:|---:|
| 2025--2092 | 0.000257 | 0.012649 | 0.012906 |
| 2025--2300 | 0.000361 | 0.018904 | 0.019265 |

These are reproducible CONUS benchmarks, not additive GIVE damages. Violent-crime
cost includes loss of life and injury that may overlap temperature mortality and
labor/health valuations. Property-crime cost includes enforcement and indirect
costs and can contain transfers or losses counted elsewhere. The released
aggregates do not permit those components to be removed. No global extrapolation
or armed-conflict interpretation is authorized.

