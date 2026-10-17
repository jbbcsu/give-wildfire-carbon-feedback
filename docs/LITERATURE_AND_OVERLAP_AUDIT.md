# Literature and overlap audit

## Purpose and accounting boundary

Bottom-up GIVE sums identified endpoints such as mortality, agriculture, energy expenditure, and coastal impacts. A top-down GDP/productivity regression estimates an aggregate economic response that can contain those market channels, cross-sector interactions, trade spillovers, correlated extremes, and other mechanisms. Adding the two would double count unknown amounts. Conversely, subtracting measured sectors from the macro estimate would not recover omitted sectors because GDP is not welfare, nonmarket endpoints may be absent, interactions are nonlinear, and methods/baselines differ.

This comparator is therefore mutually exclusive. It is neither an expanded GIVE total nor an omitted-sector residual.

## Selected published comparator

Bilal and Känzig (2026), DOI `10.1093/qje/qjag011`, exploit variation in global temperature and estimate persistent world-GDP effects using local projections, then discipline a neoclassical growth model and calculate an SCC from a CO2 temperature impulse. Their open BSD-licensed replication repository is pinned at commit `2425cebfa85772441d3f0672b9bdb301c42131a2`.

The exact published result table reports:

- PWT/global-temperature central SCC: 1,206.969 in 2024 international dollars/tCO2;
- paper-reported 95% confidence interval: 399–2,015;
- BU/global-temperature robustness SCC: 1,519.627;
- PWT/local-temperature comparator SCC: 148.939.

The model uses a 2% pure rate of time preference, not GIVE's draw-specific Ramsey implementation. Its temperature impulse, socioeconomic baseline, welfare object, and 2024 international-dollar unit also differ from GIVE. Direct numerical addition or an unqualified ratio to GIVE is prohibited.

## Leading alternatives reviewed

- Burke, Hsiang, and Miguel (2015), DOI `10.1038/nature15725`, provide open country-panel replication and project large 2100 income effects from nonlinear local temperature-growth relationships. The paper is foundational but does not supply a directly GIVE-harmonized SCC.
- Newell, Prest, and Sexton (2021), DOI `10.1016/j.jeem.2021.102445`, emphasize model uncertainty and out-of-sample model averaging in the GDP-temperature relationship. This strengthens the case for treating macro functional form as structural uncertainty rather than selecting a single aggregate residual.
- Kotz, Levermann, and Wenz (2024), DOI `10.1038/s41586-024-07219-0`, publish extensive replication code for regional income impacts from temperature, variability, and precipitation. Their 3.8-GB archive is not needed to validate the selected SCC comparator and does not provide a like-for-like GIVE pulse result.
- Burke et al. (2026), DOI `10.1038/s41586-026-10272-6`, link emissions, FaIR, pattern scaling, and country growth damages in a loss-and-damage framework. It is highly relevant but estimates a different attribution/welfare object and remains overlapping with bottom-up sectors.

## Interpretation

The wide gap between the selected paper's global-temperature and local-temperature SCCs is evidence of structural uncertainty, not proof that either number is the unmeasured remainder of GIVE. The appropriate publication use is a separate comparison panel showing bottom-up GIVE and top-down macro estimates side-by-side with non-comparability notes.
