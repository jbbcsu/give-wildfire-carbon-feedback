# U.S. rainfed-maize future SPEI exposure protocol

## Scope

This outcome-blind stage reuses the validated five-ESM, three-SSP ISIMIP3b
late-century SPEI cubes to measure a U.S. rainfed-maize scenario exposure. It
does not read NASS yields, fit a response, project yield, attribute a causal
climate effect, calculate damages, or enter an SCC calculation.

Direct precipitation and SPEI remain mutually exclusive candidate moisture
families. Their effects are never stacked or summed.

## Frozen design

The executable lock is `config/us_future_spei_exposure_v1.toml`. It retains
half-degree maize cells assigned uniquely to `USA` by the existing MAPSPAM
crop-footprint country proxy, uses fixed MIRCA-OS v2 rainfed maize area, the
GGCMI `2015soc` rainfed maize calendar, harvest years 2092--2099, and the
already validated 2091--2100 daily climate cubes. The primary exposure is the
rainfed crop-season mean of SPEI-3. SPEI-1/6 and stage/preplant windows are
prespecified sensitivity summaries.

For each of GFDL-ESM4, IPSL-CM6A-LR, MPI-ESM1-2-HR, MRI-ESM2-0, and
UKESM1-0-LL, compute SSP3-7.0 minus SSP1-2.6 and SSP5-8.5 minus SSP1-2.6.
Retain all named-model values plus the equal-model mean, median, range, and
population standard deviation. These five named models are not independent
random draws; the spread is not a confidence interval.

The underlying index is precipitation minus Hargreaves--Samani reference ET0,
standardized using cell-by-calendar-month generalized-logistic parameters fit
to observational GSWP3-W5E5 over 1982--2011 and then held fixed. No future
value is used to refit the standardization.

## Fail-closed bridge to the NASS response

A valid U.S. scenario-exposure aggregation is not sufficient to multiply by
the existing non-irrigated corn PDSI coefficient. That bridge remains closed
until all of the following are independently validated:

1. the same source-consistent SPEI definition is constructed historically on
   the NASS county support and passes the frozen geographic and terminal yield
   gates;
2. future climate is aggregated to those exact NASS counties using fixed,
   documented weights and the NASS calendar;
3. the response family uses that same SPEI scale and definition, or an
   outcome-blind PDSI-to-SPEI crosswalk is validated; and
4. the direct-rainfall and drought-index projections remain separate
   alternative results.

The current PDSI response cannot be treated as an SPEI response, and a global
half-degree crop-area exposure cannot be treated as a county-level exposure.
