# Published agricultural partial-SCC benchmark

Hultgren et al. (2025) provide a directly relevant external benchmark rather
than a coefficient to import. Their Supplementary Table S13 reports staple-crop
partial SCC values under 16 combinations of emissions, market geography,
supply/demand elasticity, expenditure cap, CO2 fertilization, and production
flexibility. All values use constant 2% discounting, SSP3 income, and 2023 USD.

Across the eight listed RCP8.5 combinations, varietal-switching values range
from $3.80 to $17.62 per tonne CO2 and flexible-production-and-trade values
range from $1.71 to $7.93. Across the eight RCP4.5 combinations, the
corresponding ranges are $3.92--$17.75 and $1.76--$7.99. Each flexible value is
approximately 45% of its paired varietal-switching value, implementing the
authors' stated 55% impact reduction.

These are sensitivity ranges, not confidence intervals, and the rows change
multiple assumptions. Table S13 also does not include a moderate-elasticity,
country-market, ag-share-plus-10-point, CO2-fertilization row; it would be
incorrect to infer or label an unreported central value. The published values
use the authors' damage function, FaIR pulse, currency, extrapolation, and
discounting conventions. They are therefore a scale and methods benchmark,
not this project's precipitation-sector SCC and not a direct GIVE input.

The exact 16-row transcription and source hashes are in
`config/hultgren_partial_scc_table_s13_20260923.toml`; an executable validator
produces `data/provenance/hultgren_partial_scc_table_s13_validation_20260923.json`.

Primary source: [Hultgren et al. (2025)](https://doi.org/10.1038/s41586-025-09085-w), Supplementary Table S13.
